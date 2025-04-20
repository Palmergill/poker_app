# poker_api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PokerTableViewSet, PlayerViewSet, GameViewSet

router = DefaultRouter()
router.register(r'tables', PokerTableViewSet)
router.register(r'players', PlayerViewSet)
router.register(r'games', GameViewSet)

urlpatterns = [
    path('', include(router.urls)),
]