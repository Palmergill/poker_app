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
import threading
import queue
import argparse
from pathlib import Path

# Try to import psutil, fall back to basic commands if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil not installed. Some features will use fallback methods.")
    print("   Install with: pip install psutil")

def check_and_stop_existing_services():
    """Check for and stop any existing Django/React processes."""
    print("🔍 Checking for existing services...")
    
    if not PSUTIL_AVAILABLE:
        return check_and_stop_with_pkill()
    
    services_stopped = False
    
    # Check for Django processes
    django_pids = []
    react_pids = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                
                # Check for Django runserver
                if 'manage.py runserver' in cmdline or 'runserver' in cmdline:
                    django_pids.append(proc.info['pid'])
                    
                # Check for React dev server (npm start in poker-frontend)
                elif ('npm start' in cmdline or 'react-scripts start' in cmdline) and 'poker-frontend' in cmdline:
                    react_pids.append(proc.info['pid'])
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
    except Exception as e:
        print(f"⚠️ Error checking processes: {e}")
        # Fallback to pkill commands
        return check_and_stop_with_pkill()
    
    # Stop Django processes
    if django_pids:
        print(f"🛑 Found running Django server(s) (PID: {', '.join(map(str, django_pids))})")
        for pid in django_pids:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=5)
                print(f"✅ Stopped Django server (PID: {pid})")
                services_stopped = True
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    proc.kill()
                    print(f"⚠️ Force killed Django server (PID: {pid})")
                    services_stopped = True
                except psutil.NoSuchProcess:
                    pass
            except Exception as e:
                print(f"⚠️ Could not stop Django server (PID: {pid}): {e}")
    
    # Stop React processes
    if react_pids:
        print(f"🛑 Found running React server(s) (PID: {', '.join(map(str, react_pids))})")
        for pid in react_pids:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=5)
                print(f"✅ Stopped React server (PID: {pid})")
                services_stopped = True
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    proc.kill()
                    print(f"⚠️ Force killed React server (PID: {pid})")
                    services_stopped = True
                except psutil.NoSuchProcess:
                    pass
            except Exception as e:
                print(f"⚠️ Could not stop React server (PID: {pid}): {e}")
    
    if not django_pids and not react_pids:
        print("✅ No existing Django/React services found")
    elif services_stopped:
        print("⏱️ Waiting for services to fully stop...")
        time.sleep(2)
    
    return True

