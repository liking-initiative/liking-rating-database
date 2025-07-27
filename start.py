#!/usr/bin/env python3
"""
Quick start script for the Liking Rating Database
"""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path


def start_backend():
    """Start the backend server"""
    root_dir = Path(__file__).parent
    
    print("🚀 Starting backend server...")
    
    try:
        # Start the backend
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        print("✅ Backend server started on http://localhost:8000")
        print("📖 API documentation available at http://localhost:8000/docs")
        
        return backend_process
        
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return None


def start_frontend():
    """Start the frontend development server"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    print("🎨 Starting frontend development server...")
    
    try:
        # Check if node_modules exists
        if not (frontend_dir / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        
        # Start the frontend
        frontend_process = subprocess.Popen(
            ["npm", "start"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        print("✅ Frontend server starting...")
        print("🌐 Application will be available at http://localhost:3000")
        
        return frontend_process
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting frontend: {e}")
        print("ℹ️ Make sure Node.js and npm are installed")
        return None
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js and npm")
        return None


def main():
    """Main function"""
    print("🚀 Starting Liking Rating Database...")
    print("=" * 50)
    
    # Check if .env exists
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("⚠️ .env file not found. Creating from .env.example...")
        example_file = Path(__file__).parent / ".env.example"
        if example_file.exists():
            env_file.write_text(example_file.read_text())
            print("✅ .env file created. Please edit it if needed.")
        else:
            print("❌ .env.example not found. Please create a .env file manually.")
            return
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Failed to start backend")
        return
    
    # Wait a bit for backend to start
    time.sleep(3)
    
    # Start frontend
    frontend_process = start_frontend()
    
    try:
        print("\n" + "=" * 50)
        print("🎉 Both servers are starting up!")
        print("📊 Backend API: http://localhost:8000")
        print("🌐 Frontend App: http://localhost:3000")
        print("📖 API Docs: http://localhost:8000/api/v1/docs")
        print("\nPress Ctrl+C to stop both servers")
        print("=" * 50)
        
        # Wait for processes
        if frontend_process:
            frontend_process.wait()
        else:
            backend_process.wait()
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
        
        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
        
        print("✅ Servers stopped")


if __name__ == "__main__":
    main()
