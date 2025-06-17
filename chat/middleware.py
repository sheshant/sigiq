import logging

from channels.security.websocket import AllowedHostsOriginValidator
from channels.middleware import BaseMiddleware


logger = logging.getLogger('__name__')

class AllowEmptyOriginValidator(BaseMiddleware):
    """
    Middleware to allow empty origin headers in WebSocket connections.
    This is useful for development purposes where the origin might not be set.
    It wraps the AllowedHostsOriginValidator to ensure that connections with no origin header
    are still processed, while still validating allowed hosts.
    This middleware should be used in development environments only, as it bypasses origin checks.
    """
    def __init__(self, inner):
        self.inner = inner
        self.allowed_hosts_validator = AllowedHostsOriginValidator(inner)

    async def __call__(self, scope, receive, send):
        if "headers" in scope:
            headers = dict(scope["headers"])
            if b"origin" not in headers:
                scope["headers"].append((b"origin", b"http://localhost"))
        return await self.allowed_hosts_validator(scope, receive, send)
