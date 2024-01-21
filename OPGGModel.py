import requests as rq
import urllib.parse
import numpy as np
from zoneinfo import ZoneInfo
from numpy import mean, median
from json import loads, dumps
from datetime import datetime
from time import sleep

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

def renew(sum_id:str) -> bool:
    rq.post(f"{domain2}/summoners/{sum_id}/renewal", headers=headers).text
    for i in range(3): # check 3 times
        response2 = loads(rq.get(f"{domain2}/summoners/{sum_id}/renewal-status", headers=headers).text)
        # print(response2.text)
        if 'message' in response2 and response2['message'] == 'Already renewed.':
            return True
        sleep(1)

    return False

def getMatches(sum_id:str) -> dict:
    current_timestamp = datetime.now(tz=ZoneInfo("Asia/Tokyo"))
    iso_time = urllib.parse.quote(current_timestamp.isoformat()[:-3])
    response = rq.get(f"{domain2}/summoners/{sum_id}/games?hl=en_US&game_type=SOLORANKED&champion=&position_type=&ended_at={iso_time}&limit=10", headers=headers)
    return loads(response.text)['data']

def getMatchesByNameTag(nametag:str) -> dict:
    id = getId(nametag)
    return getMatches(id)

def getPerformance(nametag:str):
    id = getId(nametag)
    matches = getMatches(id)
    result = { 'stats': {
        'mean_rank': -1,
        'median_rank': -1,
        'mean_lane_score': -1,
        # 'rate_of_win_lane': 0,
    }, 'data': []}
    ranks = []
    lane_scores = []

    times_won_lane = 0
    test = []
    for M in matches:
        if (M['is_remake']):
            continue

        for P in M['participants']:
            profile = P['summoner']
            if profile['summoner_id'] == id:
                stats = P['stats']
                obj = {
                    "op_score": round(stats['op_score'], 1),
                    "op_score_rank": 5,
                    "lane_score_target_vs_opponent": stats['lane_score']
                }
                test.append([stats['kill'], stats['death'], stats['assist']])
                
                for PP in M['participants']:
                    other_pf = PP['summoner']
                    other_st = PP['stats']
                    
                    if other_pf['summoner_id'] != id:
                        cond_1 = PP['team_key'] == P['team_key']
                        cond_2 = other_st['op_score_rank'] > stats['op_score_rank']
                        
                        if cond_1 and cond_2:
                            obj['op_score_rank'] -= 1
                
                # print(obj)
                result['data'].append(obj)

                ranks.append(obj['op_score_rank'])
                if obj['lane_score_target_vs_opponent'] != None:
                    lane_scores.append(obj['lane_score_target_vs_opponent'])
                if stats['lane_score'] != None and stats['lane_score'] > 50:
                    times_won_lane += 1
                break
    if len(ranks) > 0:
        result['stats']['mean_rank'] = round(mean(np.array(ranks)), 2)
        result['stats']['median_rank'] = median(np.array(ranks))
    if len(lane_scores) > 0:
        result['stats']['mean_lane_score'] = round(mean(np.array(lane_scores)), 2)
    # result['stats']['rate_of_win_lane'] = str(times_won_lane/10 * 100) + '%'
    print(test)
    return result
