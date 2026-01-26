import pandas as pd
import os
import csv
from understatapi import UnderstatClient

# =============================================================================
# CONFIGURATION - Modify these values as needed
# =============================================================================

# Season in FPL format (e.g., '2024-25')
# The understat year is derived automatically (e.g., '2024-25' -> 2024)
# Note: Understat data is only available for seasons that have started
SEASON = '2025-26'

# Set to True to also fetch individual player match data (slower)
FETCH_INDIVIDUAL_PLAYERS = True

# =============================================================================


def get_understat_year(season):
    """Convert FPL season format to understat year (e.g., '2025-26' -> '2025')."""
    return season.split('-')[0]


def get_epl_data(season=None):
    """Fetch EPL league data from understat using understatAPI."""
    if season is None:
        season = SEASON
    year = get_understat_year(season)

    print(f"Fetching EPL data for {year} season...")

    with UnderstatClient() as understat:
        # Get player data for the league
        try:
            player_data = understat.league(league="EPL").get_player_data(season=year)
        except Exception as e:
            print(f"\nError: Could not fetch data for {year} season.")
            print(f"This usually means the season data isn't available on Understat yet.")
            print(f"Try an earlier season like '2024-25' or '2023-24'.")
            print(f"\nOriginal error: {e}")
            return {}, []

        if not player_data:
            print(f"\nWarning: No player data found for {year} season.")
            return {}, []

        # Get team data - we need to fetch each team's match data
        team_data = {}
        teams = set(p['team_title'] for p in player_data)

        for team in teams:
            team_name = team.replace(' ', '_')
            print(f"  Fetching team data: {team}")
            try:
                match_data = understat.team(team=team_name).get_match_data(season=year)
                team_data[team_name] = {
                    'title': team,
                    'history': match_data
                }
            except Exception as e:
                print(f"    Warning: Could not fetch data for {team}: {e}")

    return team_data, player_data


def get_player_data(player_id):
    """Fetch individual player data from understat."""
    with UnderstatClient() as understat:
        player = understat.player(player=player_id)
        matches_data = player.get_match_data()
        shots_data = player.get_shot_data()
        # groups_data not directly available, return empty
        return matches_data, shots_data, {}


def parse_epl_data(outfile_base, season=None):
    """Parse and save EPL data to CSV files."""
    if season is None:
        season = SEASON

    team_data, player_data = get_epl_data(season)

    if not team_data and not player_data:
        print("No data to save.")
        return

    # Save team data
    for team_name, data in team_data.items():
        if data['history']:
            team_frame = pd.DataFrame.from_records(data['history'])
            team_frame.to_csv(
                os.path.join(outfile_base, f'understat_{team_name}.csv'),
                index=False
            )
            print(f"  Saved: understat_{team_name}.csv")

    # Save player summary data
    if player_data:
        player_frame = pd.DataFrame.from_records(player_data)
        player_frame.to_csv(
            os.path.join(outfile_base, 'understat_player.csv'),
            index=False
        )
        print(f"  Saved: understat_player.csv ({len(player_data)} players)")

    # Optionally fetch individual player match data
    if FETCH_INDIVIDUAL_PLAYERS and player_data:
        print(f"\nFetching individual player data ({len(player_data)} players)...")
        for i, p in enumerate(player_data):
            player_id = p['id']
            player_name = p['player_name'].replace(' ', '_')

            try:
                matches, shots, groups = get_player_data(player_id)
                if matches:
                    player_frame = pd.DataFrame.from_records(matches)
                    player_frame.to_csv(
                        os.path.join(outfile_base, f'{player_name}_{player_id}.csv'),
                        index=False
                    )
                if (i + 1) % 50 == 0:
                    print(f"  Progress: {i + 1}/{len(player_data)} players")
            except Exception as e:
                print(f"  Warning: Could not fetch data for {player_name}: {e}")

        print(f"  Completed individual player data")


class PlayerID:
    def __init__(self, us_id, fpl_id, us_name, fpl_name):
        self.us_id = str(us_id)
        self.fpl_id = str(fpl_id)
        self.us_name = us_name
        self.fpl_name = fpl_name


def match_ids(understat_dir, data_dir):
    """Match understat player IDs to FPL player IDs."""
    with open(os.path.join(understat_dir, 'understat_player.csv')) as understat_file:
        understat_inf = csv.DictReader(understat_file)
        ustat_players = {}
        for row in understat_inf:
            ustat_players[row['player_name']] = row['id']

    with open(os.path.join(data_dir, 'player_idlist.csv')) as fpl_file:
        fpl_players = {}
        fpl_inf = csv.DictReader(fpl_file)
        for row in fpl_inf:
            fpl_players[row['first_name'] + ' ' + row['second_name']] = row['id']

    players = []
    found = {}
    for k, v in ustat_players.items():
        if k in fpl_players:
            player = PlayerID(v, fpl_players[k], k, k)
            players += [player]
            found[k] = True
        else:
            player = PlayerID(v, -1, k, "")
            players += [player]

    for k, v in fpl_players.items():
        if k not in found:
            player = PlayerID(-1, v, "", k)
            players += [player]

    with open(os.path.join(data_dir, 'id_dict.csv'), 'w+') as outf:
        outf.write('Understat_ID,FPL_ID,Understat_Name,FPL_Name\n')
        for p in players:
            outf.write(f"{p.us_id},{p.fpl_id},{p.us_name},{p.fpl_name}\n")

    print(f"  Saved: id_dict.csv ({len(players)} players)")


def main():
    """Generate understat data for the configured season.

    Usage:
        python understat.py              # Generate understat data
        python understat.py --match-ids  # Only match player IDs
        python understat.py --quick      # Generate without individual player data
    """
    import sys

    season_dir = f'data/{SEASON}/'
    understat_dir = f'{season_dir}understat/'

    # Create directory if it doesn't exist
    os.makedirs(understat_dir, exist_ok=True)

    if len(sys.argv) > 1 and sys.argv[1] == '--match-ids':
        print(f"Matching player IDs for {SEASON}...")
        match_ids(understat_dir, season_dir)
    elif len(sys.argv) > 1 and sys.argv[1] == '--quick':
        print(f"Generating understat data for {SEASON} (quick mode)...")
        global FETCH_INDIVIDUAL_PLAYERS
        FETCH_INDIVIDUAL_PLAYERS = False
        parse_epl_data(understat_dir, SEASON)
        print("\nDone.")
    else:
        print(f"Generating understat data for {SEASON}...")
        parse_epl_data(understat_dir, SEASON)
        print("\nDone.")
        print(f"\nTo match player IDs, run: python understat.py --match-ids")


if __name__ == '__main__':
    main()
