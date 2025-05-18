#!/usr/bin/env python
import os
import subprocess
import time
import sys
import signal
import threading
from pathlib import Path

# Configuration
BACKEND_DIR = Path(".")  # The Django project root directory
FRONTEND_DIR = Path("poker-frontend")  # The React project directory

class BackendServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.process = None
        self.daemon = True
    
    def run(self):
        os.chdir(BACKEND_DIR)
        env = os.environ.copy()
        
        # Check if virtual environment exists, if not create it
        if not Path("venv").exists():
            print("Setting up virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        
        # Activate virtual environment
        if sys.platform == 'win32':
            python_exe = Path("venv/Scripts/python.exe")
            pip_exe = Path("venv/Scripts/pip.exe")
        else:
            python_exe = Path("venv/bin/python")
            pip_exe = Path("venv/bin/pip")
        
        # Check if dependencies are installed
        print("Installing backend dependencies...")
        subprocess.run([pip_exe, "install", "-r", "requirements.txt"])
        
        # Check if migrations need to be applied
        print("Applying migrations...")
        subprocess.run([python_exe, "manage.py", "migrate"])
        
        # Start Django server
        print("\n🚀 Starting Django backend server...\n")
        self.process = subprocess.Popen([python_exe, "manage.py", "runserver"])
        self.process.wait()
    
    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

class FrontendServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.process = None
        self.daemon = True
    
    def run(self):
        os.chdir(FRONTEND_DIR)
        env = os.environ.copy()
        
        # Check if Node.js is installed
        try:
            subprocess.run(["node", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("❌ Node.js is not installed. Please install Node.js and try again.")
            return
        
        # Install dependencies if needed
        if not Path("node_modules").exists():
            print("Installing frontend dependencies...")
            subprocess.run(["npm", "install"])
        
        # Start React dev server
        print("\n🚀 Starting React frontend server...\n")
        self.process = subprocess.Popen(["npm", "start"])
        self.process.wait()
    
    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

def create_requirements_file():
    """Create requirements.txt file if it doesn't exist"""
    if not Path(BACKEND_DIR / "requirements.txt").exists():
        with open(BACKEND_DIR / "requirements.txt", "w") as f:
            f.write("""Django>=4.2.0
djangorestframework>=3.14.0
djangorestframework-simplejwt>=5.2.2
django-cors-headers>=4.0.0
channels>=4.0.0
channels-redis>=4.1.0
psycopg2-binary>=2.9.5
""")
        print("Created requirements.txt file")

def main():
    create_requirements_file()
    
    backend = BackendServer()
    frontend = FrontendServer()
    
    # Start servers
    backend.start()
    time.sleep(2)  # Give backend a chance to start first
    frontend.start()
    
    # Handle termination
    def signal_handler(sig, frame):
        print("\nShutting down servers...")
        frontend.stop()
        backend.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        frontend.stop()
        backend.stop()

if __name__ == "__main__":
    main()