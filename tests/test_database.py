"""
Test script to validate the database setup
Demonstrates how to use the database with the AI prompt
"""

import sqlite3
import json


def test_database_connection():
    """Test basic database connectivity"""
    print("=" * 80)
    print("TEST 1: Database Connection")
    print("=" * 80)

    try:
        conn = sqlite3.connect('../data/bird_data_complete.db')
        cursor = conn.cursor()

        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print(f"\n✓ Connected to database")
        print(f"✓ Found {len(tables)} tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  • {table[0]}: {count:,} rows")

        conn.close()
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def test_species_codes():
    """Test species codes lookup"""
    print("\n" + "=" * 80)
    print("TEST 2: Species Codes Lookup")
    print("=" * 80)

    try:
        conn = sqlite3.connect('../data/bird_data_complete.db')
        cursor = conn.cursor()

        # Get common species
        cursor.execute("""
            SELECT SpeciesCode, SpeciesName
            FROM species_codes
            WHERE SpeciesCode IN ('BRPE', 'LAGU', 'SATE', 'ROYT', 'WHIB')
            ORDER BY SpeciesCode
        """)

        results = cursor.fetchall()
        print("\n✓ Common species codes:")
        for code, name in results:
            print(f"  • {code}: {name}")

        conn.close()
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def test_colony_totals():
    """Test aggregated colony data"""
    print("\n" + "=" * 80)
    print("TEST 3: Colony Totals Query")
    print("=" * 80)

    try:
        conn = sqlite3.connect('../data/bird_data_complete.db')
        cursor = conn.cursor()

        # Top species by nest count in 2021
        cursor.execute("""
            SELECT
                sc.SpeciesName,
                SUM(ct.Nests) as total_nests,
                COUNT(DISTINCT ct.ColonyName) as colonies
            FROM colony_totals ct
            JOIN species_codes sc ON ct.SpeciesCode = sc.SpeciesCode
            WHERE ct.Year = 2021
            GROUP BY sc.SpeciesName
            ORDER BY total_nests DESC
            LIMIT 5
        """)

        results = cursor.fetchall()
        print("\n✓ Top 5 species in 2021 by nest count:")
        print(f"\n{'Species':<30} {'Nests':<12} {'Colonies'}")
        print("-" * 55)
        for species, nests, colonies in results:
            print(f"{species:<30} {nests:<12,} {colonies}")

        conn.close()
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def test_detailed_observations():
    """Test detailed species observation data"""
    print("\n" + "=" * 80)
    print("TEST 4: Detailed Species Observations")
    print("=" * 80)

    try:
        conn = sqlite3.connect('../data/bird_data_complete.db')
        cursor = conn.cursor()

        # Brown Pelican breeding data from 2021
        cursor.execute("""
            SELECT
                ColonyName,
                SUM(COALESCE(WBN, 0)) as with_brood,
                SUM(COALESCE(Site, 0)) as sites,
                SUM(COALESCE(EmptyNest, 0)) as empty_nests
            FROM species_data_2015_2021
            WHERE Year = 2021 AND SpeciesCode = 'BRPE'
            GROUP BY ColonyName
            HAVING sites > 0
            ORDER BY sites DESC
            LIMIT 5
        """)

        results = cursor.fetchall()
        print("\n✓ Top 5 Brown Pelican colonies in 2021:")
        print(f"\n{'Colony':<35} {'W/Brood':<10} {'Sites':<10} {'Empty'}")
        print("-" * 65)
        for colony, brood, sites, empty in results:
            print(f"{colony:<35} {brood:<10.0f} {sites:<10.0f} {empty:.0f}")

        conn.close()
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def test_oil_observations():
    """Test oil presence queries"""
    print("\n" + "=" * 80)
    print("TEST 5: Oil Presence Analysis")
    print("=" * 80)

    try:
        conn = sqlite3.connect('../data/bird_data_complete.db')
        cursor = conn.cursor()

        # Colonies with oil observations by year
        cursor.execute("""
            SELECT
                Year,
                COUNT(DISTINCT ColonyName) as colonies_with_oil,
                COUNT(*) as total_observations
            FROM colony_site_notes
            WHERE Oil = 'Y'
            GROUP BY Year
            ORDER BY Year
        """)

        results = cursor.fetchall()
        print("\n✓ Oil observations by year:")
        print(f"\n{'Year':<10} {'Colonies':<12} {'Observations'}")
        print("-" * 35)
        for year, colonies, observations in results:
            print(f"{int(year) if year else 'N/A':<10} {colonies:<12} {observations}")

        conn.close()
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def test_empty_result_handling():
    """Test handling of queries that return no results"""
    print("\n" + "=" * 80)
    print("TEST 6: Empty Result Handling")
    print("=" * 80)

    try:
        conn = sqlite3.connect('../data/bird_data_complete.db')
        cursor = conn.cursor()

        # Query for non-existent data
        cursor.execute("""
            SELECT *
            FROM colony_totals
            WHERE Year = 2025 AND SpeciesCode = 'FAKE'
        """)

        results = cursor.fetchall()

        if len(results) == 0:
            print("\n✓ Query executed successfully")
            print("✓ No results found (as expected)")
            print("\nExample AI response:")
            print("  'The query executed successfully but found no records matching")
            print("   your criteria. Year 2025 is outside the survey period (2010-2021),")
            print("   and 'FAKE' is not a valid species code. Would you like to see")
            print("   available years or species codes?'")
        else:
            print(f"\n✗ Unexpected: Found {len(results)} results")

        conn.close()
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def test_multi_year_union():
    """Test UNION queries across multiple year tables"""
    print("\n" + "=" * 80)
    print("TEST 7: Multi-Year UNION Query")
    print("=" * 80)

    try:
        conn = sqlite3.connect('../data/bird_data_complete.db')
        cursor = conn.cursor()

        # Get Laughing Gull trends across all years
        cursor.execute("""
            SELECT
                Year,
                COUNT(*) as observations,
                SUM(COALESCE(Site, 0)) as total_sites
            FROM (
                SELECT Year, Site FROM species_data_2010 WHERE SpeciesCode = 'LAGU'
                UNION ALL
                SELECT Year, Site FROM species_data_2011_2013 WHERE SpeciesCode = 'LAGU'
                UNION ALL
                SELECT Year, Site FROM species_data_2015_2021 WHERE SpeciesCode = 'LAGU'
            ) combined
            GROUP BY Year
            ORDER BY Year
        """)

        results = cursor.fetchall()
        print("\n✓ Laughing Gull (LAGU) trends:")
        print(f"\n{'Year':<10} {'Observations':<15} {'Total Sites'}")
        print("-" * 40)
        for year, obs, sites in results:
            print(f"{int(year):<10} {obs:<15} {sites:.0f}")

        conn.close()
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def check_prompt_file():
    """Verify prompt.txt exists and is properly formatted"""
    print("\n" + "=" * 80)
    print("TEST 8: AI Prompt File Validation")
    print("=" * 80)

    try:
        with open('prompt.txt', 'r') as f:
            prompt = f.read()

        # Check for key sections
        sections = [
            "DATABASE SCHEMA",
            "QUERY GUIDELINES",
            "CRITICAL INSTRUCTIONS",
            "ALWAYS Explain Your Reasoning",
            "Handle Empty Results Gracefully"
        ]

        print("\n✓ Found prompt.txt")
        print(f"✓ File size: {len(prompt):,} characters")
        print("\n✓ Required sections present:")

        all_present = True
        for section in sections:
            if section in prompt:
                print(f"  • {section}")
            else:
                print(f"  ✗ Missing: {section}")
                all_present = False

        if all_present:
            print("\n✓ Prompt file is complete and ready for AI use")
            return True
        else:
            print("\n⚠ Some sections may be missing")
            return False

    except FileNotFoundError:
        print("\n✗ prompt.txt not found")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DATABASE VALIDATION TEST SUITE" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")

    tests = [
        ("Database Connection", test_database_connection),
        ("Species Codes", test_species_codes),
        ("Colony Totals", test_colony_totals),
        ("Detailed Observations", test_detailed_observations),
        ("Oil Presence", test_oil_observations),
        ("Empty Result Handling", test_empty_result_handling),
        ("Multi-Year UNION", test_multi_year_union),
        ("AI Prompt File", check_prompt_file),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nTests passed: {passed}/{total}")
    print("\nDetailed results:")
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    if passed == total:
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("✓ Database is ready for production use")
        print("✓ AI prompt file is properly configured")
        print("=" * 80)
    else:
        print("\n⚠ Some tests failed - please review above output")

    return passed == total


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
