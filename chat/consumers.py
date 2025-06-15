import json
import asyncio
import datetime
import uuid
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

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
    async def connect(self):
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

        except Exception:
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def disconnect(self, close_code):
        print(f"Disconnecting session {self.session_uuid} with close code {close_code}")
        try:
            await self.channel_layer.group_discard("chat-global", self.channel_name)
            async with session_store_lock:
                session_store[self.session_uuid] = self.message_count
            async with metrics_lock:
                metrics["active_connections"] = max(0, metrics["active_connections"] - 1)
            if close_code != 1001:
                print("here")
                await self.send(text_data=json.dumps({
                    "bye": True,
                    "total": self.message_count
                }))
        except Exception:
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def receive(self, text_data):
        try:
            self.message_count += 1
            async with session_store_lock:
                session_store[self.session_uuid] = self.message_count
            async with metrics_lock:
                metrics["total_messages"] += 1
            await self.send(text_data=json.dumps({
                "count": self.message_count
            }))
        except Exception:
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def heartbeat_message(self, event):
        try:
            await self.send(text_data=json.dumps(event["message"]))
        except Exception:
            async with metrics_lock:
                metrics["error_count"] += 1
            raise

    async def shutdown_message(self, event):
        try:
            await self.close(code=1001)
        except Exception:
            async with metrics_lock:
                metrics["error_count"] += 1
            raise
