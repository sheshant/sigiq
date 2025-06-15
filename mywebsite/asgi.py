import os
import asyncio
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.layers import get_channel_layer
from chat.middleware import AllowEmptyOriginValidator
from chat.routing import websocket_urlpatterns
from daphne.server import Server

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

django_asgi_app = get_asgi_application()

class CustomServer(Server):
    async def handle(self):
        try:
            await super().handle()
        except (KeyboardInterrupt, SystemExit):
            await self.graceful_shutdown()

    async def graceful_shutdown(self):
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "chat-global",
            {
                "type": "shutdown_message",
                "message": {"reason": "Server is shutting down"}
            }
        )
        await asyncio.sleep(8)  # Allow 8 seconds for in-flight messages
        self.stop()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowEmptyOriginValidator(
        URLRouter(websocket_urlpatterns)
    ),
})

application.server_class = CustomServer
