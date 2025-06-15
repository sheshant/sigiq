import json
import asyncio
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

# Flag to ensure heartbeat task runs only once
heartbeat_task_started = False

async def heartbeat_broadcast():
    """Send heartbeat every 30 seconds to all clients in the chat-global group."""
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
        await asyncio.sleep(3)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        global heartbeat_task_started
        self.message_count = 0
        # Add to global chat group
        await self.channel_layer.group_add("chat-global", self.channel_name)
        await self.accept()

        # Start heartbeat task if not already started
        if not heartbeat_task_started:
            asyncio.create_task(heartbeat_broadcast())
            heartbeat_task_started = True

    async def disconnect(self, close_code):
        # Remove from global chat group
        await self.channel_layer.group_discard("chat-global", self.channel_name)
        await self.send(text_data=json.dumps({
            "bye": True,
            "total": self.message_count
        }))

    async def receive(self, text_data):
        self.message_count += 1
        await self.send(text_data=json.dumps({
            "count": self.message_count
        }))

    async def heartbeat_message(self, event):
        """Handle heartbeat messages from the group."""
        await self.send(text_data=json.dumps(event["message"]))
