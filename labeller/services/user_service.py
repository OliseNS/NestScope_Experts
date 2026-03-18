"""
Centralized User Management Service

This service manages users across all projects. Users are stored in a global
registry and can be assigned to multiple projects.

Educational Note:
-----------------
This implements the "Single Source of Truth" pattern - users are defined once
in a central location, then referenced by projects. This prevents duplication
and makes user management easier.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional

class UserService:
    """
    Manages global user registry across all projects.

    Users are stored in labeller/projects/users.json and can work
    on multiple projects simultaneously.
    """

    def __init__(self, projects_dir: str):
        """
        Initialize the user service.

        Args:
            projects_dir: Path to projects directory
        """
        self.projects_dir = projects_dir
        self.users_file = os.path.join(projects_dir, 'users.json')
        self._ensure_users_file()

    def _ensure_users_file(self):
        """Create users.json if it doesn't exist"""
        if not os.path.exists(self.users_file):
            initial_data = {
                'users': [],
                'created_at': datetime.now().isoformat()
            }
            with open(self.users_file, 'w') as f:
                json.dump(initial_data, f, indent=2)
            print(f"✓ Created global users registry: {self.users_file}")

    def get_all_users(self) -> List[Dict]:
        """
        Get all registered users.

        Returns:
            List of user dictionaries with name, created_at, projects
        """
        with open(self.users_file, 'r') as f:
            data = json.load(f)
        return data.get('users', [])

    def get_user(self, username: str) -> Optional[Dict]:
        """
        Get a specific user by name.

        Args:
            username: User's name

        Returns:
            User dictionary or None if not found
        """
        users = self.get_all_users()
        for user in users:
            if user['name'] == username:
                return user
        return None

    def create_user(self, username: str) -> Dict:
        """
        Create a new user in the global registry.

        Args:
            username: User's name

        Returns:
            Created user dictionary
        """
        # Check if user already exists
        if self.get_user(username):
            raise ValueError(f"User '{username}' already exists")

        # Load current data
        with open(self.users_file, 'r') as f:
            data = json.load(f)

        # Create new user
        new_user = {
            'name': username,
            'created_at': datetime.now().isoformat(),
            'projects': [],  # List of project folders they're assigned to
            'total_completed': 0,
            'total_annotations': 0
        }

        data['users'].append(new_user)

        # Save
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Created user: {username}")
        return new_user

    def add_user_to_project(self, username: str, project_folder: str):
        """
        Add a project to user's project list (if not already added).

        Args:
            username: User's name
            project_folder: Project folder name
        """
        with open(self.users_file, 'r') as f:
            data = json.load(f)

        # Find user
        for user in data['users']:
            if user['name'] == username:
                if project_folder not in user.get('projects', []):
                    if 'projects' not in user:
                        user['projects'] = []
                    user['projects'].append(project_folder)
                break

        # Save
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=2)

    def update_user_stats(self, username: str, completed_delta: int = 0, annotations_delta: int = 0):
        """
        Update user's global statistics.

        Args:
            username: User's name
            completed_delta: Change in completed images
            annotations_delta: Change in total annotations
        """
        with open(self.users_file, 'r') as f:
            data = json.load(f)

        # Find and update user
        for user in data['users']:
            if user['name'] == username:
                user['total_completed'] = user.get('total_completed', 0) + completed_delta
                user['total_annotations'] = user.get('total_annotations', 0) + annotations_delta
                break

        # Save
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_user_projects(self, username: str) -> List[str]:
        """
        Get list of projects a user is assigned to.

        Args:
            username: User's name

        Returns:
            List of project folder names
        """
        user = self.get_user(username)
        if user:
            return user.get('projects', [])
        return []


# Singleton instance
_user_service = None

def get_user_service(projects_dir: str = None) -> UserService:
    """
    Get the singleton user service instance.

    Args:
        projects_dir: Path to projects directory (only used on first call)

    Returns:
        UserService instance
    """
    global _user_service
    if _user_service is None:
        if projects_dir is None:
            raise ValueError("projects_dir required for first call")
        _user_service = UserService(projects_dir)
    return _user_service
