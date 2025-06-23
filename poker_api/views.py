# poker_api/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import PokerTable, Player, Game, PlayerGame, HandHistory
from .serializers import (
    PokerTableSerializer, PlayerSerializer, GameSerializer, PlayerGameSerializer,
    GameActionRequestSerializer, HandHistorySerializer
)
from .services.game_service import GameService
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class PokerTableViewSet(viewsets.ModelViewSet):
    queryset = PokerTable.objects.all()
    serializer_class = PokerTableSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def join_table(self, request, pk=None):
        """Join a table with a specified buy-in amount"""
        table = self.get_object()
        player, created = Player.objects.get_or_create(user=request.user)
        
        # Get buy-in amount from request and convert to Decimal
        buy_in = Decimal(str(request.data.get('buy_in', table.min_buy_in)))
        
        # Validate buy-in amount
        if buy_in < table.min_buy_in:
            return Response(
                {'error': f'Buy-in must be at least {table.min_buy_in}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if buy_in > table.max_buy_in:
            return Response(
                {'error': f'Buy-in cannot exceed {table.max_buy_in}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if buy_in > player.balance:
            return Response(
                {'error': 'Insufficient balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find active game at this table or create a new one
        game = Game.objects.filter(table=table, status='WAITING').first()
        if not game:
            game = Game.objects.create(table=table, status='WAITING')
        
        # Check if player is already at the table
        if PlayerGame.objects.filter(game=game, player=player).exists():
            return Response(
                {'error': 'You are already at this table'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if table is full
        if PlayerGame.objects.filter(game=game).count() >= table.max_players:
            return Response(
                {'error': 'Table is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find an empty seat
        occupied_seats = PlayerGame.objects.filter(game=game).values_list('seat_position', flat=True)
        for seat in range(table.max_players):
            if seat not in occupied_seats:
                # Join the table
                player.balance -= buy_in
                player.save()
                
                PlayerGame.objects.create(
                    player=player,
                    game=game,
                    seat_position=seat,
                    stack=buy_in,
                    is_active=True
                )
                
                serializer = GameSerializer(game, context={'request': request})
                return Response(serializer.data)
        
        return Response(
            {'error': 'No available seats'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        """Delete all poker tables (admin only)"""
        # Check if user is admin
        if not (request.user.is_superuser or request.user.is_staff):
            return Response(
                {'error': 'Admin privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get count before deletion
        table_count = PokerTable.objects.count()
        
        # Delete all tables (this will cascade delete related games and player games)
        PokerTable.objects.all().delete()
        
        return Response({
            'message': f'Successfully deleted {table_count} tables',
            'deleted_count': table_count
        })

class GameViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter games to include only those the player is part of"""
        player, created = Player.objects.get_or_create(user=self.request.user)
        return Game.objects.filter(playergame__player=player).distinct()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start the game"""
        game = self.get_object()
        
        try:
            GameService.start_game(game.id)
            GameService.broadcast_game_update(game.id)
            serializer = self.get_serializer(game)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='action')
    def perform_action(self, request, pk=None):
        """Take an action in the game"""
        game = self.get_object()
        player, created = Player.objects.get_or_create(user=request.user)
        
        # Validate action
        serializer = GameActionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"❌ Invalid action data from {request.user.username}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        action_type = serializer.validated_data['action_type']
        amount = serializer.validated_data.get('amount', 0)
        
        # Log the action attempt
        amount_str = f" ${amount}" if amount > 0 else ""
        logger.info(f"🎮 Game {game.id}: {request.user.username} attempting {action_type}{amount_str}")
        
        try:
            # Process the action
            updated_game = GameService.process_action(game.id, player.id, action_type, amount)
            logger.info(f"✅ Action processed successfully - Game status: {updated_game.status}, Phase: {updated_game.phase}")
            
            # Broadcast the update to all connected clients
            GameService.broadcast_game_update(game.id)
            logger.debug(f"📡 Game update broadcast for game {game.id}")
            
            # Return updated game state
            game_serializer = self.get_serializer(updated_game)
            return Response(game_serializer.data)
        except ValueError as e:
            logger.error(f"❌ Action failed for {request.user.username}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reset_game_state(self, request, pk=None):
        """Reset corrupted game state (debug utility)"""
        game = self.get_object()
        
        if game.status != 'PLAYING':
            return Response({'error': 'Game is not in progress'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get all active players
            active_players = list(PlayerGame.objects.filter(game=game, is_active=True).order_by('seat_position'))
            
            if len(active_players) < 2:
                return Response({'error': 'Not enough active players'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Reset current player to first active player
            game.current_player = active_players[0].player
            
            # If no current bet, reset to first player after dealer
            if game.current_bet == 0:
                dealer_pos = game.dealer_position
                # Find first active player after dealer
                for i in range(1, len(active_players) + 1):
                    next_pos = (dealer_pos + i) % len(active_players)
                    if next_pos < len(active_players):
                        game.current_player = active_players[next_pos].player
                        break
            
            game.save()
            
            # Broadcast update
            GameService.broadcast_game_update(game.id)
            
            serializer = self.get_serializer(game)
            return Response({
                'message': 'Game state reset successfully',
                'game': serializer.data
            })
            
        except Exception as e:
            return Response({'error': f'Failed to reset game state: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def debug_state(self, request, pk=None):
        """Get detailed game state for debugging"""
        game = self.get_object()
        
        active_players = list(PlayerGame.objects.filter(game=game, is_active=True).order_by('seat_position'))
        all_players = list(PlayerGame.objects.filter(game=game).order_by('seat_position'))
        
        debug_info = {
            'game_id': game.id,
            'status': game.status,
            'phase': game.phase,
            'current_player_id': game.current_player_id,
            'current_player_name': game.current_player.user.username if game.current_player else None,
            'current_bet': str(game.current_bet),
            'pot': str(game.pot),
            'dealer_position': game.dealer_position,
            'active_players_count': len(active_players),
            'total_players_count': len(all_players),
            'active_players': [
                {
                    'id': pg.player.id,
                    'username': pg.player.user.username,
                    'seat_position': pg.seat_position,
                    'stack': str(pg.stack),
                    'current_bet': str(pg.current_bet),
                    'total_bet': str(pg.total_bet),
                    'is_active': pg.is_active
                }
                for pg in all_players
            ]
        }
        
        return Response(debug_info)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave the game and cash out"""
        game = self.get_object()
        player, created = Player.objects.get_or_create(user=request.user)
        
        try:
            player_game = PlayerGame.objects.get(game=game, player=player)
            
            # Cannot leave during an active hand if still active
            if game.status == 'PLAYING' and player_game.is_active:
                return Response(
                    {'error': 'Cannot leave during an active hand. Fold first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cash out chips
            player.balance += player_game.stack
            player.save()
            
            # Remove player from game
            player_game.delete()
            
            # If no players left, end the game
            if PlayerGame.objects.filter(game=game).count() == 0:
                game.status = 'FINISHED'
                game.save()
            
            return Response({'success': True})
        except PlayerGame.DoesNotExist:
            return Response(
                {'error': 'You are not at this table'},
                status=status.HTTP_400_BAD_REQUEST
            )

class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter to show only the current user's player profile by default"""
        if self.request.query_params.get('all'):
            return Player.objects.all()
        return Player.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get the current user's player profile"""
        player, created = Player.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(player)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """Deposit funds to player balance (simulated)"""
        player, created = Player.objects.get_or_create(user=request.user)
        
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be positive'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            player.balance += amount
            player.save()
            
            serializer = self.get_serializer(player)
            return Response(serializer.data)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """Withdraw funds from player balance (simulated)"""
        player, created = Player.objects.get_or_create(user=request.user)
        
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be positive'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if amount > player.balance:
                return Response(
                    {'error': 'Insufficient balance'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            player.balance -= amount
            player.save()
            
            serializer = self.get_serializer(player)
            return Response(serializer.data)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @api_view(['POST'])
    def register_user(request):
        """Register a new user"""
        permission_classes = [AllowAny]
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        # Validate required fields
        if not username or not email or not password:
            return Response(
                {'error': 'Please provide username, email, and password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response(
                {'username': ['This username is already taken']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {'email': ['This email is already registered']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user and player profile
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                
                # Create player profile with initial balance
                from .models import Player
                Player.objects.create(user=user, balance=1000)  # Give new users $1000 to start
            
            return Response(
                {'message': 'User registered successfully'},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user"""
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    # Validate required fields
    if not username or not email or not password:
        return Response(
            {'error': 'Please provide username, email, and password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if username already exists
    if User.objects.filter(username=username).exists():
        return Response(
            {'username': ['This username is already taken']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if email already exists
    if User.objects.filter(email=email).exists():
        return Response(
            {'email': ['This email is already registered']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create user and player profile
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Create player profile with initial balance
            from .models import Player
            Player.objects.create(user=user, balance=Decimal('1000'))  # Give new users $1000 to start
        
        return Response(
            {'message': 'User registered successfully'},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_hand_history(request, game_id):
    """Get hand history for a specific game."""
    logger.info(f"📡 Hand history requested for game {game_id} by user {request.user.username}")
    
    game = get_object_or_404(Game, id=game_id)
    
    # Check if user is participating in the game
    if not PlayerGame.objects.filter(game=game, player__user=request.user).exists():
        logger.warning(f"❌ User {request.user.username} not authorized for game {game_id}")
        return Response(
            {'error': 'You are not a participant in this game'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    hand_histories = HandHistory.objects.filter(game=game).order_by('-hand_number')
    logger.info(f"📊 Found {hand_histories.count()} hand histories for game {game_id}")
    
    serializer = HandHistorySerializer(hand_histories, many=True)
    
    # Log details about each hand
    for hand in hand_histories[:3]:  # Log first 3 hands
        winner_info = hand.get_winner_info()
        if winner_info and 'winners' in winner_info:
            winner_name = winner_info['winners'][0]['player_name']
            winning_amount = winner_info['winners'][0]['winning_amount']
            logger.info(f"   Hand #{hand.hand_number}: Winner: {winner_name}, Amount: ${winning_amount}")
    
    logger.info(f"✅ Returning hand history response for game {game_id}")
    return Response({
        'game_id': game_id,
        'hand_history': serializer.data
    })