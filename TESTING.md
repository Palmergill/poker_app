# Poker Application Test Suite

This document describes the comprehensive test suite for the Texas Hold'em poker application.

## Test Suite Overview

The test suite covers all major components of the application:

- **Models**: All Django models and their methods
- **Game Logic**: Core poker game mechanics and rules
- **API Endpoints**: REST API functionality
- **Hand Evaluation**: Poker hand ranking and comparison
- **WebSockets**: Real-time game communication
- **Integration**: End-to-end game scenarios

## Test Structure

### Main Test File: `poker_api/tests.py`

**ModelTestCase**: Tests all Django models
- PokerTable, Player, Game, PlayerGame, GameAction, HandHistory
- Model creation, string representations, JSON methods
- Database relationships and constraints

**CardUtilsTestCase**: Tests card and deck utilities
- Card creation, equality, comparison
- Deck shuffling, dealing, reset functionality
- Card validation and parsing

**HandEvaluatorTestCase**: Tests poker hand evaluation
- All hand types: Royal Flush through High Card
- Hand comparison and ranking logic
- Edge cases and error handling

**GameServiceTestCase**: Tests core game logic
- Game creation and player management
- Player actions (fold, check, call, bet, raise)
- Game phase progression and rule enforcement
- Showdown mechanics and winner determination

**APITestCase**: Tests REST API endpoints
- User registration and authentication
- Game and table management
- Hand history retrieval
- Authorization and error handling

**IntegrationTestCase**: Tests complete game scenarios
- Full hands from start to finish
- Multiple betting rounds
- Showdown vs. fold endings

### Additional Test Files

**`poker_api/test_websockets.py`**: WebSocket functionality
- Connection management
- Real-time game updates
- Message broadcasting

**`test_standalone.py`**: Standalone tests
- Tests that don't require Django database
- Core utilities and algorithms
- Quick validation of basic functionality

## Running Tests

### Method 1: Django Test Runner

```bash
# Run all tests
python manage.py test poker_api

# Run specific test class
python manage.py test poker_api.tests.ModelTestCase

# Run with verbose output
python manage.py test poker_api --verbosity=2
```

### Method 2: Custom Test Runner

```bash
# Make script executable
chmod +x run_tests.py

# Run all tests
python run_tests.py

# Run specific category
python run_tests.py --category models
python run_tests.py --category game
python run_tests.py --category api

# Run with coverage
python run_tests.py --coverage

# Quick test suite
python run_tests.py --quick

# Verbose output
python run_tests.py --verbose
```

### Method 3: Pytest (Advanced)

First install test requirements:
```bash
pip install -r requirements-test.txt
```

Then run tests:
```bash
# Run all tests with coverage
pytest

# Run specific tests
pytest poker_api/tests.py::ModelTestCase::test_poker_table_creation

# Run by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Method 4: Standalone Tests

For quick validation without database setup:
```bash
python test_standalone.py
```

## Test Categories

### Unit Tests (`-m unit`)
- Individual component testing
- No external dependencies
- Fast execution

### Integration Tests (`-m integration`)  
- Multi-component interactions
- Database transactions
- Complete workflows

### API Tests (`-m api`)
- HTTP endpoint testing
- Authentication and authorization
- Request/response validation

### WebSocket Tests (`-m websocket`)
- Real-time communication
- Connection management
- Message broadcasting

## Test Configuration

### Environment Setup

Tests use a separate test database and settings:
- Database: `test_poker_db` (auto-created/destroyed)
- Settings: Same as main app but isolated
- Media/Static: Temporary directories

### Coverage Configuration

Coverage reporting is configured to:
- Include all `poker_api` code
- Exclude migrations, virtual environments
- Generate HTML and terminal reports
- Target 90%+ coverage for core components

### Continuous Integration

The test suite is designed for CI/CD:
- No external service dependencies
- Deterministic test data
- Fast execution (< 30 seconds)
- Clear pass/fail indicators

## Test Data Management

### Fixtures and Factories

Tests use:
- Django's built-in test database isolation
- Predictable test data in `setUp()` methods
- Mock objects for external services
- Deterministic random seeds where needed

### Database Strategy

- Each test class gets fresh database
- Transactions rolled back after each test
- No shared state between tests
- Isolated test environments

## Performance Considerations

### Test Execution Speed

- **Quick Tests**: Core functionality (~5 seconds)
- **Unit Tests**: All individual components (~15 seconds)  
- **Full Suite**: All tests including integration (~30 seconds)
- **With Coverage**: Full suite plus reporting (~45 seconds)

### Optimization Tips

- Use `TransactionTestCase` only when needed
- Mock external services and WebSocket broadcasts
- Use `setUpClass` for expensive setup when possible
- Run quick tests during development

## Common Test Commands

```bash
# Development workflow
python test_standalone.py              # Quick validation
python run_tests.py --quick            # Core functionality
python run_tests.py --category game    # Specific component
python run_tests.py --coverage         # Full validation

# CI/CD pipeline
python run_tests.py --verbose          # Full suite with details
python manage.py check                 # Django configuration check
```

## Troubleshooting

### Database Permission Issues

If you get "permission denied to create database":
```bash
# Use standalone tests instead
python test_standalone.py

# Or fix database permissions
sudo -u postgres createdb test_poker_db
```

### Import Errors

If modules can't be imported:
```bash
# Ensure Python path includes project root
export PYTHONPATH="/path/to/poker_app:$PYTHONPATH"

# Or run from project root
cd /Users/jamesgill/poker_app
python run_tests.py
```

### WebSocket Test Issues

WebSocket tests require:
- Redis server running
- Channels properly configured
- Async test support

## Test Metrics

Current test coverage targets:

- **Models**: 100% (critical data integrity)
- **Game Logic**: 95% (core business rules)
- **API Endpoints**: 90% (user-facing functionality)
- **Utilities**: 95% (algorithmic correctness)
- **Overall**: 90%+ (production readiness)

## Adding New Tests

When adding features:

1. **Write tests first** (TDD approach)
2. **Cover happy path and edge cases**
3. **Add appropriate test markers**
4. **Update this documentation**
5. **Ensure tests run in CI/CD**

### Test Template

```python
def test_new_feature(self):
    """Test description."""
    # Arrange
    setup_data = create_test_data()
    
    # Act
    result = perform_action(setup_data)
    
    # Assert
    self.assertEqual(result.status, 'expected')
    self.assertIn('key', result.data)
```

This comprehensive test suite ensures the poker application is reliable, maintainable, and ready for production use.