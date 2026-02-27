"""
Species Service

This module provides database access for bird species data.
It loads species from the SQLite database and caches them in memory
for fast access during requests.

Educational Notes:
- Service Layer Pattern: Business logic separated from HTTP routes
- In-Memory Caching: Load once on startup, not per request
- Read-Only Connection: Prevents accidental database writes
"""

import sqlite3
import os


class SpeciesService:
    """
    Service for loading and managing bird species data from the database.

    This class demonstrates the service layer pattern: it encapsulates
    all database access logic in one place, making it easy to test and reuse.
    """

    def __init__(self, db_path=None):
        """
        Initialize the species service.

        Args:
            db_path: Path to SQLite database. If None, uses default path.
        """
        if db_path is None:
            # Default: Go up from labeller/ to project root, then to data/
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(current_dir, "..", "data", "bird_data_complete.db")

        self.db_path = os.path.abspath(db_path)
        self._species_cache = None  # In-memory cache

        # Verify database exists
        if not os.path.exists(self.db_path):
            print(f"WARNING: Database not found at {self.db_path}")
            print(f"Species service will return empty list.")

    def _get_connection(self):
        """
        Create a read-only connection to the database.

        Why read-only?
        - Prevents accidental data corruption
        - SQLite will throw an error if we try to write
        - Same pattern as server backend (server/main.py lines 329-330)

        Returns:
            sqlite3.Connection: Read-only database connection
        """
        # URI mode with read-only flag
        uri = f"file:{self.db_path}?mode=ro"
        return sqlite3.connect(uri, uri=True, check_same_thread=False)

    def load_species(self, force_reload=False):
        """
        Load all bird species from the database.

        This method loads species from the tblSpeciesCodes table and caches
        them in memory. Subsequent calls return the cached data unless
        force_reload is True.

        Why caching?
        - Species data is static (doesn't change during runtime)
        - Loading from database every request is slow
        - 73 species is small enough to fit in memory

        Args:
            force_reload: If True, reload from database even if cached

        Returns:
            list: List of dicts with 'code' and 'name' keys
                  Example: [{"code": "AMAV", "name": "American Avocet"}, ...]
        """
        # Return cached data if available
        if self._species_cache is not None and not force_reload:
            return self._species_cache

        species_list = []

        try:
            # Connect to database
            conn = self._get_connection()
            cursor = conn.cursor()

            # Query all species
            cursor.execute("""
                SELECT SpeciesCode, SpeciesName
                FROM tblSpeciesCodes
                ORDER BY SpeciesName
            """)

            # Convert to list of dicts
            for row in cursor.fetchall():
                code, name = row
                if code and name:  # Skip empty entries
                    species_list.append({
                        "code": code.strip(),
                        "name": name.strip()
                    })

            conn.close()

            # Cache the result
            self._species_cache = species_list

            print(f"✓ Loaded {len(species_list)} species from database")

        except sqlite3.Error as e:
            print(f"ERROR loading species from database: {e}")
            print(f"Database path: {self.db_path}")
            # Return empty list on error
            species_list = []

        return species_list

    def get_all_species(self):
        """
        Get all species (cached).

        Returns:
            list: List of species dicts
        """
        return self.load_species()

    def get_species_by_code(self, code):
        """
        Get species details by code.

        Args:
            code: Species code (e.g., "AMAV")

        Returns:
            dict: Species data, or None if not found
        """
        species_list = self.get_all_species()
        for species in species_list:
            if species["code"] == code:
                return species
        return None

    def get_species_count(self):
        """
        Get total number of species.

        Returns:
            int: Number of species
        """
        return len(self.get_all_species())


# Module-level singleton instance
# This is created once when the module is imported
_service_instance = None


def get_species_service(db_path=None):
    """
    Get the singleton species service instance.

    This function ensures we only create one SpeciesService instance
    for the entire application, which means species are only loaded
    from the database once.

    Args:
        db_path: Path to database (only used on first call)

    Returns:
        SpeciesService: The singleton instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SpeciesService(db_path)
        # Load species immediately to catch any errors early
        _service_instance.load_species()
    return _service_instance
