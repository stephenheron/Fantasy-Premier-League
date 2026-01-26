import os
import csv
from collector import collect_gw, regenerate_merged_gw

# =============================================================================
# CONFIGURATION - Modify these values as needed
# =============================================================================

SEASON = '2025-26'

# Set to None to auto-detect missing gameweeks, or specify a list e.g. [7, 10, 11, 12]
MISSING_GAMEWEEKS = None

# Set to True to regenerate merged_gw.csv after collecting
REGENERATE_MERGED = True

# =============================================================================


def get_existing_gameweeks(gw_dir):
    """Find which gameweek files already exist."""
    existing = set()
    if os.path.exists(gw_dir):
        for fname in os.listdir(gw_dir):
            if fname.startswith('gw') and fname.endswith('.csv') and fname != 'merged_gw.csv':
                try:
                    gw_num = int(fname[2:-4])
                    existing.add(gw_num)
                except ValueError:
                    continue
    return existing


def get_available_gameweeks(player_dir):
    """Find which gameweeks are available in player data."""
    available = set()

    # Sample first player directory to find available gameweeks
    for player_folder in os.listdir(player_dir):
        player_path = os.path.join(player_dir, player_folder)
        if os.path.isdir(player_path):
            gw_file = os.path.join(player_path, 'gw.csv')
            if os.path.exists(gw_file):
                with open(gw_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        available.add(int(row['round']))
                break  # Only need to check one player

    return available


def main():
    season_dir = f'data/{SEASON}/'
    player_dir = season_dir + 'players/'
    gw_dir = season_dir + 'gws/'

    # Determine which gameweeks to collect
    if MISSING_GAMEWEEKS is not None:
        gameweeks_to_collect = MISSING_GAMEWEEKS
    else:
        existing = get_existing_gameweeks(gw_dir)
        available = get_available_gameweeks(player_dir)
        gameweeks_to_collect = sorted(available - existing)

        print(f"Existing gameweek files: {sorted(existing)}")
        print(f"Available in player data: {sorted(available)}")

    if not gameweeks_to_collect:
        print("No missing gameweeks to collect.")
    else:
        print(f"Collecting gameweeks: {gameweeks_to_collect}")

        for gw in gameweeks_to_collect:
            print(f'  Collecting GW {gw}...')
            collect_gw(gw, player_dir, gw_dir, season_dir)

    if REGENERATE_MERGED:
        print("Regenerating merged_gw.csv...")
        regenerate_merged_gw(gw_dir)
        print("Done.")


if __name__ == '__main__':
    main()
