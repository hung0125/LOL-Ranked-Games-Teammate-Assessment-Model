import requests as rq
from json import loads, dumps
import numpy as np
import traceback
import os

bypass = "你自己的ID-TAG名稱"
token = "RIOT API TOKEN"
log_path = "D:\\Riot Games\\League of Legends\\Logs\\LeagueClient Logs" # 按需要修改實際路徑，必須是LeagueClient Logs資料夾

def checkTeammate(name:str, tag:str):
    print(f"Checking: {name}#{tag}")
    if f"{name}-{tag}" == bypass:
        print("Skipped.")
        return
    #每把都是TOP GAP-MDZZ
    username = [name, tag]

    positions = ["TOP", "MIDDLE", "JUNGLE", "BOTTOM", "UTILITY"]
    score_weighting = { 
        # Aimed to provide an effective customized metric for each lane 
        # Score multiplication. All lanes should have same total bonus ratio
        # CC, heal to teammate don't count because its final outcome is still kill participation
        "TOP": {
            "damageDealtToTurrets": 2,
        },
        "MIDDLE": {
            "totalDamageDealtToChampions": 1.5,
            "killParticipation": 1.5
        },
        "JUNGLE": {
            "killParticipation": 2
        },
        "BOTTOM": {
            "totalDamageDealtToChampions": 1.5,
            "killParticipation": 1.5
        },
        "UTILITY": {
            "visionScore": 1.5,
            "killParticipation": 1.5
        }
    }

    metrics_1v1 = ["damageDealtToTurrets", "totalDamageDealtToChampions", "visionScore", "kda"] # these metric can be extreme to some lanes
    metrics_1v9 = ["kda", "killParticipation"] # fair metrics
    challenge_metrics = ["kda", "killParticipation"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,zh-HK;q=0.8,zh;q=0.7,zh-TW;q=0.6",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com",
        "X-Riot-Token": token
    }

    api_account = "https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id"
    api_matches =  "https://sea.api.riotgames.com/lol/match/v5/matches/by-puuid"
    api_match = "https://sea.api.riotgames.com/lol/match/v5/matches"

    #{"puuid":"68Lv5MYrVEo7cwNQdRgj-otlOtqlxLMta1CxOt8krZOldpK95VSz7w36xk2oMbcYq3tAi_QPS12x_w","gameName":"每把都是TOP GAP","tagLine":"MDZZ"}
    account_detail = loads(rq.get(f"{api_account}/{username[0]}/{username[1]}", headers=headers).text)
    puuid = account_detail["puuid"]
    match_ids = loads(rq.get(f"{api_matches}/{puuid}/ids?queue=420&start=0&count=10", headers=headers).text)

    print(match_ids)
    cnt = 1
    ranks = []
    lane_wins = 0
    for match in match_ids:
        match_detail = loads(rq.get(f"{api_match}/{match}", headers=headers).text)
        good_match = True
        dto_info = match_detail["info"]
        dto_participant = dto_info["participants"]
        # https://riot-api-libraries.readthedocs.io/en/latest/roleid.html
        dto_target = None
        dto_matchups = {"TOP": [], "JUNGLE": [], "MIDDLE": [], "BOTTOM": [], "UTILITY": []} # stores participants
        matchup_scores = {"TOP": [0,0], "JUNGLE": [0,0], "MIDDLE": [0,0], "BOTTOM": [0,0], "UTILITY": [0,0]}

        for p in dto_participant:
            if p["puuid"] == account_detail["puuid"]:
                dto_target = p
            if p["teamPosition"]:
                dto_matchups[p["teamPosition"]].append(p)
            if dto_info["gameDuration"] < 800:
                good_match = False
                break

        if not good_match:
            continue
        # VS opponent
        for pos in positions:
            for metric in metrics_1v1:
                val_A = 0
                val_B = 0
                if metric in challenge_metrics:
                    val_A = dto_matchups[pos][0]["challenges"][metric]
                    val_B = dto_matchups[pos][1]["challenges"][metric]
                else:
                    val_A = dto_matchups[pos][0][metric]
                    val_B = dto_matchups[pos][1][metric]
                if val_A == 0 and val_B == 0:
                    continue
                scr_A = val_A/(val_A+val_B)
                scr_B = val_B/(val_A+val_B)
                if metric in score_weighting[pos]:
                    scr_A *= score_weighting[pos][metric]
                    scr_B *= score_weighting[pos][metric]
                matchup_scores[pos][0] += scr_A
                matchup_scores[pos][1] += scr_B
        # VS all
        for metric in metrics_1v9:
            sum_val = 0
            for p in dto_participant:
                val = 0
                if metric in challenge_metrics:
                    if metric in p["challenges"]:
                        val = p["challenges"][metric]
                else:
                    val = p[metric]
                sum_val += val

            avg_val = sum_val/10

            for pos in positions:
                val_A = 0
                val_B = 0
                if metric in challenge_metrics:
                    if metric in dto_matchups[pos][0]["challenges"]:
                        val_A = dto_matchups[pos][0]["challenges"][metric]
                    if metric in dto_matchups[pos][1]["challenges"]:
                        val_B = dto_matchups[pos][1]["challenges"][metric]
                else:
                    val_A = dto_matchups[pos][0][metric]
                    val_B = dto_matchups[pos][1][metric]
                if val_A == 0 and val_B == 0:
                    continue
                scr_A = val_A/(val_A+avg_val)
                scr_B = val_B/(val_B+avg_val)
                if metric in score_weighting[pos]:
                    scr_A *= score_weighting[pos][metric]
                    scr_B *= score_weighting[pos][metric]
                matchup_scores[pos][0] += scr_A
                matchup_scores[pos][1] += scr_B

        target_score = 0
        winlane_rate = 0
        for i in range(2):
            if dto_matchups[dto_target["teamPosition"]][i] == dto_target:
                target_score = matchup_scores[dto_target["teamPosition"]][i]
                opponent_score = matchup_scores[dto_target["teamPosition"]][abs(i-1)]
                winlane_rate = round((target_score - opponent_score)/opponent_score * 100, 2)
                if winlane_rate >= 0:
                    lane_wins += 1
        rank = 5
        for pos in positions:
            for i in range(2):
                if dto_matchups[pos][i] != dto_target and dto_target["win"] == dto_matchups[pos][i]["win"] and target_score > matchup_scores[pos][i]:
                    rank -= 1
        ranks.append(rank)
        print(f'[{cnt}] [{"勝" if dto_target["win"] else "敗"}][{dto_target["kills"]}/{dto_target["deaths"]}/{dto_target["assists"]}] \tTeam rank: {rank}/5\t贏線率: {winlane_rate}%')
        cnt += 1
        
    print("Summary: ")
    ranks = np.array(ranks)
    mean_rk = round(np.mean(ranks), 2)
    median_rk = np.median(ranks)
    total_lanewinrate = (lane_wins/(cnt-1)) * 100 
    print(f"平均排名: {mean_rk}/5, 中位數排名: {median_rk}/5, 總贏線率: {total_lanewinrate}%", end=" ")
    if max(mean_rk, median_rk) >= 4 or total_lanewinrate < 40:
        print("<==!CAUTION!")

