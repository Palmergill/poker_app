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
1. Players authenticate and join tables via REST API
2. Game state managed through `GameService` with atomic transactions
3. Real-time updates broadcast via WebSocket consumers to all connected clients
4. Game phases: PREFLOP → FLOP → TURN → RIVER → SHOWDOWN

## Development Commands

### Backend (Django)
```bash
# Start backend server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run tests (if available)
python manage.py test
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
```

This script handles:
- Redis server startup/verification
- Python dependencies installation
- Django migrations
- Superuser creation (admin/admin)
- Concurrent startup of both Django and React servers

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