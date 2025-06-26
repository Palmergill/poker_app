# poker_api/models.py
from django.db import models
from django.contrib.auth.models import User
import json

class PokerTable(models.Model):
    """Represents a poker table with betting limits and player capacity."""
    name = models.CharField(max_length=100)
    max_players = models.IntegerField(default=9)
    small_blind = models.DecimalField(max_digits=10, decimal_places=2)
    big_blind = models.DecimalField(max_digits=10, decimal_places=2)
    min_buy_in = models.DecimalField(max_digits=10, decimal_places=2)
    max_buy_in = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        """Returns the string representation of the poker table."""
        return self.name

class Player(models.Model):
    """Represents a poker player with their account balance."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        """Returns the string representation of the player."""
        return self.user.username

class Game(models.Model):
    """Represents a poker game instance with all game state information."""
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
        ('WAITING_FOR_PLAYERS', 'Waiting for players to be ready'),
    ]

    table = models.ForeignKey(PokerTable, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=GAME_STATUS_CHOICES, default='WAITING')
    phase = models.CharField(max_length=20, choices=GAME_PHASE_CHOICES, null=True, blank=True)
    pot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_bet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dealer_position = models.IntegerField(default=0)
    current_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='games_to_play')
    community_cards = models.CharField(max_length=100, blank=True, null=True)  # Stored as JSON string
    winner_info = models.TextField(blank=True, null=True)  # Stored as JSON string with winner details
    game_summary = models.TextField(blank=True, null=True)  # Stored as JSON string with final results when all players cash out
    hand_count = models.PositiveIntegerField(default=0)  # Tracks number of completed hands
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        """Returns the string representation of the game."""
        return f"Game at {self.table.name}"
    
    def set_community_cards(self, cards_list):
        """Stores community cards as JSON string."""
        self.community_cards = json.dumps(cards_list)
    
    def get_community_cards(self):
        """Retrieves community cards from JSON string."""
        if self.community_cards:
            return json.loads(self.community_cards)
        return []
    
    def set_winner_info(self, winner_data):
        """Stores winner information as JSON string."""
        self.winner_info = json.dumps(winner_data)
    
    def get_winner_info(self):
        """Retrieves winner information from JSON string."""
        if self.winner_info:
            return json.loads(self.winner_info)
        return None
    
    def set_game_summary(self, summary_data):
        """Stores game summary as JSON string."""
        self.game_summary = json.dumps(summary_data)
    
    def get_game_summary(self):
        """Retrieves game summary from JSON string."""
        if self.game_summary:
            return json.loads(self.game_summary)
        return None
    
    def generate_game_summary(self):
        """Generate and store game summary when game ends."""
        from django.utils import timezone
        
        # Get all players who participated in this game
        all_players = PlayerGame.objects.filter(game=self)
        
        summary_data = {
            'game_id': self.id,
            'table_name': self.table.name,
            'completed_at': timezone.now().isoformat(),
            'total_hands': self.hand_count,
            'players': []
        }
        
        for pg in all_players:
            win_loss = pg.calculate_win_loss()
            player_data = {
                'player_name': pg.player.user.username,
                'player_id': pg.player.id,
                'starting_stack': float(pg.starting_stack) if pg.starting_stack else 0,
                'final_stack': float(pg.final_stack) if pg.final_stack is not None else float(pg.stack),
                'win_loss': float(win_loss) if win_loss is not None else 0,
                'status': pg.status
            }
            summary_data['players'].append(player_data)
        
        # Sort players by win/loss (highest to lowest)
        summary_data['players'].sort(key=lambda x: x['win_loss'], reverse=True)
        
        self.set_game_summary(summary_data)
        self.status = 'FINISHED'
        self.save()
        
        return summary_data

class PlayerGame(models.Model):
    """Represents a player's participation in a specific game."""
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    seat_position = models.IntegerField()
    stack = models.DecimalField(max_digits=10, decimal_places=2)
    starting_stack = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Initial stack when joining game
    final_stack = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Final stack when cashing out/leaving
    is_active = models.BooleanField(default=True)
    cashed_out = models.BooleanField(default=False)  # Player has cashed out but still at table
    cards = models.CharField(max_length=50, blank=True, null=True)  # Stored as JSON string
    current_bet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_bet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ready_for_next_hand = models.BooleanField(default=False)  # Player ready for next hand
    
    class Meta:
        unique_together = [
            ['game', 'seat_position'],  # Each seat can only be occupied by one player
            ['game', 'player']          # Each player can only join a game once
        ]
    
    def __str__(self):
        """Returns the string representation of the player game."""
        return f"{self.player} at {self.game}"
    
    def set_cards(self, cards_list):
        """Stores player's hole cards as JSON string."""
        self.cards = json.dumps(cards_list)
    
    def get_cards(self):
        """Retrieves player's hole cards from JSON string."""
        if self.cards:
            return json.loads(self.cards)
        return []
    
    def cash_out(self):
        """Cash out the player - they become inactive but stay at the table."""
        self.is_active = False
        self.cashed_out = True
        self.save()
    
    def buy_back_in(self, amount):
        """Buy back in - only available if player is cashed out."""
        if self.cashed_out:
            self.stack = amount
            self.is_active = True
            self.cashed_out = False
            self.save()
    
    def can_leave_table(self):
        """Check if player can leave the table (only if cashed out)."""
        return self.cashed_out
    
    def can_buy_back_in(self):
        """Check if player can buy back in (only if cashed out)."""
        return self.cashed_out
    
    @property
    def status(self):
        """Return the current status of the player."""
        if self.cashed_out:
            return 'CASHED_OUT'
        elif self.is_active:
            return 'ACTIVE'
        else:
            return 'INACTIVE'
    
    def calculate_win_loss(self):
        """Calculate win/loss amount for this player in the game."""
        if self.starting_stack is None:
            return None
        
        # If still playing, use current stack
        if not self.cashed_out and self.final_stack is None:
            current_amount = self.stack
        else:
            # Use final stack if available, otherwise current stack
            current_amount = self.final_stack if self.final_stack is not None else self.stack
        
        return current_amount - self.starting_stack
    
