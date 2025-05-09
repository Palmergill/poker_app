# poker_api/models.py
from django.db import models
from django.contrib.auth.models import User
import json

class PokerTable(models.Model):
    name = models.CharField(max_length=100)
    max_players = models.IntegerField(default=9)
    small_blind = models.DecimalField(max_digits=10, decimal_places=2)
    big_blind = models.DecimalField(max_digits=10, decimal_places=2)
    min_buy_in = models.DecimalField(max_digits=10, decimal_places=2)
    max_buy_in = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return self.user.username

class Game(models.Model):
    GAME_STATUS_CHOICES = [
        ('WAITING', 'Waiting for players'),
        ('PLAYING', 'Game in progress'),
        ('FINISHED', 'Game finished'),
    ]

    GAME_PHASE_CHOICES = [
        ('PREFLOP', 'Pre-flop'),
        ('FLOP', 'Flop'),
        ('TURN', 'Turn'),
        ('RIVER', 'River'),
        ('SHOWDOWN', 'Showdown'),
    ]

    table = models.ForeignKey(PokerTable, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=GAME_STATUS_CHOICES, default='WAITING')
    phase = models.CharField(max_length=20, choices=GAME_PHASE_CHOICES, null=True, blank=True)
    pot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_bet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dealer_position = models.IntegerField(default=0)
    current_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='games_to_play')
    community_cards = models.CharField(max_length=100, blank=True, null=True)  # Stored as JSON string
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Game at {self.table.name}"
    
    def set_community_cards(self, cards_list):
        self.community_cards = json.dumps(cards_list)
    
    def get_community_cards(self):
        if self.community_cards:
            return json.loads(self.community_cards)
        return []

class PlayerGame(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    seat_position = models.IntegerField()
    stack = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    cards = models.CharField(max_length=50, blank=True, null=True)  # Stored as JSON string
    current_bet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_bet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['game', 'seat_position']
    
    def __str__(self):
        return f"{self.player} at {self.game}"
    
    def set_cards(self, cards_list):
        self.cards = json.dumps(cards_list)
    
    def get_cards(self):
        if self.cards:
            return json.loads(self.cards)
        return []
    
class GameAction(models.Model):
    ACTION_CHOICES = [
        ('FOLD', 'Fold'),
        ('CHECK', 'Check'),
        ('CALL', 'Call'),
        ('BET', 'Bet'),
        ('RAISE', 'Raise'),
    ]
    
    player_game = models.ForeignKey(PlayerGame, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.action_type in ['BET', 'RAISE']:
            return f"{self.player_game.player} {self.action_type} {self.amount}"
        return f"{self.player_game.player} {self.action_type}"

# class Card(models.Model):
#     SUIT_CHOICES = [
#         ('S', 'Spades'),
#         ('H', 'Hearts'),
#         ('D', 'Diamonds'),
#         ('C', 'Clubs'),
#     ]
#     RANK_CHOICES = [
#         ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'),
#         ('8', '8'), ('9', '9'), ('10', '10'), ('J', 'Jack'), ('Q', 'Queen'),
#         ('K', 'King'), ('A', 'Ace'),
#     ]
#     suit = models.CharField(max_length=1, choices=SUIT_CHOICES)
#     rank = models.CharField(max_length=2, choices=RANK_CHOICES)
    
#     def __str__(self):
#         return f"{self.rank}{self.suit}"