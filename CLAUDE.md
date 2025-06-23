# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a real-time multiplayer Texas Hold'em poker application with a Django REST Framework backend and React frontend.

### Backend Architecture (Django)

- **Models** (`poker_api/models.py`): Core entities - PokerTable, Player, Game, PlayerGame, GameAction
- **Game Service** (`poker_api/services/game_service.py`): Central game logic and state management with transaction-based operations
- **WebSocket Consumers** (`poker_api/consumers.py`): Real-time communication via Django Channels
- **Utilities**:
  - `poker_api/utils/card_utils.py`: Card and deck management
  - `poker_api/utils/hand_evaluator.py`: Poker hand evaluation logic
  - `poker_api/utils/game_manager.py`: Additional game management utilities

### Frontend Architecture (React)

- **Components** (`poker-frontend/src/components/`): UI components for tables, games, authentication
- **API Service** (`poker-frontend/src/services/apiService.js`): HTTP API communication
- **WebSocket Integration**: Real-time game updates via WebSocket connections

### Key Game Flow

# Texas Hold'em Poker: Complete Rules and Game Flow

## Overview

Texas Hold'em is the most popular variant of poker, played with a standard 52-card deck. Each player receives two private cards (hole cards) and combines them with five community cards to make the best possible five-card poker hand. The goal is to win chips by either having the best hand at showdown or by forcing all other players to fold through strategic betting.

## Game Setup

**Players:** 2-10 players (typically 6-9 for optimal play)
**Deck:** Standard 52-card deck, no jokers
**Chips:** Each player starts with a predetermined amount of chips
**Dealer Button:** A small disc that rotates clockwise after each hand to indicate the dealer position

## Pre-Game Preparation

### Blinds

Before any cards are dealt, two players must post forced bets called blinds:

- **Small Blind:** Posted by the player immediately to the left of the dealer button (typically half the minimum bet)
- **Big Blind:** Posted by the player two seats to the left of the dealer button (typically equal to the minimum bet)

These blinds ensure there's always money in the pot to play for and create initial action.

## Hand Rankings (Highest to Lowest)

1. **Royal Flush:** A, K, Q, J, 10 all of the same suit
2. **Straight Flush:** Five consecutive cards of the same suit
3. **Four of a Kind:** Four cards of the same rank
4. **Full House:** Three cards of one rank plus two cards of another rank
5. **Flush:** Five cards of the same suit (not consecutive)
6. **Straight:** Five consecutive cards of mixed suits
7. **Three of a Kind:** Three cards of the same rank
8. **Two Pair:** Two cards of one rank plus two cards of another rank
9. **One Pair:** Two cards of the same rank
10. **High Card:** When no other hand is made, the highest card plays

## Game Flow: The Four Betting Rounds

### Round 1: Pre-Flop

**Deal:** Each player receives two private cards face down (hole cards)

**Action:** Starting with the player to the left of the big blind, each player has three options:

- **Call:** Match the current bet (big blind amount)
- **Raise:** Increase the bet amount
- **Fold:** Discard cards and forfeit any chance to win the pot

The betting continues clockwise until all active players have either called the current bet or folded.

### Round 2: The Flop

**Deal:** Three community cards are dealt face up in the center of the table

**Action:** Starting with the first active player to the left of the dealer button, players can:

- **Check:** Pass the action without betting (only if no one has bet before you)
- **Bet:** Make the first wager of the round
- **Call:** Match the current bet
- **Raise:** Increase the current bet
- **Fold:** Discard cards and exit the hand

### Round 3: The Turn

**Deal:** One additional community card is dealt face up (fourth community card total)

**Action:** Same betting options as the flop round, starting with the first active player to the left of the dealer button.

### Round 4: The River

**Deal:** The final community card is dealt face up (fifth community card total)

**Action:** Final betting round with the same options as previous rounds.

## Showdown

After the final betting round, if two or more players remain, there's a showdown:

1. The last player to bet or raise shows their cards first
2. If there was no betting on the river, the player closest to the left of the dealer button shows first
3. Each player makes their best five-card hand using any combination of their two hole cards and the five community cards
4. The player with the best hand wins the entire pot
5. In case of identical hands, the pot is split equally among the tied players

