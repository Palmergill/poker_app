#!/usr/bin/env python3
"""
Poker App Startup Script
This script helps you start all required services for the poker application.
"""

import subprocess
import sys
import time
import os
import redis
from pathlib import Path

def check_redis():
    """Check if Redis is running."""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except redis.ConnectionError:
        print("❌ Redis is not running")
        return False

def start_redis():
    """Attempt to start Redis."""
    print("🔄 Attempting to start Redis...")
    
    # Try different Redis startup commands
    redis_commands = [
        ['redis-server'],
        ['brew', 'services', 'start', 'redis'],  # macOS
        ['sudo', 'systemctl', 'start', 'redis-server'],  # Linux
        ['docker', 'run', '-d', '-p', '6379:6379', '--name', 'redis', 'redis:alpine']  # Docker
    ]
    
    for cmd in redis_commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            time.sleep(2)  # Give Redis time to start
            if check_redis():
                print(f"✅ Redis started with command: {' '.join(cmd)}")
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    return False

def install_requirements():
    """Install Python requirements."""
    print("📦 Installing Python requirements...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Python requirements installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python requirements")
        return False

def run_migrations():
    """Run Django migrations."""
    print("🔄 Running Django migrations...")
    try:
        subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
        print("✅ Migrations completed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Migration failed")
        return False

def create_superuser():
    """Create Django superuser if it doesn't exist."""
    print("👤 Checking for superuser...")
    try:
        # Check if superuser exists
        result = subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c',
            "from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())"
        ], capture_output=True, text=True)
        
        if 'True' not in result.stdout:
            print("Creating superuser (admin/admin)...")
            subprocess.run([
                sys.executable, 'manage.py', 'shell', '-c',
                "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')"
            ], check=True)
            print("✅ Superuser created (username: admin, password: admin)")
        else:
            print("✅ Superuser already exists")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create superuser")
        return False

def start_django():
    """Start Django development server."""
    print("🚀 Starting Django server...")
    try:
        # Start Django in the background
        django_process = subprocess.Popen([sys.executable, 'manage.py', 'runserver'])
        return django_process
    except Exception as e:
        print(f"❌ Failed to start Django: {e}")
        return None

def start_react():
    """Start React development server."""
    print("⚛️ Starting React server...")
    try:
        os.chdir('poker-frontend')
        
        # Install npm packages if needed
        if not os.path.exists('node_modules'):
            print("📦 Installing npm packages...")
            subprocess.run(['npm', 'install'], check=True)
        
        # Start React server
        react_process = subprocess.Popen(['npm', 'start'])
        os.chdir('..')
        return react_process
    except Exception as e:
        print(f"❌ Failed to start React: {e}")
        return None

def main():
    """Main startup function."""
    print("🎰 Poker App Startup Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Please run this script from the Django project root directory")
        sys.exit(1)
    
    # Step 1: Check/Start Redis
    if not check_redis():
        if not start_redis():
            print("❌ Could not start Redis. Please start it manually:")
            print("   - macOS: brew services start redis")
            print("   - Linux: sudo systemctl start redis-server")
            print("   - Docker: docker run -d -p 6379:6379 --name redis redis:alpine")
            sys.exit(1)
    
    # Step 2: Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Step 3: Run migrations
    if not run_migrations():
        sys.exit(1)
    
    # Step 4: Create superuser
    create_superuser()
    
    # Step 5: Start Django
    django_process = start_django()
    if not django_process:
        sys.exit(1)
    
    # Step 6: Start React
    react_process = start_react()
    if not react_process:
        django_process.terminate()
        sys.exit(1)
    
    print("\n🎉 All services started successfully!")
    print("=" * 40)
    print("📝 Application URLs:")
    print("   - Django Admin: http://localhost:8000/admin/")
    print("   - Django API: http://localhost:8000/api/")
    print("   - React App: http://localhost:3000/")
    print("\n👤 Default admin credentials: admin/admin")
    print("\n⏹️  Press Ctrl+C to stop all services")
    
    try:
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if processes are still running
            if django_process.poll() is not None:
                print("❌ Django process stopped")
                break
            if react_process.poll() is not None:
                print("❌ React process stopped")
                break
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        django_process.terminate()
        react_process.terminate()
        print("✅ All services stopped")

if __name__ == "__main__":
    main()