# poker_api/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import PokerTable, Player, Game, PlayerGame
from .serializers import (
    PokerTableSerializer, PlayerSerializer, GameSerializer, PlayerGameSerializer,
    GameActionRequestSerializer
)
from .services.game_service import GameService
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal

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
            serializer = self.get_serializer(game)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def perform_action(self, request, pk=None):
        """Take an action in the game"""
        game = self.get_object()
        player, created = Player.objects.get_or_create(user=request.user)
        
        # Validate action
        serializer = GameActionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        action_type = serializer.validated_data['action_type']
        amount = serializer.validated_data.get('amount', 0)
        
        try:
            GameService.process_action(game.id, player.id, action_type, amount)
            game_serializer = self.get_serializer(game)
            return Response(game_serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
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