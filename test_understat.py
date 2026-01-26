from understatapi import UnderstatClient
understat = UnderstatClient()
league_player_data = understat.league(league="EPL").get_player_data(season="2019")
print(f"Found {len(league_player_data)} players")
