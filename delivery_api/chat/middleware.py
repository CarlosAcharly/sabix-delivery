from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token):
    """Obtener usuario desde el token JWT"""
    try:
        access_token = AccessToken(token)
        user_id = access_token.payload.get('user_id')
        return User.objects.get(id=user_id, is_active=True)
    except Exception as e:
        print(f"❌ Error obteniendo usuario del token: {e}")
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Middleware para autenticación JWT en WebSockets
    """
    def __init__(self, inner):
        self.inner = inner
    
    async def __call__(self, scope, receive, send):
        # Obtener token de la query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        token = None
        if 'token' in query_params:
            token = query_params['token'][0]
        
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Wrapper para facilitar el uso"""
    return JWTAuthMiddleware(inner)