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
import signal
from pathlib import Path

def check_virtual_environment():
    """Check if we're running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        venv_path = sys.prefix
        print(f"✅ Running in virtual environment: {venv_path}")
        return True
    else:
        print("⚠️  Not running in a virtual environment")
        print("   It's recommended to run this in a virtual environment to avoid package conflicts.")
        
        # Check if there's a venv directory in the current folder
        if os.path.exists('venv'):
            print("   Found 'venv' directory. You can activate it with:")
            if os.name == 'nt':  # Windows
                print("   .\\venv\\Scripts\\activate")
            else:  # Unix/MacOS
                print("   source venv/bin/activate")
        
        # Ask user if they want to continue
        response = input("   Do you want to continue anyway? (y/N): ").strip().lower()
        return response in ['y', 'yes']

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
        ['brew', 'services', 'start', 'redis'],  # macOS
        ['sudo', 'systemctl', 'start', 'redis-server'],  # Linux
        ['redis-server', '--daemonize', 'yes'],  # Redis daemon mode
    ]
    
    # Try Docker as last resort (check if container exists first)
    try:
        result = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=redis-poker', '--format', '{{.Names}}'], 
                              capture_output=True, text=True, timeout=5)
        if 'redis-poker' not in result.stdout:
            redis_commands.append(['docker', 'run', '-d', '-p', '6379:6379', '--name', 'redis-poker', 'redis:alpine'])
        else:
            redis_commands.append(['docker', 'start', 'redis-poker'])
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    for cmd in redis_commands:
        try:
            print(f"Trying: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            time.sleep(3)  # Give Redis time to start
            if check_redis():
                print(f"✅ Redis started with command: {' '.join(cmd)}")
                return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"Failed: {e}")
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
        # Start Django in the background with output capture
        django_process = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give Django a moment to start and check if it's still running
        time.sleep(2)
        if django_process.poll() is None:
            print("✅ Django server starting...")
            return django_process
        else:
            stdout, stderr = django_process.communicate()
            print(f"❌ Django failed to start: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start Django: {e}")
        return None

def start_react():
    """Start React development server."""
    print("⚛️ Starting React server...")
    original_dir = os.getcwd()
    try:
        os.chdir('poker-frontend')
        
        # Install npm packages if needed
        if not os.path.exists('node_modules'):
            print("📦 Installing npm packages...")
            subprocess.run(['npm', 'install'], check=True, timeout=120)
        
        # Start React server with environment variable to disable browser opening
        env = os.environ.copy()
        env['BROWSER'] = 'none'
        react_process = subprocess.Popen(
            ['npm', 'start'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give React a moment to start
        time.sleep(3)
        if react_process.poll() is None:
            print("✅ React server starting...")
            return react_process
        else:
            stdout, stderr = react_process.communicate()
            print(f"❌ React failed to start: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start React: {e}")
        return None
    finally:
        os.chdir(original_dir)

def main():
    """Main startup function."""
    print("🎰 Poker App Startup Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Please run this script from the Django project root directory")
        sys.exit(1)
    
    # Check virtual environment
    if not check_virtual_environment():
        print("❌ Startup cancelled by user")
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
    
    def cleanup_processes():
        """Clean up all spawned processes."""
        print("\n🛑 Shutting down services...")
        
        # Terminate Django process
        if django_process:
            try:
                django_process.terminate()
                django_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️ Force killing Django process...")
                django_process.kill()
                django_process.wait()
        
        # Terminate React process
        if react_process:
            try:
                react_process.terminate()
                react_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️ Force killing React process...")
                react_process.kill()
                react_process.wait()
        
        print("✅ All services stopped")
    
    try:
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if processes are still running
            if django_process.poll() is not None:
                print("❌ Django process stopped unexpectedly")
                break
            if react_process.poll() is not None:
                print("❌ React process stopped unexpectedly")
                break
    except KeyboardInterrupt:
        cleanup_processes()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        cleanup_processes()

if __name__ == "__main__":
    main()