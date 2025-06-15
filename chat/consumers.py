import json
import asyncio
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

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
        self.message_count = 0
        await self.channel_layer.group_add("chat-global", self.channel_name)
        await self.accept()

        if not heartbeat_task_started:
            asyncio.create_task(heartbeat_broadcast())
            heartbeat_task_started = True

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("chat-global", self.channel_name)
        if close_code != 1001:
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
        await self.send(text_data=json.dumps(event["message"]))

    async def shutdown_message(self, event):
        await self.close(code=1001)
