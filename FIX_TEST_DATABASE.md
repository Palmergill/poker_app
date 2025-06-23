# Fixing Test Database Issues

You're getting "permission denied to create database" because Django can't create test databases in PostgreSQL. Here are several solutions:

## 🚀 Quick Fix: Use SQLite for Testing (Recommended)

I've created test-specific settings that use SQLite instead of PostgreSQL:

```bash
# Use the new SQLite test runner
python test_with_sqlite.py

# Or use the updated main test runner
python run_tests.py

# Run specific tests
python test_with_sqlite.py poker_api.tests.ModelTestCase
```

This approach:
- ✅ No database permissions needed
- ✅ Faster test execution (in-memory database)
- ✅ Isolated test environment
- ✅ Works identically to PostgreSQL for testing

## 🔧 Alternative: Fix PostgreSQL Permissions

If you prefer to use PostgreSQL for testing, here are the fixes:

### Option 1: Grant Database Creation Rights

```bash
# Connect to PostgreSQL as superuser
psql -h localhost -U postgres

# Grant createdb permission to your user
ALTER USER palmer CREATEDB;

# Verify the permission
\du palmer
```

### Option 2: Create Test Database Manually

```bash
# Connect as PostgreSQL superuser
psql -h localhost -U postgres

# Create test database with correct owner
CREATE DATABASE test_poker_db OWNER palmer;

# Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE test_poker_db TO palmer;
```

### Option 3: Use PostgreSQL Superuser for Tests

Edit `poker_project/settings.py` to add test database config:

```python
import sys

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'poker_db',
        'USER': 'palmer',
        'PASSWORD': 'palmeristhebest',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Use postgres superuser for testing
if 'test' in sys.argv:
    DATABASES['default']['USER'] = 'postgres'
    DATABASES['default']['PASSWORD'] = 'your_postgres_password'
```

## 🔍 Verify Your Setup

Test that the fix worked:

```bash
# Quick verification
python test_standalone.py

# SQLite test runner  
python test_with_sqlite.py

# Full test suite
python run_tests.py

# Specific test categories
python run_tests.py --category models
python run_tests.py --category game
```

## 📊 Test Performance Comparison

| Method | Speed | Setup | Database |
|--------|-------|-------|----------|
| SQLite (in-memory) | ⚡⚡⚡ Fastest | ✅ No config needed | 🧠 RAM |
| SQLite (file) | ⚡⚡ Fast | ✅ No config needed | 💾 Disk |
| PostgreSQL | ⚡ Normal | ⚙️ Permissions needed | 🐘 Full DB |

## 🐛 Troubleshooting

### If SQLite tests fail:

```bash
# Check Django setup
python -c "import django; print('Django version:', django.VERSION)"

# Check database config
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poker_project.test_settings')
import django
django.setup()
from django.conf import settings
print('Database engine:', settings.DATABASES['default']['ENGINE'])
"
```

### If PostgreSQL connection fails:

```bash
# Check PostgreSQL is running
brew services list | grep postgresql
# or
sudo systemctl status postgresql

# Test connection
psql -h localhost -U palmer -d poker_db -c "SELECT version();"
```

### If tests hang or timeout:

The SQLite configuration uses in-memory database which should be very fast. If tests still hang:

1. Check for infinite loops in game logic
2. Verify WebSocket consumers aren't waiting for real Redis
3. Use `--verbosity=2` to see which test is hanging

## 🎯 Recommended Workflow

For development:
```bash
# Quick validation (no database)
python test_standalone.py

# Fast database tests  
python test_with_sqlite.py

# Specific components
python run_tests.py --category models
```

For CI/CD:
```bash
# Full suite with coverage
python run_tests.py --coverage
```

For debugging:
```bash
# Verbose output
python run_tests.py --verbose

# Single test
python test_with_sqlite.py poker_api.tests.ModelTestCase.test_poker_table_creation
```

The SQLite approach is recommended because it's faster, requires no setup, and tests the same business logic as PostgreSQL.