"""
Test-specific Django settings.

This configuration uses SQLite for testing to avoid PostgreSQL permission issues
and provides faster test execution.
"""

from .settings import *
import tempfile
import os

# Override database configuration for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for speed
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Alternative: Use temporary file-based SQLite (uncomment if in-memory doesn't work)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(tempfile.gettempdir(), 'test_poker_db.sqlite3'),
#     }
# }

# Disable migrations for faster testing
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
DEBUG = False
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Faster for testing
]

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Use local memory cache for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable CSRF for API testing
USE_TZ = True
SECRET_KEY = 'test-secret-key-not-for-production'

# Channel layers for WebSocket testing
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}