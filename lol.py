import requests as rq
from json import loads, dumps
import numpy as np
import traceback
import os
from OPGGModel import getPerformance
from tempfile import gettempdir
from time import time

bypass = "每把都是TOP GAP-MDZZ"
token = "RGAPI-f93917e1-bcd7-4009-b1ac-1810e0c8937a"
log_path = "D:\\Riot Games\\League of Legends\\Logs\\LeagueClient Logs" # 按需要修改實際路徑，必須是LeagueClient Logs資料夾

def makeHtmlPage(tables:list):
    tbs = ""
    for T in tables:
        tbs += T
    template = """
<html>
<style>
table, th, td {
  border:1px solid black;
  margin: 2px
}
div {
display:flex;
}
</style>
<body>
<div>
""" + tbs + """
</div>
</body>
</html>
"""
    ts = str(int(time()))
    open(f"{gettempdir()}/lol-team-check_{ts}.html", "wb").write(template.encode("utf-8"))
    os.system(f"{gettempdir()}/lol-team-check_{ts}.html")

def getOPDataHTML(name:str, tag:str):
    resp = getPerformance(f'{name}#{tag}')

    rks = []
    for match in resp['data']:
        rk = match['op_score_rank']
        rks.append(f'{rk}' if rk < 4 else f'<a style="color:red">{rk}</a>')
    rks = reversed(rks)
    html_rows = f"<tr><td colspan='7'><b>OP Score 同隊排名:</b><br>{"➡️".join(rks)}</td></tr>"
    
    mean_rk = resp['stats']['mean_rank']
    median_rk = resp['stats']['median_rank']
    mean_lane_score = resp['stats']['mean_lane_score']
    overall = f"平均排名: {mean_rk}, 中位數排名: {median_rk}, 平均對線分數: {mean_lane_score}/100"
    if mean_rk > 3 or median_rk > 3:
        html_rows += f"<tr><td colspan='7' bgcolor='pink'><b>{overall}</b></td>"
    else:
        html_rows += f"<tr><td colspan='7'><b>{overall}</b></td>"
    return html_rows

