#!/usr/bin/env python3
"""
Startup script for Railway deployment
Handles migrations and starts Gunicorn server
"""
import os
import sys
import subprocess

def check_environment():
    """Check required environment variables"""
    required_vars = ["DJANGO_SECRET_KEY", "PROJECT_ENVIRONMENT"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        print(f"WARNING: Missing environment variables: {', '.join(missing)}")
        print("Server may not start correctly.")
    else:
        print("Environment variables check passed")

def run_migrations():
    """Run database migrations"""
    try:
        print("Running database migrations...")
        result = subprocess.run(
            ["python3", "manage.py", "migrate", "--noinput"],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("Migrations completed successfully")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"Migration warnings/errors (continuing anyway):")
            print(result.stderr)
            if result.stdout:
                print(result.stdout)
        return True
    except Exception as e:
        print(f"Error running migrations: {e}")
        import traceback
        traceback.print_exc()
        return True  # Continue anyway

def start_server():
    """Start Gunicorn server"""
    port = os.environ.get("PORT", "8000")
    print(f"Starting Gunicorn server on port {port}...")
    
    # Start the server using execvp (replaces current process)
    os.execvp(
        "python3",
        [
            "python3", "-m", "gunicorn",
            "--bind", f"0.0.0.0:{port}",
            "--workers", "4",
            "--timeout", "120",
            "--access-logfile", "-",
            "--error-logfile", "-",
            "src.wsgi:application"
        ]
    )

if __name__ == "__main__":
    # Check environment
    check_environment()
    
    # Run migrations first
    run_migrations()
    
    # Start the server
    try:
        start_server()
    except Exception as e:
        print(f"FATAL: Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

