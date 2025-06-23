#!/usr/bin/env python3
"""
Poker App Shutdown Script
This script stops all running poker application services.
"""

import subprocess
import sys
import time
import os
import argparse

# Try to import psutil, fall back to basic commands if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def stop_django_servers():
    """Stop all Django runserver processes."""
    stopped_count = 0
    
    if PSUTIL_AVAILABLE:
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'manage.py runserver' in cmdline:
                        print(f"🛑 Stopping Django server (PID: {proc.info['pid']})")
                        proc.terminate()
                        proc.wait(timeout=5)
                        stopped_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired):
                    pass
        except Exception:
            # Fallback to pkill
            pass
    
    # Fallback or if psutil not available
    try:
        result = subprocess.run(['pkill', '-f', 'manage.py runserver'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Stopped Django server(s) using pkill")
            stopped_count += 1
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    return stopped_count

def stop_react_servers():
    """Stop all React development servers."""
    stopped_count = 0
    
    if PSUTIL_AVAILABLE:
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if ('npm start' in cmdline or 'react-scripts start' in cmdline) and 'poker-frontend' in cmdline:
                        print(f"🛑 Stopping React server (PID: {proc.info['pid']})")
                        proc.terminate()
                        proc.wait(timeout=5)
                        stopped_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired):
                    pass
        except Exception:
            # Fallback to pkill
            pass
    
    # Fallback or if psutil not available
    try:
        result = subprocess.run(['pkill', '-f', 'react-scripts start'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Stopped React server(s) using pkill")
            stopped_count += 1
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    # Also try npm processes
    try:
        result = subprocess.run(['pkill', '-f', 'npm start'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Stopped npm process(es) using pkill")
            stopped_count += 1
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    return stopped_count

def stop_startup_script():
    """Stop the startup script itself."""
    stopped_count = 0
    
    try:
        result = subprocess.run(['pkill', '-f', 'start_poker_app.py'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Stopped startup script")
            stopped_count += 1
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    return stopped_count

def main():
    """Main shutdown function."""
    parser = argparse.ArgumentParser(description='Poker App Shutdown Script')
    parser.add_argument('--force', action='store_true',
                       help='Force kill processes if they don\'t stop gracefully')
    args = parser.parse_args()
    
    print("🛑 Poker App Shutdown Script")
    print("=" * 40)
    
    total_stopped = 0
    
    # Stop Django servers
    print("🔍 Looking for Django servers...")
    django_stopped = stop_django_servers()
    total_stopped += django_stopped
    
    # Stop React servers
    print("🔍 Looking for React servers...")
    react_stopped = stop_react_servers()
    total_stopped += react_stopped
    
    # Stop startup script
    print("🔍 Looking for startup script...")
    script_stopped = stop_startup_script()
    total_stopped += script_stopped
    
    if total_stopped == 0:
        print("✅ No poker app services were running")
    else:
        print(f"✅ Stopped {total_stopped} service(s)")
        print("⏱️ Waiting for services to fully stop...")
        time.sleep(2)
    
    # Check if ports are now free
    ports_to_check = [8000, 3000]
    occupied_ports = []
    
    for port in ports_to_check:
        try:
            if os.name == 'posix':
                result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                      capture_output=True, text=True, timeout=5)
                if result.stdout.strip():
                    occupied_ports.append(port)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    if occupied_ports:
        print(f"⚠️ Ports still occupied: {occupied_ports}")
        if args.force:
            print("🔥 Force killing processes on occupied ports...")
            for port in occupied_ports:
                try:
                    result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                          capture_output=True, text=True, timeout=5)
                    pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    for pid in pids:
                        if pid:
                            subprocess.run(['kill', '-KILL', pid], timeout=5)
                            print(f"💀 Force killed process {pid} on port {port}")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    pass
        else:
            print("   Use --force to force kill remaining processes")
    else:
        print("✅ All poker app ports are now free")
    
    print("\n🎉 Shutdown complete!")

if __name__ == "__main__":
    main()