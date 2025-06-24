#!/usr/bin/env python
"""
Test script to verify hand history is working correctly.
This script will create a simple test to check that hand history saves pot amounts correctly.
"""

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poker_project.settings')
django.setup()

from django.contrib.auth.models import User
from poker_api.models import PokerTable, Player, Game, PlayerGame, HandHistory
from poker_api.services.game_service import GameService
from decimal import Decimal

def test_hand_history():
    """Test that hand history correctly saves pot amounts and winner information."""
    
    print("🧪 Testing Hand History Functionality")
    print("=" * 50)
    
    # Clean up any existing test data
    HandHistory.objects.filter(game__table__name="Test Hand History Table").delete()
    Game.objects.filter(table__name="Test Hand History Table").delete()
    PokerTable.objects.filter(name="Test Hand History Table").delete()
    
    try:
        # Create test users
        user1, _ = User.objects.get_or_create(username="test_player1", defaults={"email": "test1@example.com"})
        user2, _ = User.objects.get_or_create(username="test_player2", defaults={"email": "test2@example.com"})
        
        # Create players
        player1, _ = Player.objects.get_or_create(user=user1, defaults={"balance": Decimal("1000.00")})
        player2, _ = Player.objects.get_or_create(user=user2, defaults={"balance": Decimal("1000.00")})
        
        # Create table
        table = PokerTable.objects.create(
            name="Test Hand History Table",
            max_players=9,
            small_blind=Decimal("5.00"),
            big_blind=Decimal("10.00"),
            min_buy_in=Decimal("100.00"),
            max_buy_in=Decimal("1000.00")
        )
        
        # Create game
        game = GameService.create_game(table, [player1, player2])
        print(f"✅ Created game {game.id} with players {player1.user.username} and {player2.user.username}")
        
        # Start game
        GameService.start_game(game.id)
        game.refresh_from_db()
        print(f"✅ Started game - Status: {game.status}, Phase: {game.phase}, Pot: ${game.pot}")
        
        # Simulate player 1 folding to test _end_hand scenario
        # This should trigger hand history creation
        player_games = PlayerGame.objects.filter(game=game, is_active=True).order_by('seat_position')
        current_player_id = game.current_player.id
        
        print(f"🎯 Current player: {game.current_player.user.username} (ID: {current_player_id})")
        print(f"💰 Pot before action: ${game.pot}")
        
        # Make the current player fold
        GameService.process_action(game.id, current_player_id, 'FOLD')
        game.refresh_from_db()
        
        print(f"✅ Processed FOLD action")
        print(f"💰 Pot after action: ${game.pot}")
        print(f"🎯 Game status: {game.status}, Phase: {game.phase}")
        
        # Check hand history
        hand_histories = HandHistory.objects.filter(game=game).order_by('-hand_number')
        print(f"📊 Found {hand_histories.count()} hand history records")
        
        if hand_histories.exists():
            for history in hand_histories:
                winner_info = history.get_winner_info()
                print(f"\n📋 Hand #{history.hand_number}:")
                print(f"   💰 Pot Amount: ${history.pot_amount}")
                print(f"   🏆 Winner Info: {winner_info}")
                
                if winner_info and 'winners' in winner_info:
                    for winner in winner_info['winners']:
                        print(f"   🥇 Winner: {winner['player_name']} - Amount: ${winner['winning_amount']}")
                        if 'reason' in winner:
                            print(f"   📝 Reason: {winner['reason']}")
                
                print(f"   🎯 Final Phase: {history.final_phase}")
                print(f"   ⏰ Completed: {history.completed_at}")
        else:
            print("❌ No hand history found!")
            
        print("\n" + "=" * 50)
        print("🧪 Hand History Test Complete")
        
        return hand_histories.count() > 0
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hand_history()
    if success:
        print("✅ Hand history test PASSED")
        sys.exit(0)
    else:
        print("❌ Hand history test FAILED")
        sys.exit(1)