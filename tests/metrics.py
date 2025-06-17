import pytest
from django.test import AsyncClient
from prometheus_client.parser import text_string_to_metric_families
from chat.consumers import metrics, metrics_lock

@pytest.mark.asyncio
async def test_metrics_endpoint():
    client = AsyncClient()
    async with metrics_lock:
        metrics["total_messages"] = 10
        metrics["active_connections"] = 3
        metrics["error_count"] = 1
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; version=0.0.4"

    metric_families = list(text_string_to_metric_families(response.content.decode()))
    metrics_dict = {m.name: m for m in metric_families}

    assert "websocket_total_messages" in metrics_dict
    assert metrics_dict["websocket_total_messages"].samples[0].value == 10

    assert "websocket_active_connections" in metrics_dict
    assert metrics_dict["websocket_active_connections"].samples[0].value == 3

    assert "websocket_error_count" in metrics_dict
    assert metrics_dict["websocket_error_count"].samples[0].value == 1

    assert "websocket_last_shutdown_time" in metrics_dict
    assert metrics_dict["websocket_last_shutdown_time"].samples[0].value == 0.0
