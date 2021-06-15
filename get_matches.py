import cassiopeia as cass
import sqlite3

DATABASE = "league.db"
DATABASE_LAYOUT = "db_layout.txt"
API_INFO = "api_key.txt"
ACCOUNT = 'YoRHa Destiny'
REGION = 'NA'

def user_init():
    with open(API_INFO) as f:
        key = f.readlines()[0]
        cass.set_riot_api_key(key)
    user = cass.Summoner(name=ACCOUNT, region=REGION)
    print(f"API authorized. Account id: {user.id}")
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


def main():
    user_init()
    db_init()


main()
# match_list = user.match_history
# tmp_match = match_list[0]
# print(tmp_match.blue_team.bans[0].name)