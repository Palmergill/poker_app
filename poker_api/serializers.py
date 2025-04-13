# poker_api/serializers.py
from rest_framework import serializers
from .models import PokerTable, Player, Game, PlayerGame, Card
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class PlayerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Player
        fields = ['id', 'user', 'balance']

class PokerTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = PokerTable
        fields = ['id', 'name', 'max_players', 'small_blind', 'big_blind', 'min_buy_in', 'max_buy_in', 'created_at']

class GameSerializer(serializers.ModelSerializer):
    table = PokerTableSerializer(read_only=True)
    current_player = PlayerSerializer(read_only=True)

    class Meta:
        model = Game
        fields = ['id', 'table', 'status', 'pot', 'current_player', 'created_at']

class PlayerGameSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)
    game = GameSerializer(read_only=True)

    class Meta:
        model = PlayerGame
        fields = ['id', 'player', 'game', 'seat_position', 'stack', 'is_active']