def get_latest_modified_json_trace(directory):
    latest_modified_time = 0
    latest_modified_file = None

    for root, directories, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if file_path.endswith('.json'):
                modified_time = os.path.getmtime(file_path)
                if modified_time > latest_modified_time:
                    latest_modified_time = modified_time
                    latest_modified_file = file_path

    return latest_modified_file

def getUsers():
    raw = open(get_latest_modified_json_trace(log_path), "rb").read().decode("utf-8")
    raw = raw.strip()
    raw = raw[:-1] + "]}"

    trace = loads(raw)["entries"]
    summoners = set()
    for i in range(len(trace)-1, -1, -1):
        if "ty" in trace[i] and "ur" in trace[i] and trace[i]["ty"] == "Update" and trace[i]["ur"] == "/chat/v5/participants/champ-select":
            obj = loads(trace[i]["dds"])
            for user in obj["participants"]:
                summoners.add(f"{user['game_name']}-{user['game_tag']}")
                if len(summoners) == 5:
                    break
            if len(summoners) == 5:
                break
    for s in summoners:
        name = s.split("-")
        checkTeammate(name[0], name[1])
        print()
        print("=" * 50)

def ask():
    print("1 -> 檢查個別玩家 | 2 -> 選角即時批量檢查")
    choice = input("輸入功能代號: ")
    if choice == "1":
        try:
            name = input("Input [name-tag]: ").split("-")
            checkTeammate(name[0], name[1])
        except Exception as e:
            traceback.print_exc()
    elif choice == "2":
        os.system("cls")
        getUsers()
    ask()

ask()
