# Updated ASGI configuration for poker_project/asgi.py
"""
ASGI config for poker_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from poker_api.middleware import JWTAuthMiddleware
import poker_api.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poker_project.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(
                poker_api.routing.websocket_urlpatterns
            )
        )
    ),
})