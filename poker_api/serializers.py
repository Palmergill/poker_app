# poker_api/serializers.py
from rest_framework import serializers
from .models import PokerTable, Player, Game, PlayerGame, GameAction
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
        
    def validate(self, data):
        """
        Validate table creation data
        """
        if 'big_blind' in data and 'small_blind' in data:
            if data['big_blind'] < data['small_blind']:
                raise serializers.ValidationError({'big_blind': 'Big blind must be greater than or equal to small blind'})
        
        if 'min_buy_in' in data and 'big_blind' in data:
            if data['min_buy_in'] < data['big_blind'] * 10:
                raise serializers.ValidationError({'min_buy_in': 'Minimum buy-in should be at least 10 times the big blind'})
        
        if 'max_buy_in' in data and 'min_buy_in' in data:
            if data['max_buy_in'] < data['min_buy_in']:
                raise serializers.ValidationError({'max_buy_in': 'Maximum buy-in must be greater than or equal to minimum buy-in'})
        
        return data

class PlayerGameSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)
    cards = serializers.SerializerMethodField()
    
    class Meta:
        model = PlayerGame
        fields = ['id', 'player', 'seat_position', 'stack', 'is_active', 'cards', 'current_bet', 'total_bet']
    
    def get_cards(self, obj):
        # Only show cards to the owning player or in showdown
        request = self.context.get('request')
        if request and request.user == obj.player.user:
            return obj.get_cards()
        if obj.game.phase == 'SHOWDOWN' and obj.is_active:
            return obj.get_cards()
        return []

class GameActionSerializer(serializers.ModelSerializer):
    player = serializers.SerializerMethodField()
    
    class Meta:
        model = GameAction
        fields = ['id', 'player', 'action_type', 'amount', 'timestamp']
    
    def get_player(self, obj):
        return obj.player_game.player.user.username

class GameSerializer(serializers.ModelSerializer):
    table = PokerTableSerializer(read_only=True)
    current_player = PlayerSerializer(read_only=True)
    players = serializers.SerializerMethodField()
    community_cards = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = ['id', 'table', 'status', 'phase', 'pot', 'current_bet', 'dealer_position', 
                  'current_player', 'community_cards', 'players', 'actions', 'created_at']
    
    def get_community_cards(self, obj):
        return obj.get_community_cards()
    
    def get_players(self, obj):
        player_games = PlayerGame.objects.filter(game=obj).order_by('seat_position')
        serializer = PlayerGameSerializer(player_games, many=True, context=self.context)
        return serializer.data
    
    def get_actions(self, obj):
        # Get last 10 actions
        actions = GameAction.objects.filter(
            player_game__game=obj
        ).order_by('-timestamp')[:10]
        serializer = GameActionSerializer(actions, many=True)
        return serializer.data

class GameActionRequestSerializer(serializers.Serializer):
    action_type = serializers.ChoiceField(choices=['FOLD', 'CHECK', 'CALL', 'BET', 'RAISE'])
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)