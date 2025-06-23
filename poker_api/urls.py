# poker_api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PokerTableViewSet, PlayerViewSet, GameViewSet
from .views import register_user, game_hand_history

router = DefaultRouter()
router.register(r'tables', PokerTableViewSet)
router.register(r'players', PlayerViewSet)
router.register(r'games', GameViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', register_user, name='register_user'),
    path('games/<int:game_id>/hand-history/', game_hand_history, name='game_hand_history'),
]