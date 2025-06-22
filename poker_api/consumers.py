# poker_api/consumers.py (Updated)
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Game, PlayerGame
import logging

logger = logging.getLogger(__name__)

class PokerGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'
        
        # Get user from scope (set by our custom middleware)
        user = self.scope.get('user')
        
        logger.info(f"WebSocket connection attempt for game {self.game_id}, user: {user}")
        
        # Check if user is authenticated
        if isinstance(user, AnonymousUser) or not user.is_authenticated:
            logger.warning(f"Unauthenticated WebSocket connection attempt for game {self.game_id}")
            await self.close(code=4001)  # Custom close code for authentication failure
            return
        
        # Check if user can join this game
        can_join = await self.can_join_game(user)
        if not can_join:
            logger.warning(f"User {user.username} cannot join game {self.game_id}")
            await self.close(code=4003)  # Custom close code for permission denied
            return
        
        # Join game group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected for user {user.username} to game {self.game_id}")
        
        # Send current game state to the new consumer
        try:
            game_state = await self.get_game_state()
            await self.send(text_data=json.dumps(game_state))
        except Exception as e:
            logger.error(f"Error sending initial game state: {e}")
    
    async def disconnect(self, close_code):
        # Leave game group
        if hasattr(self, 'game_group_name'):
            await self.channel_layer.group_discard(
                self.game_group_name,
                self.channel_name
            )
        
        user = self.scope.get('user')
        if user and not isinstance(user, AnonymousUser):
            logger.info(f"WebSocket disconnected for user {user.username}, close code: {close_code}")
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        # This consumer doesn't handle incoming messages from clients
        # Game actions are handled by the REST API
        logger.info(f"Received WebSocket message: {text_data}")
        pass
    
    # Receive message from game group
    async def game_update(self, event):
        # Send message to WebSocket
        try:
            await self.send(text_data=json.dumps(event['data']))
        except Exception as e:
            logger.error(f"Error sending game update: {e}")
    
    @database_sync_to_async
    def can_join_game(self, user):
        try:
            game = Game.objects.get(id=self.game_id)
            # Check if user is part of the game
            return PlayerGame.objects.filter(game=game, player__user=user).exists()
        except Game.DoesNotExist:
            logger.error(f"Game {self.game_id} does not exist")
            return False
        except Exception as e:
            logger.error(f"Error checking if user can join game: {e}")
            return False
    
    @database_sync_to_async
    def get_game_state(self):
        from .serializers import GameSerializer
        from rest_framework.request import Request
        from django.http import HttpRequest
        
        try:
            # Create a mock request with the user
            http_request = HttpRequest()
            http_request.user = self.scope['user']
            request = Request(http_request)
            
            game = Game.objects.get(id=self.game_id)
            serializer = GameSerializer(game, context={'request': request})
            return serializer.data
        except Exception as e:
            logger.error(f"Error getting game state: {e}")
            return {"error": "Failed to get game state"}