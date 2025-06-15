import os
import asyncio
import time
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.layers import get_channel_layer
from chat.middleware import AllowEmptyOriginValidator
from chat.routing import websocket_urlpatterns
from daphne.server import Server

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mywebsite.settings')

django_asgi_app = get_asgi_application()

# Metrics for shutdown time
metrics = {
    "last_shutdown_time": 0.0
}
metrics_lock = asyncio.Lock()

class CustomServer(Server):
    async def handle(self):
        try:
            await super().handle()
        except (KeyboardInterrupt, SystemExit):
            await self.graceful_shutdown()

    async def graceful_shutdown(self):
        start_time = time.time()
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "chat-global",
            {
                "type": "shutdown_message",
                "message": {"reason": "Server is shutting down"}
            }
        )
        await asyncio.sleep(8)
        self.stop()
        async with metrics_lock:
            metrics["last_shutdown_time"] = time.time() - start_time

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowEmptyOriginValidator(
        URLRouter(websocket_urlpatterns)
    ),
})

application.server_class = CustomServer
