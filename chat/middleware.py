from channels.security.websocket import AllowedHostsOriginValidator
from channels.middleware import BaseMiddleware

class AllowEmptyOriginValidator(BaseMiddleware):
    def __init__(self, inner):
        self.inner = inner
        self.allowed_hosts_validator = AllowedHostsOriginValidator(inner)

    async def __call__(self, scope, receive, send):
        if "headers" in scope:
            headers = dict(scope["headers"])
            if b"origin" not in headers:
                scope["headers"].append((b"origin", b"http://localhost"))
        return await self.allowed_hosts_validator(scope, receive, send)
