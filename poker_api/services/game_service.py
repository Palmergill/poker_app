# poker_api/services/game_service.py
from django.db import transaction
from ..models import Game, PlayerGame, GameAction, Player
from ..utils.card_utils import Deck, Card
from ..utils.hand_evaluator import HandEvaluator
import random
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from decimal import Decimal

class GameService:
    """
    Service for managing poker games.
    """
    
    @staticmethod
    @transaction.atomic
    def create_game(table, players):
        """
        Create a new game at the specified table with the given players.
        
        Args:
            table: PokerTable instance
            players: List of Player instances
        
        Returns:
            Game instance
        """
        # Create new game
        game = Game.objects.create(
            table=table,
            status='WAITING',
            pot=0,
            current_bet=0,
            dealer_position=0,
        )
        
        # Add players to the game
        for i, player in enumerate(players):
            PlayerGame.objects.create(
                player=player,
                game=game,
                seat_position=i,
                stack=min(player.balance, table.max_buy_in),
                is_active=True
            )
        
        return game
    
    @staticmethod
    @transaction.atomic
    def start_game(game_id):
        """
        Start a poker game.
        
        Args:
            game_id: ID of the game to start
        
        Returns:
            Updated Game instance
        """
        game = Game.objects.get(id=game_id)
        
        # Check if game can be started
        if game.status != 'WAITING':
            raise ValueError("Game has already started or finished")
        
        player_games = PlayerGame.objects.filter(game=game, is_active=True)
        if player_games.count() < 2:
            raise ValueError("Not enough players to start the game")
        
        # Initialize the deck
        deck = Deck()
        deck.shuffle()
        
        # Randomly assign dealer position
        game.dealer_position = random.randint(0, player_games.count() - 1)
        
        # Set game status and phase
        game.status = 'PLAYING'
        game.phase = 'PREFLOP'
        
        # Determine small and big blind positions
        num_players = player_games.count()
        small_blind_pos = (game.dealer_position + 1) % num_players
        big_blind_pos = (game.dealer_position + 2) % num_players
        
        # Assign positions
        player_games_list = list(player_games.order_by('seat_position'))
        
        # Post blinds
        small_blind_player = player_games_list[small_blind_pos]
        big_blind_player = player_games_list[big_blind_pos]
        
        # Post small blind
        small_blind_amount = min(game.table.small_blind, small_blind_player.stack)
        small_blind_player.stack -= small_blind_amount
        small_blind_player.current_bet = small_blind_amount
        small_blind_player.total_bet = small_blind_amount
        small_blind_player.save()
        
        # Post big blind
        big_blind_amount = min(game.table.big_blind, big_blind_player.stack)
        big_blind_player.stack -= big_blind_amount
        big_blind_player.current_bet = big_blind_amount
        big_blind_player.total_bet = big_blind_amount
        big_blind_player.save()
        
        # Set current bet to big blind
        game.current_bet = big_blind_amount
        
        # Deal cards to players
        for player_game in player_games:
            cards = deck.deal(2)
            card_strings = [str(card) for card in cards]
            player_game.set_cards(card_strings)
            player_game.save()
        
        # Set current player (after big blind)
        current_player_pos = (big_blind_pos + 1) % num_players
        game.current_player = player_games_list[current_player_pos].player
        
        # Save game state
        game.save()
        
        # Broadcast game update
        GameService.broadcast_game_update(game_id)
        
        return game
    
    @staticmethod
    @transaction.atomic
    def process_action(game_id, player_id, action_type, amount=0):
        """
        Process a player's action in the game.
        
        Args:
            game_id: ID of the game
            player_id: ID of the player taking action
            action_type: Type of action ('FOLD', 'CHECK', 'CALL', 'BET', 'RAISE')
            amount: Amount for bet or raise (only used for BET and RAISE)
        
        Returns:
            Updated Game instance
        """
        game = Game.objects.get(id=game_id)
        
        # Validate game is in progress
        if game.status != 'PLAYING':
            raise ValueError("Game is not in progress")
        
        # Validate it's the player's turn
        if game.current_player_id != player_id:
            raise ValueError("Not your turn to act")
        
        # Get player's game entry
        try:
            player_game = PlayerGame.objects.get(game=game, player_id=player_id, is_active=True)
        except PlayerGame.DoesNotExist:
            raise ValueError("Player not in this game or not active")
        
        # Convert amount to Decimal for consistency
        if amount:
            amount = Decimal(str(amount))
            
        # Process the action
        if action_type == 'FOLD':
            GameService._handle_fold(game, player_game)
        elif action_type == 'CHECK':
            GameService._handle_check(game, player_game)
        elif action_type == 'CALL':
            GameService._handle_call(game, player_game)
        elif action_type == 'BET':
            GameService._handle_bet(game, player_game, amount)
        elif action_type == 'RAISE':
            GameService._handle_raise(game, player_game, amount)
        else:
            raise ValueError(f"Invalid action: {action_type}")
        
        # Record the action
        GameAction.objects.create(
            player_game=player_game,
            action_type=action_type,
            amount=amount if action_type in ['BET', 'RAISE', 'CALL'] else 0
        )
        
        # Move to next player or phase
        GameService._advance_game(game)
        
        return game
    
    @staticmethod
    def _handle_fold(game, player_game):
        """Handle a fold action."""
        player_game.is_active = False
        player_game.save()
        
        # Check if only one player left
        active_players = PlayerGame.objects.filter(game=game, is_active=True)
        if active_players.count() == 1:
            GameService._end_hand(game)
    
    @staticmethod
    def _handle_check(game, player_game):
        """Handle a check action."""
        if player_game.current_bet < game.current_bet:
            raise ValueError("Cannot check when there is a bet to call")
    
    @staticmethod
    def _handle_call(game, player_game):
        """Handle a call action."""
        # Convert all values to Decimal for consistent operations
        current_bet = game.current_bet
        player_current_bet = player_game.current_bet
        player_stack = player_game.stack
        
        call_amount = min(current_bet - player_current_bet, player_stack)
        
        player_game.stack -= call_amount
        player_game.current_bet += call_amount
        player_game.total_bet += call_amount
        player_game.save()
    
    @staticmethod
    def _handle_bet(game, player_game, amount):
        """Handle a bet action."""
        if game.current_bet > 0:
            raise ValueError("Cannot bet when there is already a bet, use 'RAISE' instead")
        
        min_bet = game.table.big_blind
        if amount < min_bet:
            raise ValueError(f"Bet must be at least the big blind: {min_bet}")
        
        bet_amount = min(amount, player_game.stack)
        player_game.stack -= bet_amount
        player_game.current_bet = bet_amount
        player_game.total_bet += bet_amount
        player_game.save()
        
        game.current_bet = bet_amount
        game.save()
    
    @staticmethod
    def _handle_raise(game, player_game, amount):
        """Handle a raise action."""
        if game.current_bet == 0:
            raise ValueError("Cannot raise when there is no bet, use 'BET' instead")
        
        # Calculate total amount player needs to put in
        total_amount = amount
        current_player_bet = player_game.current_bet
        raise_amount = total_amount - current_player_bet
        
        # Validate raise amount
        min_raise = game.current_bet * 2
        if total_amount < min_raise:
            raise ValueError(f"Raise must be at least double the current bet: {min_raise}")
        
        # Cap raise at player's stack
        raise_amount = min(raise_amount, player_game.stack)
        total_bet = current_player_bet + raise_amount
        
        player_game.stack -= raise_amount
        player_game.current_bet = total_bet
        player_game.total_bet += raise_amount
        player_game.save()
        
        game.current_bet = total_bet
        game.save()
    
    @staticmethod
    def _advance_game(game):
        """Advance the game to the next player or phase."""
        active_players = list(PlayerGame.objects.filter(game=game, is_active=True).order_by('seat_position'))
        
        if len(active_players) == 1:
            # Only one player left
            GameService._end_hand(game)
            return
        
        # Find current player's position in the active players list
        current_pos = None
        for i, pg in enumerate(active_players):
            if pg.player_id == game.current_player_id:
                current_pos = i
                break
        
        # If current player is not found in active players (e.g., they just folded),
        # find the next active player by seat position
        if current_pos is None:
            # Get the current player's seat position
            try:
                current_player_game = PlayerGame.objects.get(game=game, player_id=game.current_player_id)
                current_seat = current_player_game.seat_position
                
                # Find the next active player by seat position
                next_player = None
                for pg in active_players:
                    if pg.seat_position > current_seat:
                        next_player = pg
                        break
                
                # If no player found after current seat, wrap around to first active player
                if next_player is None:
                    next_player = active_players[0]
                    
                game.current_player = next_player.player
            except PlayerGame.DoesNotExist:
                # Fallback: set to first active player
                game.current_player = active_players[0].player
        else:
            # Move to next player in the active players list
            next_pos = (current_pos + 1) % len(active_players)
            game.current_player = active_players[next_pos].player
        
        game.save()
        
        # Check if betting round is complete
        betting_complete = True
        current_bet = game.current_bet
        
        # Round is complete when all active players have matched the current bet or are all-in
        for pg in active_players:
            if pg.current_bet < current_bet and pg.stack > 0:
                betting_complete = False
                break
        
        # Check if we've completed a full round (everyone has had a chance to act)
        # This happens when we're back to the player who started the betting round
        if betting_complete:
            # In preflop, the betting round ends when action returns to the big blind
            # In other phases, it ends when action returns to the first player to act
            
            # For simplicity, if all bets are matched and we have active players, advance phase
            if len(active_players) > 1:
                GameService._move_to_next_phase(game)
            else:
                # Only one player left, end the hand
                GameService._end_hand(game)
    
    @staticmethod
    @transaction.atomic
    def _move_to_next_phase(game):
        """Move to the next phase of the game."""
        # Add all bets to the pot
        active_players = PlayerGame.objects.filter(game=game, is_active=True)
        for pg in active_players:
            game.pot += pg.current_bet
            pg.current_bet = 0
            pg.save()
        
        # Reset current bet
        game.current_bet = 0
        
        # Deal community cards based on current phase
        if game.phase == 'PREFLOP':
            # Deal the flop (3 cards)
            deck = GameService._get_game_deck(game)
            flop_cards = [str(card) for card in deck.deal(3)]
            game.set_community_cards(flop_cards)
            game.phase = 'FLOP'
        elif game.phase == 'FLOP':
            # Deal the turn (1 card)
            deck = GameService._get_game_deck(game)
            community_cards = game.get_community_cards()
            community_cards.append(str(deck.deal()))
            game.set_community_cards(community_cards)
            game.phase = 'TURN'
        elif game.phase == 'TURN':
            # Deal the river (1 card)
            deck = GameService._get_game_deck(game)
            community_cards = game.get_community_cards()
            community_cards.append(str(deck.deal()))
            game.set_community_cards(community_cards)
            game.phase = 'RIVER'
        elif game.phase == 'RIVER':
            # Move to showdown
            game.phase = 'SHOWDOWN'
            # Evaluate hands and determine winner
            GameService._showdown(game)
        
        # Set the first active player after the dealer to act first
        if game.phase != 'SHOWDOWN':
            dealer_pos = game.dealer_position
            active_players = list(active_players.order_by('seat_position'))
            
            # Find the first active player after the dealer
            for i in range(1, len(active_players) + 1):
                next_pos = (dealer_pos + i) % len(active_players)
                game.current_player = active_players[next_pos].player
                break
        
        game.save()
        
        # Broadcast game update
        GameService.broadcast_game_update(game.id)
    
    @staticmethod
    def _get_game_deck(game):
        """Get a deck with the appropriate cards removed."""
        # Create a new deck
        deck = Deck()
        
        # Remove community cards
        community_cards = game.get_community_cards()
        for card_str in community_cards:
            card = Card(card_str[0:-1], card_str[-1])
            deck.cards.remove(card)
        
        # Remove player cards
        player_games = PlayerGame.objects.filter(game=game)
        for pg in player_games:
            for card_str in pg.get_cards():
                card = Card(card_str[0:-1], card_str[-1])
                if card in deck.cards:
                    deck.cards.remove(card)
        
        return deck
    
    @staticmethod
    def _showdown(game):
        """Determine the winner(s) at showdown."""
        # Get active players
        active_players = PlayerGame.objects.filter(game=game, is_active=True)
        
        # If only one active player, they win
        if active_players.count() == 1:
            winner = active_players.first()
            winner.stack += game.pot
            winner.save()
            game.pot = 0
            game.save()
            return
        
        # Evaluate each player's hand
        community_cards = [Card(card[0:-1], card[-1]) for card in game.get_community_cards()]
        
        best_hands = {}
        for pg in active_players:
            # Convert string cards to Card objects
            hole_cards = [Card(card[0:-1], card[-1]) for card in pg.get_cards()]
            
            # Combine with community cards
            all_cards = hole_cards + community_cards
            
            # Evaluate best hand
            hand_rank, hand_value, hand_name = HandEvaluator.evaluate_hand(all_cards)
            best_hands[pg.id] = (hand_rank, hand_value, hand_name, pg)
        
        # Sort by hand strength
        sorted_hands = sorted(best_hands.values(), key=lambda x: (x[0], x[1]))
        
        # Find winners (players with the same best hand)
        best_hand = sorted_hands[0]
        winners = [pg for rank, value, name, pg in sorted_hands if (rank, value) == (best_hand[0], best_hand[1])]
        
        # Split pot among winners
        win_amount = game.pot / Decimal(len(winners))
        for winner in winners:
            winner.stack += win_amount
            winner.save()
        
        # Reset pot
        game.pot = 0
        game.save()
        
        # Broadcast game update
        GameService.broadcast_game_update(game.id)
    
    @staticmethod
    def _end_hand(game):
        """End the current hand when only one player remains."""
        # Award pot to the last remaining player
        winner = PlayerGame.objects.filter(game=game, is_active=True).first()
        if winner:
            winner.stack += game.pot
            winner.save()
        
        # Reset pot
        game.pot = 0
        game.phase = 'SHOWDOWN'
        game.save()
        
        # Broadcast game update
        GameService.broadcast_game_update(game.id)

    @staticmethod
    def broadcast_game_update(game_id):
        """
        Broadcast game update to all connected clients.
        For card visibility, we'll send all data and let the frontend handle visibility.
        """
        from ..serializers import GameSerializer
        
        game = Game.objects.get(id=game_id)
        
        # Create serializer without user context - cards will be handled on frontend
        serializer = GameSerializer(game)
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'game_{game_id}',
            {
                'type': 'game_update', 
                'data': serializer.data
            }
        )

        # Call this method after game state changes, for example:
        # At the end of process_action
        # At the end of start_game
        # At the end of _move_to_next_phase
        # At the end of _showdown
        # At the end of _end_hand