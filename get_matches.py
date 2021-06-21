from genericpath import exists
import cassiopeia as cass
import sqlite3
import arrow
from os import path

DATABASE = "league.db"
DATABASE_LAYOUT = "db_layout.txt"
API_INFO = "api_key.txt"
LAST_UPDATE = "last_update.txt"
ACCOUNT = 'YoRHa Destiny'
REGION = 'NA'
MAX_MATCHES = 4

target_id = -1


def user_init():
    global target_id
    with open(API_INFO) as f:
        key = f.readline()
        cass.set_riot_api_key(key)
    user = cass.Summoner(name=ACCOUNT, region=REGION)
    target_id = user.id
    print(f"API authorized. Account id: {target_id}")
    return user


def db_init():
    conn = sqlite3.connect(DATABASE)
    if conn is None:
        print("Database cannot be connected to. Quitting")
        quit()
    cur = conn.cursor()
    with open (DATABASE_LAYOUT) as f:
        table_strs = f.readlines()
        for table_str in table_strs:
            table_name, column_str = table_str.strip().split(":")
            cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({column_str});")
    print("Database connected.")
    return conn


def new_matches(user):
    time = None
    # if path.exists(LAST_UPDATE):
    #     with open(LAST_UPDATE) as f:
    #         time = arrow.get(f.readline())
    # Ugh ... list[0] is the most recent match but begin_time is the earliest match
    now = arrow.utcnow()
    matches = user.match_history(begin_time=time, end_time=now, end_index=MAX_MATCHES)
    with open(LAST_UPDATE, "w") as f:
        f.write(str(now))
    print("Recent matches obtained.")
    return matches


def scan_timeline(summ, timeline, id_map):
    TIME_LIMIT = 15 * 60
    CHAMP_MAP = ["TOP_LANE", "JUNGLE", "MID_LANE", "DUO_CARRY", "DUO_SUPPORT"]
    death_count = [0] * 5
    for event in timeline.events:
        if event.timestamp.total_seconds < TIME_LIMIT:
            break
        if event.type == "CHAMPION_KILL" and event.victim_id == summ.id:
            summ = id_map[event.killer_id]
            role = summ.lane.value
            role = role if role != "BOT_LANE" else summ.role.value
            death_count[CHAMP_MAP.index(role)] += 1
    print(death_count)


def enter_summ(cur, team_id, summ, category, seconds, id_map):
    scan_timeline(summ, summ.timeline, id_map)
    stats = summ.stats
    # Enter individual champ
    role = summ.lane.value
    role = role if role != "BOT_LANE" else summ.role.value
    params = (team_id, category, summ.summoner.id, summ.champion.name, role,
                stats.win, stats.kda, stats.kills, stats.deaths, 
                stats.assists, stats.total_minions_killed, seconds, stats.gold_earned, 
                stats.damage_dealt_to_objectives, stats.damage_dealt_to_turrets, 
                stats.total_damage_dealt_to_champions, stats.total_damage_dealt, 
                stats.time_CCing_others)
    cur.execute("INSERT INTO summs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                params)
    # Now add to summary statistics
    cur.execute(f"SELECT * FROM summary WHERE category = ? AND champ = ?", (category, summ.champion.name))
    res = cur.fetchone()
    qry_str = "INSERT OR REPLACE INTO summary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (params[1], params[3], 1) + params[5:]
    if res is not None: 
        params = (category, summ.champion.name) + tuple([params[i] + res[i] for i in range(2, len(params))])
    cur.execute(qry_str, params)
    return stats.kills, stats.deaths
    
    

def enter_team(cur, color, team, match_id, team_id, seconds, id_map, has_tgt):
    bans = team.bans
    bans = ["None" if c is None else c.name for c in bans]
    ban_str = bans[0]
    for ban in bans[1:]:
        ban_str += f",{ban}"

    on_team = False
    for summ in team.participants:
        if summ.summoner.id == target_id:
            on_team = True

    category = "NI" # Not involved
    if has_tgt:
        category = "T" if on_team else "E" # Team and Enemy
    total_kills, total_deaths = 0, 0
    for summ in team.participants:
        stats = enter_summ(cur, team_id, summ, category, seconds, id_map)
        total_kills += stats[0]
        total_deaths += stats[1]
    cur.execute("INSERT INTO teams VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (match_id, team_id, category, color, team.win, ban_str, total_kills, 
                    total_deaths, team.baron_kills, team.dragon_kills, team.inhibitor_kills, 
                    team.tower_kills, team.first_blood, team.first_tower))
    


def enter_matches(conn, matches, has_tgt):
    # A little weird - we want unique IDs for teams to make a hierarchy from match->team->players with
    # foreign keys. However, RIOT for good reason doesn't give team ids, so we'll make our own
    cur = conn.cursor()
    cur.execute("SELECT MAX(team_id) FROM teams")
    result = cur.fetchone()[0]
    team_id = 0 if result is None else 1 + int(result)
    
    for match in matches:
        # id_map[0] is just used so I don't have to subtract one each time from the id list
        id_map = ["SHOULD NOT BE SELECTED"] + [""] * 10
        for part in match.participants:
            id_map[part.id] = part
        seconds = match.duration.seconds
        # If the match isn't remade or ended by any weird stuff w/ people leaving pre-15
        if seconds >= 15 * 60:
            cur.execute("INSERT INTO matches VALUES (?, ?, ?)", (match.id, has_tgt, seconds))
            enter_team(cur, "blue", match.blue_team, match.id, team_id, seconds, id_map, has_tgt)
            enter_team(cur, "red", match.red_team, match.id, team_id + 1, seconds, id_map, has_tgt)
            team_id += 2
            conn.commit()


def main():
    user = user_init()
    conn = db_init()
    matches = new_matches(user)
    enter_matches(conn, matches, True)
    conn.close()


main()