def checkTeammate(name:str, tag:str, bulkmode:bool):
    print(f"Checking: {name}#{tag}")
    if f"{name}-{tag}" == bypass and bulkmode:
        print("Skipped.")
        return ""
    #每把都是TOP GAP-MDZZ
    username = [name, tag]
    html_rows = f'''<table><tr><td colspan="7"><a href='https://www.op.gg/summoners/tw/{name}-{tag}' target="_blank">{name}-{tag}</a></td></tr>
    <tr><th>#</th><th>W/L</th><th>KDA</th><th>英雄</th><th>定位</th><th>同隊排名</th><th>線路優勢</th></tr>'''

    positions = ["TOP", "MIDDLE", "JUNGLE", "BOTTOM", "UTILITY"]
    score_weighting = { 
        # Aimed to provide an effective customized metric for each lane 
        # Score multiplication. All lanes should have same total bonus ratio (i.e. 100% addition)
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
            "visionScore": 1.33,
            "killParticipation": 1.33,
            "totalHealsOnTeammates": 1.33
        }
    }
    
    metrics_1v1 = ["damageDealtToTurrets", "totalDamageDealtToChampions", "totalDamageTaken", "visionScore", "kda", "killParticipation", "totalHealsOnTeammates"] # these metric can be extreme to some lanes
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

    account_detail = loads(rq.get(f"{api_account}/{username[0]}/{username[1]}", headers=headers).text)
    try:
        puuid = account_detail["puuid"]
    except:
        print(account_detail)
        return ""
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
        individual_scores = {"TOP": [0,0], "JUNGLE": [0,0], "MIDDLE": [0,0], "BOTTOM": [0,0], "UTILITY": [0,0]}

        for p in dto_participant:
            if p["puuid"] == account_detail["puuid"]:
                dto_target = p
            if p["teamPosition"]:
                dto_matchups[p["teamPosition"]].append(p)
            else:
                good_match = False
                 
            if dto_info["gameDuration"] < 800:
                good_match = False
            
            if not good_match:
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
            all_vals = []
            for p in dto_participant:
                val = 0
                if metric in challenge_metrics:
                    if metric in p["challenges"]:
                        val = p["challenges"][metric]
                else:
                    val = p[metric]
                all_vals.append(val)

            median_val = np.median(np.array(all_vals))

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
                scr_A = val_A/(val_A+median_val)
                scr_B = val_B/(val_B+median_val)
                # if metric in score_weighting[pos]:
                #     scr_A *= score_weighting[pos][metric]
                #     scr_B *= score_weighting[pos][metric]
                individual_scores[pos][0] += scr_A
                individual_scores[pos][1] += scr_B

        # for win lane stats
        individual_score = 0
        winlane_rate = 0
        for i in range(2):
            if dto_matchups[dto_target["teamPosition"]][i] == dto_target:
                individual_score = individual_scores[dto_target["teamPosition"]][i]
                target_score = matchup_scores[dto_target["teamPosition"]][i]
                opponent_score = matchup_scores[dto_target["teamPosition"]][abs(i-1)]
                winlane_rate = round((target_score - opponent_score)/opponent_score * 100, 2)
                if winlane_rate >= 0:
                    lane_wins += 1

        # for overall stats
        rank = 5
        for pos in positions:
            for i in range(2):
                if dto_matchups[pos][i] != dto_target and dto_target["win"] == dto_matchups[pos][i]["win"] and individual_score > individual_scores[pos][i]:
                    rank -= 1
        ranks.append(rank)
        print(f'[{cnt}] [{"勝" if dto_target["win"] else "敗"}][{dto_target["kills"]}/{dto_target["deaths"]}/{dto_target["assists"]}] \t隊伍排名: {rank}/5\t線路優勢: {winlane_rate}% [{dto_target["championName"]}]')
        
        html_row = f'''<tr>
        <td>{cnt}</td>
        <td>{"勝" if dto_target["win"] else "敗"}</td>
        <td>{dto_target["kills"]}/{dto_target["deaths"]}/{dto_target["assists"]}</td>
        <td>{dto_target["championName"]}</td>
        <td>{dto_target["teamPosition"][:3]}</td>
        <td style="color:{"red" if rank > 3 else "black"}">{rank}/5</td>
        <td style="color:{"red" if winlane_rate < 0 else "black"}">{winlane_rate}%</td>
        </tr>'''
        html_rows += html_row
        
        cnt += 1
        
    print("Summary: ")
    ranks = np.array(ranks)
    mean_rk = round(np.mean(ranks), 2)
    median_rk = np.median(ranks)
    total_lanewinrate = round((lane_wins/(cnt-1)) * 100, 2)
    sum_str = f"平均排名: {mean_rk}/5, 中位數排名: {median_rk}/5, 贏線率: {total_lanewinrate}%"
    print(sum_str, end=" ")
    
    if max(mean_rk, median_rk) >= 4 or total_lanewinrate < 40:
        print("<==!CAUTION!")
        html_rows += f"<tr><td colspan='7' bgcolor='pink'><b>{sum_str}</b></td>"
    else:
        print()
        html_rows += f"<tr><td colspan='7'><b>{sum_str}</b></td>"

    # opgg data
    html_rows += getOPDataHTML(name, tag)
    
    return html_rows + "</table>"
        
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
    raw = raw[:-1] + "]}" # comment this if check without client

    trace = loads(raw)["entries"]
    summoners = set()
    for i in range(len(trace)-1, -1, -1):
        if "ty" in trace[i] and "ur" in trace[i] and trace[i]["ty"] == "Update" and trace[i]["ur"] == "/chat/v5/participants/lol-champ-select":
            obj = loads(trace[i]["dds"])
            for user in obj["participants"]:
                summoners.add(f"{user['game_name']}-{user['game_tag']}")
                if len(summoners) == 5:
                    break
            if len(summoners) == 5:
                break
    tables = []
    for s in summoners:
        name = s.split("-")
        tables.append(checkTeammate(name[0], name[1], True))
        print()
        print("=" * 50)

    makeHtmlPage(tables)

def ask():
    print("1 -> 檢查個別玩家 | 2 -> 選角即時批量檢查")
    choice = input("輸入功能代號: ")
    if choice == "1":
        try:
            name = input("Input [name-tag]: ").split("-")
            makeHtmlPage([checkTeammate(name[0], name[1], False)])
        except Exception as e:
            traceback.print_exc()
    elif choice == "2":
        os.system("cls")
        getUsers()
    ask()

ask()
