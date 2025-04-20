# poker_api/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Game, PlayerGame

class PokerGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'
        
        # Join game group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )
        
        # Check if user is authenticated and part of the game
        user = self.scope['user']
        if isinstance(user, AnonymousUser):
            await self.close()
            return
        
        can_join = await self.can_join_game(user)
        if not can_join:
            await self.close()
            return
        
        await self.accept()
        
        # Send current game state to the new consumer
        game_state = await self.get_game_state()
        await self.send(text_data=json.dumps(game_state))
    
    async def disconnect(self, close_code):
        # Leave game group
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        # This consumer doesn't handle incoming messages from clients
        # Game actions are handled by the REST API
        pass
    
    # Receive message from game group
    async def game_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event['data']))
    
    @database_sync_to_async
    def can_join_game(self, user):
        try:
            game = Game.objects.get(id=self.game_id)
            # Check if user is part of the game
            return PlayerGame.objects.filter(game=game, player__user=user).exists()
        except Game.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_game_state(self):
        from .serializers import GameSerializer
        from rest_framework.request import Request
        from django.http import HttpRequest
        
        # Create a mock request with the user
        http_request = HttpRequest()
        http_request.user = self.scope['user']
        request = Request(http_request)
        
        game = Game.objects.get(id=self.game_id)
        serializer = GameSerializer(game, context={'request': request})
        return serializer.data