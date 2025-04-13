# poker_api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PokerTableViewSet, PlayerViewSet, GameViewSet, PlayerGameViewSet

router = DefaultRouter()
router.register(r'tables', PokerTableViewSet)
router.register(r'players', PlayerViewSet)
router.register(r'games', GameViewSet)
router.register(r'player-games', PlayerGameViewSet)

urlpatterns = [
    path('', include(router.urls)),
]