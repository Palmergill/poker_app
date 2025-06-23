# poker_api/services/game_service.py
from django.db import transaction
from ..models import Game, PlayerGame, GameAction, Player, HandHistory
from ..utils.card_utils import Deck, Card
from ..utils.hand_evaluator import HandEvaluator
import random
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from decimal import Decimal
from django.utils import timezone

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
        
        # Add blinds to pot immediately
        game.pot += small_blind_amount + big_blind_amount
        
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
            amount=amount if action_type in ['BET', 'RAISE', 'CALL'] else 0,
            phase=game.phase
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
        # Player can check if they've already matched the current bet
        # This allows big blind to check pre-flop and players to check after calling
        if player_game.current_bet != game.current_bet:
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
        
        # Add call amount to pot immediately
        game.pot += call_amount
        game.save()
    
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
        
        # Add bet amount to pot immediately
        game.pot += bet_amount
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
        
        # Add raise amount to pot immediately
        game.pot += raise_amount
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
        # Get the last action to see if we need to track who started betting this round
        last_action = GameAction.objects.filter(player_game__game=game).order_by('-timestamp').first()
        
        # In preflop, betting round ends when action returns to big blind (if they haven't acted beyond posting blind)
        # In other phases, betting round ends when all players have matched the current bet
        betting_complete = GameService._is_betting_round_complete(game, active_players)
        
        if betting_complete:
            if len(active_players) > 1:
                GameService._move_to_next_phase(game)
            else:
                # Only one player left, end the hand
                GameService._end_hand(game)
    
    @staticmethod
    def _is_betting_round_complete(game, active_players):
        """Check if the current betting round is complete."""
        current_bet = game.current_bet
        
        # First check: all active players must have matched the current bet or be all-in
        for pg in active_players:
            if pg.current_bet < current_bet and pg.stack > 0:
                return False
        
        # Second check: determine if all players have had proper opportunity to act
        # Find when the current hand started (after the last hand history was saved)
        last_hand_history = HandHistory.objects.filter(game=game).order_by('-completed_at').first()
        current_hand_start = last_hand_history.completed_at if last_hand_history else game.created_at
        
        # Get the most recent bet or raise action in current phase (only from current hand)
        recent_bet_actions = GameAction.objects.filter(
            player_game__game=game,
            player_game__is_active=True,
            phase=game.phase,
            action_type__in=['BET', 'RAISE'],
            timestamp__gt=current_hand_start
        ).order_by('-timestamp')
        
        if recent_bet_actions.exists():
            # If there was a bet/raise, all other active players must have acted after it
            last_bet_raise = recent_bet_actions.first()
            
            for pg in active_players:
                if pg == last_bet_raise.player_game:
                    continue  # Skip the player who made the bet/raise
                
                # Check if this player has acted after the last bet/raise
                player_actions_after_bet = GameAction.objects.filter(
                    player_game=pg,
                    phase=game.phase,
                    timestamp__gt=last_bet_raise.timestamp
                )
                
                # Player must act unless they're all-in
                if not player_actions_after_bet.exists() and pg.stack > 0:
                    return False
        else:
            # No bets/raises in this phase - all players must have had chance to act
            all_actions = GameAction.objects.filter(
                player_game__game=game,
                player_game__is_active=True,
                phase=game.phase,
                timestamp__gt=current_hand_start
            )
            
            # All active players with chips must have acted
            for pg in active_players:
                if pg.stack > 0:  # Only check players who can still act
                    player_actions = all_actions.filter(player_game=pg)
                    if not player_actions.exists():
                        return False
        
        return True
    
    @staticmethod
    @transaction.atomic
    def _move_to_next_phase(game):
        """Move to the next phase of the game."""
        # Reset current bets (pot already updated during betting)
        active_players = PlayerGame.objects.filter(game=game, is_active=True)
        for pg in active_players:
            pg.current_bet = 0
            pg.save()
        
        # Reset current bet
        game.current_bet = 0
        
        # Clear actions from previous phase to reset action tracking
        # Note: We keep actions for history but track per-phase actions differently
        
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
        # Create a new deck and shuffle it for randomness
        deck = Deck()
        deck.shuffle()
        
        # Remove community cards
        community_cards = game.get_community_cards()
        for card_str in community_cards:
            # Handle parsing - rank can be 1-2 characters, suit is always last
            rank = card_str[:-1]
            suit = card_str[-1]
            card = Card(rank, suit)
            if card in deck.cards:
                deck.cards.remove(card)
        
        # Remove player cards
        player_games = PlayerGame.objects.filter(game=game)
        for pg in player_games:
            for card_str in pg.get_cards():
                # Handle parsing - rank can be 1-2 characters, suit is always last
                rank = card_str[:-1]
                suit = card_str[-1]
                card = Card(rank, suit)
                if card in deck.cards:
                    deck.cards.remove(card)
        
        return deck
    
    @staticmethod
    def _get_showdown_order(game, active_players):
        """Determine the order players should show their cards at showdown.
        
        Rules from CLAUDE.md:
        1. The last player to bet or raise shows their cards first
        2. If there was no betting on the river, player closest to left of dealer shows first
        """
        # Find the last bet or raise action on the river
        last_aggressive_action = GameAction.objects.filter(
            player_game__game=game,
            player_game__is_active=True,
            phase='RIVER',
            action_type__in=['BET', 'RAISE']
        ).order_by('-timestamp').first()
        
        if last_aggressive_action:
            # Last aggressive player shows first
            first_to_show = last_aggressive_action.player_game
        else:
            # No betting on river - find player closest to left of dealer
            dealer_pos = game.dealer_position
            active_players_list = list(active_players.order_by('seat_position'))
            
            # Find first active player after dealer
            first_to_show = None
            for i in range(1, len(active_players_list) + 1):
                next_pos = (dealer_pos + i) % len(active_players_list)
                candidate = None
                for pg in active_players_list:
                    if pg.seat_position == next_pos:
                        candidate = pg
                        break
                if candidate:
                    first_to_show = candidate
                    break
            
            if not first_to_show:
                first_to_show = active_players.first()
        
        # Create ordered list starting with first_to_show
        ordered_players = [first_to_show]
        remaining_players = [pg for pg in active_players if pg != first_to_show]
        ordered_players.extend(remaining_players)
        
        return ordered_players
    
    @staticmethod
    def _showdown(game):
        """Determine the winner(s) at showdown."""
        # Get active players
        active_players = PlayerGame.objects.filter(game=game, is_active=True)
        
        # Determine showdown order according to Texas Hold'em rules
        showdown_order = GameService._get_showdown_order(game, active_players)
        
        # If only one active player, they win
        if active_players.count() == 1:
            winner = active_players.first()
            winner.stack += game.pot
            winner.save()
            
            # Store winner information
            winner_data = {
                'type': 'single_winner',
                'winners': [{
                    'player_name': winner.player.user.username,
                    'player_id': winner.player.id,
                    'winning_amount': float(game.pot),
                    'reason': 'All other players folded'
                }],
                'pot_amount': float(game.pot)
            }
            game.set_winner_info(winner_data)
            game.pot = 0
            game.save()
            
            # Broadcast game update
            GameService.broadcast_game_update(game.id)
            return
        
        # Evaluate each player's hand
        community_cards = [GameService._parse_card(card) for card in game.get_community_cards()]
        
        best_hands = {}
        for pg in active_players:
            # Convert string cards to Card objects
            hole_cards = [GameService._parse_card(card) for card in pg.get_cards()]
            
            # Combine with community cards
            all_cards = hole_cards + community_cards
            
            # Evaluate best hand
            hand_rank, hand_value, hand_name = HandEvaluator.evaluate_hand(all_cards)
            best_hands[pg.id] = (hand_rank, hand_value, hand_name, pg)
        
        # Sort by hand strength (lower rank is better, higher value within rank is better)
        sorted_hands = sorted(best_hands.values(), key=lambda x: (x[0], [-v for v in x[1]]))
        
        # Find winners (players with the same best hand)
        best_hand = sorted_hands[0]
        winners = [pg for rank, value, name, pg in sorted_hands if (rank, value) == (best_hand[0], best_hand[1])]
        
        # Split pot among winners
        win_amount = game.pot / Decimal(len(winners))
        for winner in winners:
            winner.stack += win_amount
            winner.save()
        
        # Store winner information
        winner_data = {
            'type': 'showdown_winner',
            'winners': [{
                'player_name': winner.player.user.username,
                'player_id': winner.player.id,
                'winning_amount': float(win_amount),
                'hand_name': best_hand[2],
                'hole_cards': winner.get_cards()
            } for winner in winners],
            'pot_amount': float(game.pot),
            'community_cards': game.get_community_cards(),
            'showdown_order': [{
                'player_name': pg.player.user.username,
                'player_id': pg.player.id,
                'show_order': idx + 1
            } for idx, pg in enumerate(showdown_order)],
            'all_hands': [{
                'player_name': pg.player.user.username,
                'hand_name': hand_name,
                'hole_cards': pg.get_cards(),
                'hand_rank': hand_rank
            } for hand_rank, hand_value, hand_name, pg in sorted_hands]
        }
        game.set_winner_info(winner_data)
        
        # Reset pot
        game.pot = 0
        game.save()
        
        # Start new hand
        GameService._start_new_hand(game)
        
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
            
            # Store winner information
            winner_data = {
                'type': 'single_winner',
                'winners': [{
                    'player_name': winner.player.user.username,
                    'player_id': winner.player.id,
                    'winning_amount': float(game.pot),
                    'reason': 'All other players folded'
                }],
                'pot_amount': float(game.pot)
            }
            game.set_winner_info(winner_data)
        
        # Reset pot
        game.pot = 0
        game.phase = 'SHOWDOWN'
        game.save()
        
        # Start new hand
        GameService._start_new_hand(game)
        
        # Broadcast game update
        GameService.broadcast_game_update(game.id)

    @staticmethod
    def _parse_card(card_str):
        """Parse a card string like 'AH', '10C', 'KS' into a Card object."""
        if len(card_str) == 2:
            # Single character rank like 'A', 'K', 'Q', 'J', '2'-'9'
            rank = card_str[0]
            suit = card_str[1]
        elif len(card_str) == 3 and card_str.startswith('10'):
            # Special case for '10'
            rank = '10'
            suit = card_str[2]
        else:
            raise ValueError(f"Invalid card format: {card_str}")
        
        return Card(rank, suit)

    @staticmethod
    def _save_hand_history(game):
        """Save the completed hand to history before starting a new hand."""
        if not game.winner_info:
            return
        
        # Get current hand number
        current_hand_number = game.hand_count + 1
        
        # Collect all player cards
        player_cards = {}
        for pg in PlayerGame.objects.filter(game=game):
            if pg.cards:
                player_cards[pg.player.user.username] = pg.get_cards()
        
        # Collect all actions for this hand (since last hand history save)
        actions = []
        last_hand_history = HandHistory.objects.filter(game=game).order_by('-hand_number').first()
        if last_hand_history:
            # Get actions since the last hand history was saved
            actions_query = GameAction.objects.filter(
                player_game__game=game,
                timestamp__gt=last_hand_history.completed_at
            ).order_by('timestamp')
        else:
            # This is the first hand, get all actions
            actions_query = GameAction.objects.filter(
                player_game__game=game
            ).order_by('timestamp')
        
        for action in actions_query:
            actions.append({
                'player': action.player_game.player.user.username,
                'action': action.action_type,
                'amount': float(action.amount) if action.amount else 0,
                'phase': action.phase,
                'timestamp': action.timestamp.isoformat()
            })
        
        # Create hand history record
        hand_history = HandHistory.objects.create(
            game=game,
            hand_number=current_hand_number,
            pot_amount=game.pot,
            final_phase=game.phase,
            completed_at=timezone.now()
        )
        
        # Set JSON data
        hand_history.set_winner_info(game.get_winner_info())
        hand_history.set_player_cards(player_cards)
        hand_history.set_actions(actions)
        if game.community_cards:
            hand_history.set_community_cards(game.get_community_cards())
        
        hand_history.save()
        
        # Increment hand count
        game.hand_count = current_hand_number
        game.save()
        
        # Console log the completed hand history
        winner_info = hand_history.get_winner_info()
        print("\n" + "="*60)
        print(f"🃏 HAND #{current_hand_number} COMPLETED - Table: {game.table.name}")
        print("="*60)
        print(f"💰 Pot Amount: ${hand_history.pot_amount}")
        print(f"🎯 Final Phase: {hand_history.final_phase}")
        print(f"⏰ Completed: {hand_history.completed_at}")
        
        # Winner information
        if winner_info and 'winners' in winner_info:
            print(f"\n🏆 WINNER(S):")
            for i, winner in enumerate(winner_info['winners'], 1):
                print(f"   {i}. {winner['player_name']} - ${winner['winning_amount']}")
                if 'hand_name' in winner:
                    print(f"      Hand: {winner['hand_name']}")
                if 'reason' in winner:
                    print(f"      Reason: {winner['reason']}")
        
        # Community cards
        community_cards = hand_history.get_community_cards()
        if community_cards:
            print(f"\n🎴 Community Cards: {', '.join(community_cards)}")
        
        # Player hole cards
        player_cards = hand_history.get_player_cards()
        if player_cards:
            print(f"\n👥 Player Hole Cards:")
            for player_name, cards in player_cards.items():
                print(f"   {player_name}: {', '.join(cards)}")
        
        # Actions summary
        actions = hand_history.get_actions()
        if actions:
            print(f"\n📋 Actions Summary ({len(actions)} total):")
            current_phase = None
            for action in actions:
                if action['phase'] != current_phase:
                    current_phase = action['phase']
                    print(f"\n   {current_phase}:")
                amount_str = f" ${action['amount']}" if action['amount'] > 0 else ""
                print(f"     {action['player']}: {action['action']}{amount_str}")
        
        print("="*60)
        print(f"🎮 Game continues... Next hand will be #{current_hand_number + 1}")
        print("="*60 + "\n")

    @staticmethod
    @transaction.atomic
    def _start_new_hand(game):
        """Start a new hand after the previous one ended."""
        # Check if we have enough players with money to continue
        player_games = PlayerGame.objects.filter(game=game)
        players_with_money = [pg for pg in player_games if pg.stack > 0]
        
        if len(players_with_money) < 2:
            # End the game if not enough players have money
            game.status = 'FINISHED'
            game.save()
            return
        
        # Reset players who have money to active and clear their cards
        for pg in player_games:
            if pg.stack > 0:
                pg.is_active = True
                pg.cards = None
                pg.current_bet = 0
                pg.total_bet = 0
                pg.save()
            else:
                pg.is_active = False
                pg.save()
        
        # Save hand history before starting new hand
        GameService._save_hand_history(game)
        
        # Get active players (those with money)
        active_players = PlayerGame.objects.filter(game=game, is_active=True).order_by('seat_position')
        if active_players.count() >= 2:
            current_dealer_pos = game.dealer_position
            next_dealer_pos = (current_dealer_pos + 1) % active_players.count()
            game.dealer_position = next_dealer_pos
            
            # Reset game state
            game.phase = 'PREFLOP'
            game.community_cards = None
            game.current_bet = 0
            game.winner_info = None
            
            # Deal new cards
            deck = Deck()
            deck.shuffle()
            
            # Deal cards to players
            for pg in active_players:
                cards = deck.deal(2)
                card_strings = [str(card) for card in cards]
                pg.set_cards(card_strings)
                pg.save()
            
            # Post blinds
            num_players = active_players.count()
            small_blind_pos = (game.dealer_position + 1) % num_players
            big_blind_pos = (game.dealer_position + 2) % num_players
            
            active_players_list = list(active_players)
            
            # Post small blind
            small_blind_player = active_players_list[small_blind_pos]
            small_blind_amount = min(game.table.small_blind, small_blind_player.stack)
            small_blind_player.stack -= small_blind_amount
            small_blind_player.current_bet = small_blind_amount
            small_blind_player.total_bet = small_blind_amount
            small_blind_player.save()
            
            # Post big blind
            big_blind_player = active_players_list[big_blind_pos]
            big_blind_amount = min(game.table.big_blind, big_blind_player.stack)
            big_blind_player.stack -= big_blind_amount
            big_blind_player.current_bet = big_blind_amount
            big_blind_player.total_bet = big_blind_amount
            big_blind_player.save()
            
            # Add blinds to pot immediately  
            game.pot += small_blind_amount + big_blind_amount
            
            # Set current bet to big blind
            game.current_bet = big_blind_amount
            
            # Set current player (after big blind)
            current_player_pos = (big_blind_pos + 1) % num_players
            game.current_player = active_players_list[current_player_pos].player
            
            game.save()

    @staticmethod
    def broadcast_game_update(game_id):
        """
        Broadcast game update to all connected clients.
        For card visibility, we'll send all data and let the frontend handle visibility.
        """
        import logging
        from ..serializers import GameSerializer
        
        logger = logging.getLogger(__name__)
        game = Game.objects.get(id=game_id)
        
        # Log the broadcast details
        player_count = game.playergame_set.filter(is_active=True).count()
        logger.info(f"📡 Broadcasting update for game {game_id} - Status: {game.status}, Phase: {game.phase}, Players: {player_count}")
        
        # Check if this is a hand completion broadcast
        if hasattr(game, 'winner_info') and game.winner_info:
            winner_info = game.winner_info
            if winner_info.get('winners'):
                winner_name = winner_info['winners'][0].get('player_name', 'Unknown')
                logger.info(f"🏆 Broadcasting hand completion - Winner: {winner_name}")
        
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
        
        logger.debug(f"✅ Broadcast completed for game {game_id}")

        # Call this method after game state changes, for example:
        # At the end of process_action
        # At the end of start_game
        # At the end of _move_to_next_phase
        # At the end of _showdown
        # At the end of _end_hand