def check_and_stop_with_pkill():
    """Fallback method using pkill commands."""
    print("🔄 Using pkill fallback to stop services...")
    
    services_stopped = False
    
    # Stop Django processes
    try:
        result = subprocess.run(['pkill', '-f', 'manage.py runserver'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Stopped Django server(s) using pkill")
            services_stopped = True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    # Stop React processes
    try:
        result = subprocess.run(['pkill', '-f', 'react-scripts start'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Stopped React server(s) using pkill")
            services_stopped = True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    # Also try npm processes
    try:
        result = subprocess.run(['pkill', '-f', 'npm start'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Stopped npm process(es) using pkill")
            services_stopped = True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    if services_stopped:
        print("⏱️ Waiting for services to fully stop...")
        time.sleep(2)
    else:
        print("✅ No services needed to be stopped")
    
    return True

def check_port_availability(auto_cleanup=False):
    """Check if required ports are available."""
    print("🔍 Checking port availability...")
    
    ports_to_check = [8000, 3000]  # Django and React ports
    occupied_ports = []
    
    for port in ports_to_check:
        if PSUTIL_AVAILABLE:
            try:
                # Check if port is in use using psutil
                for conn in psutil.net_connections():
                    if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                        occupied_ports.append(port)
                        break
            except Exception:
                # Fallback to lsof if psutil fails
                occupied_ports.extend(check_port_with_lsof(port))
        else:
            # Use lsof directly
            occupied_ports.extend(check_port_with_lsof(port))
    
    if occupied_ports:
        print(f"⚠️ Ports still occupied: {occupied_ports}")
        if auto_cleanup:
            print("   Auto-cleanup enabled, freeing ports...")
            return force_free_ports(occupied_ports)
        else:
            response = input("   Do you want to try to free these ports? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                return force_free_ports(occupied_ports)
            else:
                print("   Continuing anyway - services may fail to start")
                return True
    else:
        print("✅ All required ports are available")
        return True

def check_port_with_lsof(port):
    """Check if a specific port is in use using lsof."""
    try:
        if os.name == 'posix':  # Unix-like systems
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.stdout.strip():
                return [port]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []

def force_free_ports(ports):
    """Force free the specified ports."""
    print(f"🔄 Attempting to free ports: {ports}")
    
    for port in ports:
        try:
            if os.name == 'posix':  # Unix-like systems
                # Find processes using the port
                result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                      capture_output=True, text=True, timeout=5)
                pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
                
                for pid in pids:
                    if pid:
                        try:
                            subprocess.run(['kill', '-TERM', pid], timeout=5)
                            print(f"✅ Sent TERM signal to process {pid} on port {port}")
                            time.sleep(1)
                            # Check if still running, then force kill
                            subprocess.run(['kill', '-KILL', pid], timeout=5)
                        except subprocess.CalledProcessError:
                            pass  # Process may have already terminated
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            print(f"⚠️ Could not free port {port}")
    
    time.sleep(2)
    return True

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
        # Start Django in the background but allow stdout/stderr to pass through
        django_process = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Give Django a moment to start and check if it's still running
        time.sleep(2)
        if django_process.poll() is None:
            print("✅ Django server starting...")
            return django_process
        else:
            stdout, stderr = django_process.communicate()
            print(f"❌ Django failed to start: {stdout}")
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

def monitor_django_output(django_process, output_queue):
    """Monitor Django process output and put lines in queue."""
    try:
        while True:
            line = django_process.stdout.readline()
            if line:
                output_queue.put(line.strip())
            elif django_process.poll() is not None:
                break
    except Exception as e:
        output_queue.put(f"Error reading Django output: {e}")

def display_logs(output_queue, errors_only=False):
    """Display Django logs from queue."""
    if errors_only:
        print("\n🚨 Following Django error logs only (press Ctrl+C to stop):")
    else:
        print("\n🔍 Following Django logs (press Ctrl+C to stop):")
    print("=" * 60)
    try:
        while True:
            try:
                line = output_queue.get(timeout=1)
                
                if errors_only:
                    # Only show lines that contain error indicators
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['error', 'exception', 'traceback', 'critical', 'failed', '❌']):
                        print(f"[DJANGO ERROR] {line}")
                else:
                    print(f"[DJANGO] {line}")
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        pass

def main():
    """Main startup function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Poker App Startup Script')
    parser.add_argument('--auto-cleanup', action='store_true', 
                       help='Automatically clean up existing services without prompting')
    parser.add_argument('--skip-cleanup', action='store_true',
                       help='Skip cleanup of existing services')
    parser.add_argument('--errors-only', action='store_true',
                       help='Show only error logs, suppress info messages')
    args = parser.parse_args()
    
    print("🎰 Poker App Startup Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Please run this script from the Django project root directory")
        sys.exit(1)
    
    # Step 0: Stop any existing services
    if not args.skip_cleanup:
        try:
            if not check_and_stop_existing_services():
                print("❌ Failed to stop existing services")
                sys.exit(1)
            
            if not check_port_availability(auto_cleanup=args.auto_cleanup):
                print("❌ Required ports are not available")
                sys.exit(1)
                
        except Exception as e:
            print(f"⚠️ Error during service cleanup: {e}")
            print("Continuing with startup...")
    else:
        print("⏭️ Skipping service cleanup as requested")
    
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
    
    # Set up log monitoring
    output_queue = queue.Queue()
    log_thread = threading.Thread(target=monitor_django_output, args=(django_process, output_queue))
    log_thread.daemon = True
    log_thread.start()
    
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
        # Start displaying logs
        display_logs(output_queue, errors_only=args.errors_only)
    except KeyboardInterrupt:
        cleanup_processes()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        cleanup_processes()

if __name__ == "__main__":
    main()