#!/usr/bin/env python3
"""
Script to create the initial database migration for the FastAPI application.
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"Success: {description}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {description} failed")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Create initial migration."""
    print("Creating initial database migration...")
    
    # Set environment variable for database URL if not set
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://waitlist_user:waitlist_password@localhost:5432/waitlist_db"
        print("Using default DATABASE_URL")
    
    # Create initial migration
    if not run_command(
        "alembic revision --autogenerate -m 'Initial migration'",
        "Creating initial migration"
    ):
        sys.exit(1)
    
    print("\nMigration created successfully!")
    print("To apply the migration, run:")
    print("  alembic upgrade head")

if __name__ == "__main__":
    main() 