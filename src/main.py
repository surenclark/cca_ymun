import argparse
from collections import defaultdict

from mun import Conference, Organ
from sheets import download_sheets

SHEET_URL = "https://docs.google.com/spreadsheets/d/12gOwqAfFz0pJLW8SJz58vopMzc-1xVWhMoIf2En8x5Y/edit"

def run_conference():
    """Test the conference with detailed output"""
    print("\n" + "=" * 60)
    print("🏛️  TESTING CONFERENCE WITH REAL DATA")
    print("=" * 60)

    conf = Conference("MUN 2024")

    # 1. Load committees
    print("\n" + "-" * 40)
    print("STEP 1: Loading Committees")
    print("-" * 40)
    conf.load_committees_from_csv('test_data/committees.csv')
    print(f"\nCommittees loaded: {len(conf.committees)}")

    # Show committees by organ
    print("\nCommittees by Organ:")
    for organ in Organ:
        committees = conf.get_committees_by_organ(organ)
        if committees:
            print(f"  {organ.name}: {len(committees)} committees")
            for c in sorted(committees)[:3]:
                print(f"    • {c}")

    # 2. Load positions
    print("\n" + "-" * 40)
    print("STEP 2: Loading Positions")
    print("-" * 40)
    conf.load_positions_from_csv('test_data/all_positions.csv')

    position_counts = [(c, len(p)) for c, p in conf.committee_positions.items()]
    position_counts.sort(key=lambda x: x[1], reverse=True)

    print("\nTop 5 committees by positions:")
    for c, count in position_counts[:5]:
        print(f"  • {c}: {count} positions")

    total = sum(len(p) for p in conf.committee_positions.values())
    print(f"\nTotal positions: {total}")

    # 3. Load preferences
    print("\n" + "-" * 40)
    print("STEP 3: Loading Delegation Preferences")
    print("-" * 40)
    conf.load_country_regions('test_data/country_regions.csv')
    conf.load_delegations_from_preference_form('test_data/preferences.csv')
    # Validate country preferences
    country_analysis = conf.validate_country_preferences()
    conf._init_assignment_tracking()
    conf.print_distribution()
    print("\n🌍 Country Preferences by Region:")
    for region, count in country_analysis['by_region'].items():
        print(f"  • {region}: {count} requests")

    # 4. Print full summary
    print("\n" + "=" * 60)
    print("📊 CONFERENCE SUMMARY")
    print("=" * 60)
    conf.print_summary()

    conf.optimize_assignments()


    return conf


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--download', action='store_true')
    args = parser.parse_args()

    if args.download:
        download_sheets(SHEET_URL)
        print("\n✅ Download complete!")
        conference = run_conference()
    else:
        conference = run_conference()