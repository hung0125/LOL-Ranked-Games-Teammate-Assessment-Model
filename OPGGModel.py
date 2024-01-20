import requests as rq
import urllib.parse
import numpy as np
from numpy import mean, median
from json import loads, dumps

headers = {
    "Content-Type": "application/json",
    "X-OPGG-OCM-Service": "OCMAPI-7FB8E453-1886-4B50-A6CB-43F49212BA98",
    "X-OPGG-Service": '0TaeV8zQcZjoWaRUC3EPy6qVxy6GuToA',
    "User-Agent": "OP.GG Mobile-lol Android (6.7.4);X-DEVICE-WIDTH=480.0;X-DEVICE-LANGUAGE=en;" 
}

domain1 = 'https://lol-api-summoner.op.gg/api/v2/TW'
domain2 = 'https://lol-api-summoner.op.gg/api/TW'

def getId(nametag:str):
    nametag = urllib.parse.quote(nametag)
    response = rq.get(f"{domain1}/summoners?riot_id={nametag}%0A&page=1", headers=headers)
    return loads(response.text)['data'][0]['summoner_id']

def getMatches(sum_id:str) -> dict:
    response = rq.get(f"{domain2}/summoners/{sum_id}/games?hl=en_US&game_type=SOLORANKED&champion=&position_type=&ended_at=2024-01-20T23%3A41%3A06.955&limit=10", headers=headers)
    return loads(response.text)['data']

def getMatchesByNameTag(nametag:str) -> dict:
    id = getId(nametag)
    return getMatches(id)

def getPerformance(nametag:str):
    nametag = nametag.split('#')
    name = nametag[0]
    tag = nametag[1]

    matches = getMatchesByNameTag('#'.join(nametag))
    result = { 'stats': {
        'mean_rank': 0,
        'median_rank': 0,
        'mean_lane_score': 0,
        'rate_of_win_lane': 0,
    }, 'data': []}
    ranks = []
    lane_scores = []
    times_won_lane = 0
    for M in matches:
        for P in M['participants']:
            profile = P['summoner']
            if profile['game_name'] == name and profile['tagline'] == tag:
                stats = P['stats']
                obj = {
                    "op_score": stats['op_score'],
                    "op_score_rank": 5,
                    "lane_score_target_vs_opponent": stats['lane_score']
                }
                for PP in M['participants']:
                    other_pf = PP['summoner']
                    other_st = PP['stats']

                    cond_1 = other_pf['game_name'] != name
                    cond_2 = other_pf['tagline'] != tag
                    if cond_1 and cond_2:
                        cond_3 = other_st['result'] == stats['result']
                        cond_4 = other_st['op_score_rank'] > stats['op_score_rank']

                        if cond_3 and cond_4:
                            obj['op_score_rank'] -= 1
                
                # print(obj)
                result['data'].append(obj)

                ranks.append(obj['op_score_rank'])
                lane_scores.append(obj['lane_score_target_vs_opponent'])
                if stats['lane_score'] > 50:
                    times_won_lane += 1
                break
    result['stats']['mean_rank'] = round(mean(np.array(ranks)), 2)
    result['stats']['median_rank'] = median(np.array(ranks))
    result['stats']['mean_lane_score'] = round(mean(np.array(lane_scores)), 2)
    result['stats']['rate_of_win_lane'] = str(times_won_lane/10 * 100) + '%'
    return result

print(dumps(getPerformance("name#tagline")))