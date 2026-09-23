import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "delivery_api.settings")

from django.core.asgi import get_asgi_application

# Inicializa Django antes de importar cualquier app
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# ✅ Importar rutas de WebSocket de cada app
from notifications.routing import websocket_urlpatterns as notification_ws
from chat.routing import websocket_urlpatterns as chat_ws

# ✅ Combinar todas las rutas de WebSocket
websocket_urlpatterns = notification_ws + chat_ws

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})