## Key Rules and Concepts

### Betting Structure

- **Limit:** Fixed betting amounts for each round
- **No-Limit:** Players can bet any amount up to their entire chip stack
- **Pot-Limit:** Maximum bet is the current size of the pot

### All-In

When a player bets all their remaining chips, they are "all-in" and cannot be forced out of the hand by further betting from other players.

### Side Pots

When players have different amounts of chips and someone goes all-in, side pots are created so that players can only win amounts proportional to what they've contributed.

### Protecting Your Hand

Players are responsible for protecting their cards from being mucked (discarded) accidentally. Always keep your cards in front of you and consider using a chip or card protector.

### Table Stakes

You can only play with the chips you have on the table at the start of the hand. You cannot add more chips during a hand or bet money from your pocket.

## Betting Actions Explained

- **Check:** Pass the action to the next player without betting (only available when no one has bet before you)
- **Bet:** Make the first wager in a betting round
- **Call:** Match the current bet amount
- **Raise:** Increase the current bet (must be at least double the current bet in most games)
- **Fold:** Surrender your cards and any claim to the pot

## Strategy Fundamentals

### Starting Hand Selection

Not all hole cards are created equal. Premium hands like pocket aces, kings, queens, and ace-king suited should typically be played aggressively, while weak hands like 7-2 offsuit should usually be folded.

### Position Importance

Your position relative to the dealer button significantly affects your strategy. Later positions (closer to the button) are advantageous because you act after other players and have more information.

### Pot Odds

Consider the ratio of the current pot size to the cost of calling when deciding whether to continue with a drawing hand.

## Common Etiquette

- Act in turn and be clear about your intentions
- Keep your cards and chips organized and visible
- Don't discuss the hand while it's in progress
- Be respectful to other players and the dealer
- Don't slow-roll (deliberately delay showing a winning hand)

## Tournament vs. Cash Game Differences

**Cash Games:** Play with real money values, can leave at any time, blinds stay constant
**Tournaments:** Play for tournament chips, elimination format, blinds increase over time, winner takes predetermined prize structure

## Development Commands

### Backend (Django)

```bash
# Start backend server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run tests
python run_tests.py

# Run specific test category
python run_tests.py --category unit
python run_tests.py --category integration
python run_tests.py --category api

# Run with Django test runner
python manage.py test tests
```

### Frontend (React)

```bash
# Navigate to frontend directory
cd poker-frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Full Application Startup

```bash
# Use the provided startup script (recommended)
python start_poker_app.py

# With automatic cleanup of existing services
python start_poker_app.py --auto-cleanup

# Skip cleanup if you know no services are running
python start_poker_app.py --skip-cleanup
```

This script handles:

- **Service Cleanup**: Automatically detects and stops existing Django/React processes
- **Port Management**: Checks and frees occupied ports (8000, 3000)
- Redis server startup/verification
- Python dependencies installation
- Django migrations
- Superuser creation (admin/admin)
- Concurrent startup of both Django and React servers

### Full Application Shutdown

```bash
# Stop all poker app services
python stop_poker_app.py

# Force kill any stubborn processes
python stop_poker_app.py --force
```

The shutdown script:

- Stops all Django runserver processes
- Stops all React development servers
- Stops the startup script itself
- Checks and optionally frees occupied ports
- Works with or without psutil for process management

### Prerequisites

- Python 3.8+
- Node.js 14+ and npm
- PostgreSQL database named `poker_db`
- Redis server (for WebSocket functionality)

## Key Dependencies

- **Backend**: Django 4.2.7, DRF, Django Channels, psycopg2-binary, channels-redis, PyJWT
- **Frontend**: React 19.1.0, react-router-dom, axios
- **Testing**: pytest, pytest-django, pytest-asyncio, @testing-library/react

## Application URLs

- Django Admin: http://localhost:8000/admin/
- Django API: http://localhost:8000/api/
- React App: http://localhost:3000/
- WebSocket: ws://localhost:8000/ws/game/{game_id}/
