# poker_api/middleware.py
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate users for WebSocket connections using JWT tokens.
    """
    
    async def __call__(self, scope, receive, send):
        # Get the token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        logger.info(f"WebSocket auth attempt with token: {token[:20] if token else 'None'}...")
        
        if token:
            try:
                # Decode the token
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                user = await get_user(user_id)
                scope['user'] = user
                logger.info(f"WebSocket authenticated user: {user.username if user.is_authenticated else 'Anonymous'}")
            except (InvalidToken, TokenError, KeyError) as e:
                logger.warning(f"WebSocket JWT validation failed: {e}")
                scope['user'] = AnonymousUser()
        else:
            logger.warning("WebSocket connection attempt without token")
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)