"""Download NBA player/team game logs into data/*.csv (skips files already there)."""
import os, time
from nba_api.stats.endpoints import playergamelogs, teamgamelogs

SEASONS = [f"{y}-{str(y + 1)[2:]}" for y in range(2010, 2023)]  # 2010-11 to 2022-23 (injury data ends 2023-04)
for name, ep in [("player_games", playergamelogs.PlayerGameLogs), ("team_games", teamgamelogs.TeamGameLogs)]:
    for s in SEASONS:
        if os.path.exists(f"data/{name}_{s}.csv"):
            continue
        df = ep(season_nullable=s, timeout=60).get_data_frames()[0]
        df.to_csv(f"data/{name}_{s}.csv", index=False)
        print(name, s, df.shape)
        time.sleep(1)  # be polite to nba.com