class GameAction(models.Model):
    """Represents a player's action during a poker game."""
    ACTION_CHOICES = [
        ('FOLD', 'Fold'),
        ('CHECK', 'Check'),
        ('CALL', 'Call'),
        ('BET', 'Bet'),
        ('RAISE', 'Raise'),
    ]
    
    PHASE_CHOICES = [
        ('PREFLOP', 'Pre-flop'),
        ('FLOP', 'Flop'),
        ('TURN', 'Turn'),
        ('RIVER', 'River'),
    ]
    
    player_game = models.ForeignKey(PlayerGame, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='PREFLOP')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        """Returns the string representation of the game action."""
        if self.action_type in ['BET', 'RAISE']:
            return f"{self.player_game.player} {self.action_type} {self.amount}"
        return f"{self.player_game.player} {self.action_type}"

class HandHistory(models.Model):
    """Stores historical data for completed poker hands."""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='hand_history')
    hand_number = models.PositiveIntegerField()
    winner_info = models.TextField()  # JSON data with winner details
    pot_amount = models.DecimalField(max_digits=10, decimal_places=2)
    community_cards = models.CharField(max_length=100, blank=True, null=True)  # JSON
    final_phase = models.CharField(max_length=20, choices=Game.GAME_PHASE_CHOICES)
    player_cards = models.TextField()  # JSON data with all player hole cards
    actions = models.TextField()  # JSON data with all actions taken during hand
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['game', 'hand_number']
        ordering = ['-completed_at']
    
    def __str__(self):
        """Returns the string representation of the hand history."""
        return f"Hand {self.hand_number} - Game {self.game.id}"
    
    def set_winner_info(self, winner_data):
        """Stores winner information as JSON string."""
        self.winner_info = json.dumps(winner_data)
    
    def get_winner_info(self):
        """Retrieves winner information from JSON string."""
        if self.winner_info:
            return json.loads(self.winner_info)
        return None
    
    def set_player_cards(self, cards_data):
        """Stores all players' hole cards as JSON string."""
        self.player_cards = json.dumps(cards_data)
    
    def get_player_cards(self):
        """Retrieves all players' hole cards from JSON string."""
        if self.player_cards:
            return json.loads(self.player_cards)
        return {}
    
    def set_actions(self, actions_data):
        """Stores all game actions as JSON string."""
        self.actions = json.dumps(actions_data)
    
    def get_actions(self):
        """Retrieves all game actions from JSON string."""
        if self.actions:
            return json.loads(self.actions)
        return []
    
    def set_community_cards(self, cards_list):
        """Stores community cards as JSON string."""
        self.community_cards = json.dumps(cards_list)
    
    def get_community_cards(self):
        """Retrieves community cards from JSON string."""
        if self.community_cards:
            return json.loads(self.community_cards)
        return []

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