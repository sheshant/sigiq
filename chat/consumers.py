import json
import asyncio
import datetime
import logging
import uuid
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer


logger = logging.getLogger('__name__')

# In-memory store for session data (session_uuid -> message_count)
session_store = {}
session_store_lock = asyncio.Lock()
# Metrics
metrics = {
    "total_messages": 0,
    "active_connections": 0,
    "error_count": 0
}
metrics_lock = asyncio.Lock()
heartbeat_task_started = False

async def heartbeat_broadcast():
    """
    Broadcast a heartbeat message every 30 seconds to all connected clients.
    This function runs indefinitely and sends a timestamp to the "chat-global" group.
    It is started when the first client connects.
    The heartbeat message is used to keep the connection alive and to check the health of the server.
    """
    channel_layer = get_channel_layer()
    while True:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        await channel_layer.group_send(
            "chat-global",
            {
                "type": "heartbeat_message",
                "message": {"ts": timestamp}
            }
        )
        await asyncio.sleep(30)

class ChatConsumer(AsyncWebsocketConsumer):
    """
    A WebSocket consumer that handles chat messages and session management.
    This consumer manages WebSocket connections, allowing clients to connect, send messages,
    and receive messages, including heartbeat messages to keep the connection alive.
    It also tracks the number of messages sent in a session and provides metrics for active connections and errors.
    The consumer uses an in-memory store to keep track of session UUIDs and message counts.
    The session UUID is passed as a query parameter during the WebSocket handshake.
    The consumer also handles graceful disconnection and broadcasts a shutdown message when the server is shutting down.
    The heartbeat broadcast is started when the first client connects, ensuring that all clients receive periodic updates.
    """
    async def connect(self):
        # This method is called when the WebSocket is handshaking as part of the connection process.
        logger.info(f'Connecting session on channel {self.channel_name}')
        global heartbeat_task_started
        # Parse query string for session_uuid
        query_string = self.scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        session_uuid = query_params.get("session_uuid", [None])[0]

        try:
            async with session_store_lock:
                if session_uuid and session_uuid in session_store:
                    self.message_count = session_store[session_uuid]
                    self.session_uuid = session_uuid
                else:
                    self.session_uuid = str(uuid.uuid4())
                    self.message_count = 0
                    session_store[self.session_uuid] = self.message_count

            async with metrics_lock:
                metrics["active_connections"] += 1

            await self.channel_layer.group_add("chat-global", self.channel_name)
            await self.accept()

            await self.send(text_data=json.dumps({
                "session_uuid": self.session_uuid
            }))

            if not heartbeat_task_started:
                asyncio.create_task(heartbeat_broadcast())
                heartbeat_task_started = True

        except Exception as e:
            logger.exception(f"Error during WebSocket connection for session {self.session_uuid}: {e}")
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def disconnect(self, close_code):
        """
        This method is called when the WebSocket closes for any reason.
        It handles the disconnection process, updates the session store with the message count,
        and decrements the active connections metric.
        If the disconnection is not due to a normal closure (close code 1001),
        it sends a goodbye message back to the client with the total message count for the session.
        """
        logger.info(f'Disconnecting session {self.session_uuid} on channel {self.channel_name} with close code {close_code}')
        try:
            await self.channel_layer.group_discard("chat-global", self.channel_name)
            async with session_store_lock:
                session_store[self.session_uuid] = self.message_count
            async with metrics_lock:
                metrics["active_connections"] = max(0, metrics["active_connections"] - 1)
            if close_code != 1001:
                await self.send(text_data=json.dumps({
                    "bye": True,
                    "total": self.message_count
                }))
        except Exception as e:
            logger.exception(f"Error during WebSocket disconnection for session {self.session_uuid}: {e}")
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def receive(self, text_data):
        """
        This method is called when a message is received from the WebSocket.
        It increments the message count for the session, updates the session store,
        """
        logger.info(f'Receiving message for session {self.session_uuid} on channel {self.channel_name}')
        try:
            self.message_count += 1
            async with session_store_lock:
                session_store[self.session_uuid] = self.message_count
            async with metrics_lock:
                metrics["total_messages"] += 1
            await self.send(text_data=json.dumps({
                "count": self.message_count
            }))
        except Exception as e:
            logger.exception(f"Error receiving message for session {self.session_uuid} {text_data}: {e} ")
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def heartbeat_message(self, event):
        """
        This method handles heartbeat messages sent to the "chat-global" group.
        It sends a timestamp to the client to keep the connection alive and check the health of the server.
        """
        try:
            await self.send(text_data=json.dumps(event["message"]))
        except Exception:
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def shutdown_message(self, event):
        """
        This method handles shutdown messages sent to the "chat-global" group.
        It attempts to close the WebSocket connection gracefully with a code indicating that the server is shutting down.
        If an error occurs during the shutdown process, it increments the error count in the metrics.
        """
        try:
            await self.close(code=1001)
        except Exception:
            async with metrics_lock:
                metrics["error_count"] += 1
            raise
