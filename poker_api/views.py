# poker_api/views.py
from rest_framework import viewsets
from .models import PokerTable, Player, Game, PlayerGame
from .serializers import PokerTableSerializer, PlayerSerializer, GameSerializer, PlayerGameSerializer

class PokerTableViewSet(viewsets.ModelViewSet):
    queryset = PokerTable.objects.all()
    serializer_class = PokerTableSerializer

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer

class PlayerGameViewSet(viewsets.ModelViewSet):
    queryset = PlayerGame.objects.all()
    serializer_class = PlayerGameSerializer