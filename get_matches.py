import cassiopeia as cass

ACCOUNT = 'YoRHa Destiny'
REGION = 'NA'

with open('api_key.txt') as f:
    key = f.readlines()[0]
    cass.set_riot_api_key(key)

Summoner = cass.Summoner

user = Summoner(name=ACCOUNT, region=REGION)

match_list = user.match_history
tmp_match = match_list[0]
print(tmp_match.timeline.frames[10].participant_frames[1].position.location)