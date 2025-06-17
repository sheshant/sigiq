import logging

from django.http import HttpResponse
from django.shortcuts import render

from .consumers import metrics as ws_metrics, metrics_lock as ws_metrics_lock
from mywebsite.asgi import metrics as asgi_metrics, metrics_lock as asgi_metrics_lock


logger = logging.getLogger('__name__')

async def metrics_view(request):
    """
    View to expose WebSocket metrics in Prometheus format.
    This view collects metrics from the WebSocket consumer and ASGI application,
    and formats them for Prometheus scraping.
    It includes total messages received, active connections,
    error counts, and the last shutdown time of the ASGI application.
    """

    async with ws_metrics_lock:
        total_messages = ws_metrics["total_messages"]
        active_connections = ws_metrics["active_connections"]
        error_count = ws_metrics["error_count"]
    async with asgi_metrics_lock:
        last_shutdown_time = asgi_metrics["last_shutdown_time"]

    prometheus_metrics = (
        '# HELP websocket_total_messages Total number of WebSocket messages received\n'
        '# TYPE websocket_total_messages counter\n'
        f'websocket_total_messages {total_messages}\n'
        '# HELP websocket_active_connections Current number of active WebSocket connections\n'
        '# TYPE websocket_active_connections gauge\n'
        f'websocket_active_connections {active_connections}\n'
        '# HELP websocket_error_count Total number of WebSocket errors\n'
        '# TYPE websocket_error_count counter\n'
        f'websocket_error_count {error_count}\n'
        '# HELP websocket_last_shutdown_time Time taken for last server shutdown in seconds\n'
        '# TYPE websocket_last_shutdown_time gauge\n'
        f'websocket_last_shutdown_time {last_shutdown_time}\n'
    )
    return HttpResponse(prometheus_metrics, content_type='text/plain; version=0.0.4')


def ws_chat_view(request):
    return render(request, "chat/test_websocket.html")
