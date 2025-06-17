import pytest
import uuid
from channels.testing import WebsocketCommunicator
from chat.consumers import session_store
from chat.routing import websocket_urlpatterns
from channels.routing import URLRouter
from chat.middleware import AllowEmptyOriginValidator

@pytest.fixture(autouse=True)
def clear_session_store():
    session_store.clear()
    yield
    session_store.clear()

async def test_connect_new_session():
    communicator = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        "/ws/chat/"
    )
    try:
        connected, _ = await communicator.connect()
        assert connected
        response = await communicator.receive_json_from()
        assert "session_uuid" in response
        assert isinstance(uuid.UUID(response["session_uuid"]), uuid.UUID)
    finally:
        await communicator.disconnect()

async def test_connect_resume_session():
    session_uuid = str(uuid.uuid4())
    session_store[session_uuid] = 5
    communicator = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        f"/ws/chat/?session_uuid={session_uuid}"
    )
    try:
        connected, _ = await communicator.connect()
        assert connected
        response = await communicator.receive_json_from()
        assert response["session_uuid"] == session_uuid
        await communicator.send_json_to({"message": "test"})
        response = await communicator.receive_json_from()
        assert response["count"] == 6
    finally:
        await communicator.disconnect()

async def test_connect_invalid_session_uuid():
    communicator = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        "/ws/chat/?session_uuid=invalid-uuid"
    )
    try:
        connected, _ = await communicator.connect()
        assert connected
        response = await communicator.receive_json_from()
        assert "session_uuid" in response
        assert response["session_uuid"] != "invalid-uuid"
        await communicator.send_json_to({"message": "test"})
        response = await communicator.receive_json_from()
        assert response["count"] == 1
    finally:
        await communicator.disconnect()

async def test_connect_nonexistent_session_uuid():
    communicator = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        f"/ws/chat/?session_uuid={str(uuid.uuid4())}"
    )
    try:
        connected, _ = await communicator.connect()
        assert connected
        response = await communicator.receive_json_from()
        assert "session_uuid" in response
        await communicator.send_json_to({"message": "test"})
        response = await communicator.receive_json_from()
        assert response["count"] == 1
    finally:
        await communicator.disconnect()

async def test_connect_concurrent_same_session_uuid():
    session_uuid = str(uuid.uuid4())
    session_store[session_uuid] = 5
    communicator1 = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        f"/ws/chat/?session_uuid={session_uuid}"
    )
    communicator2 = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        f"/ws/chat/?session_uuid={session_uuid}"
    )
    try:
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        assert connected1 and connected2
        await communicator1.receive_json_from()
        await communicator2.receive_json_from()
        await communicator1.send_json_to({"message": "test"})
        await communicator1.receive_json_from()
        await communicator2.send_json_to({"message": "test"})
        response = await communicator2.receive_json_from()
        assert response["count"] == 6
    finally:
        await communicator1.disconnect()
        await communicator2.disconnect()

async def test_receive_message():
    communicator = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        "/ws/chat/"
    )
    try:
        connected, _ = await communicator.connect()
        assert connected
        await communicator.receive_json_from()
        await communicator.send_json_to({"message": "test"})
        response = await communicator.receive_json_from()
        assert response["count"] == 1
        await communicator.send_json_to({"message": "test2"})
        response = await communicator.receive_json_from()
        assert response["count"] == 2
    finally:
        await communicator.disconnect()

async def test_disconnect_normal():
    communicator = WebsocketCommunicator(
        AllowEmptyOriginValidator(URLRouter(websocket_urlpatterns)),
        "/ws/chat/"
    )
    try:
        connected, _ = await communicator.connect()
        assert connected
        await communicator.receive_json_from()
        await communicator.send_json_to({"message": "test"})
        await communicator.receive_json_from()
        await communicator.disconnect()
        response = await communicator.receive_json_from()
        assert response["bye"] is True
        assert response["total"] == 1
    finally:
        await communicator.disconnect()

