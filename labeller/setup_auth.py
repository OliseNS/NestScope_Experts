#!/usr/bin/env python3
"""
Setup script for Nestperts authentication

This script helps you:
1. Initialize the authentication database
2. Create your first admin user
3. Verify Google OAuth configuration
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from labeller.auth import init_auth_db, add_approved_email, add_admin

def check_env_vars():
    """Check if required environment variables are set"""
    required_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'SECRET_KEY']
    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    return missing

def main():
    print("=" * 60)
    print("Nestperts Authentication Setup")
    print("=" * 60)
    print()

    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()

    # Check environment variables
    missing_vars = check_env_vars()
    if missing_vars:
        print("❌ Missing required environment variables in .env:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        print("Please add these to your .env file.")
        print("See AUTH_SETUP.md for instructions on getting Google OAuth credentials.")
        return

    print("✅ Environment variables configured")
    print()

    # Initialize database
    print("Initializing authentication database...")
    init_auth_db()
    print("✅ Database initialized at data/users.db")
    print()

    # Get admin email
    print("Let's set up your admin account.")
    print("This email will have full access to manage other users.")
    print()

    admin_email = input("Enter your Gmail address: ").strip().lower()

    if not admin_email:
        print("❌ Email is required")
        return

    if not admin_email.endswith('@gmail.com'):
        print("⚠️  Warning: This should be a Gmail address for Google OAuth")
        confirm = input("Continue anyway? (y/n): ").lower()
        if confirm != 'y':
            return

    # Add admin to approved emails
    print()
    print(f"Adding {admin_email} to approved list...")
    success = add_approved_email(admin_email, 'setup_script', 'Initial admin user')

    if not success:
        print(f"⚠️  {admin_email} was already in the approved list")
    else:
        print("✅ Email approved")

    # Make admin
    print(f"Granting admin privileges to {admin_email}...")
    add_admin(admin_email)
    print("✅ Admin privileges granted")
    print()

    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start Nestperts: python labeller/app.py")
    print("2. Open http://localhost:5000")
    print("3. Click 'Sign in with Google'")
    print(f"4. Sign in with {admin_email}")
    print("5. Access the admin panel at http://localhost:5000/admin")
    print()
    print("From the admin panel, you can:")
    print("- Add more approved emails")
    print("- View all registered users")
    print("- Monitor login activity")
    print()

if __name__ == '__main__':
    main()
