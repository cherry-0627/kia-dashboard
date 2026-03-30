import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9"
}

TEAM_ENG_KOR = {
    'KIA': 'KIA 타이거즈', 'LG': 'LG 트윈스', 'SAMSUNG': '삼성 라이온즈',
    'HANWHA': '한화 이글스', 'SSG': 'SSG 랜더스', 'NC': 'NC 다이노스',
    'KT': 'KT 위즈', 'LOTTE': '롯데 자이언츠', 'DOOSAN': '두산 베어스',
    'KIWOOM': '키움 히어로즈'
}
DAY_MAP = {'MON':'월','TUE':'화','WED':'수','THU':'목','FRI':'금','SAT':'토','SUN':'일'}
VALID_TEAMS = set(TEAM_ENG_KOR.keys())

# 선수 번호 매핑
PLAYER_NUM = {
    '카스트로':'53','김선빈':'3','나성범':'22','데일':'58','김도영':'5',
    '박민':'2','윤도현':'99','김호령':'18','한준수':'27','오선우':'56',
    '박재현':'15','네일':'47','올러':'49','양현종':'11','이의리':'35',
    '김태형':'17','최지민':'39','조상우':'1'
}
PLAYER_POS = {
    '카스트로':'지명타자','김선빈':'2루수','나성범':'우익수','데일':'유격수',
    '김도영':'유격수','박민':'3루수','윤도현':'내야수','김호령':'중견수',
    '한준수':'포수','오선우':'1루수','박재현':'외야수'
}
MAIN_HITTERS = ['카스트로','나성범','김선빈','김도영','데일','박민']
FAV_HITTERS = ['오선우','박재현']
MAIN_PITCHERS = ['네일','올러','양현종','이의리','김태형']
FAV_PITCHERS = ['최지민']

def get_standings():
    url = "https://eng.koreabaseball.com/Standings/TeamStandings.aspx"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table")[0].select("tr")[1:]
        standings = []
        for row in rows:
            cols = row.select("td")
            if len(cols) < 8:
                continue
            try:
                rank = int(cols[0].get_text(strip=True))
            except:
                continue
            team_eng = cols[1].get_text(strip=True).upper()
            team_kor = TEAM_ENG_KOR.get(team_eng, team_eng)
            standings.append({
                "rank": rank, "team": team_kor,
                "g": cols[2].get_text(strip=True),
                "w": cols[3].get_text(strip=True),
                "l": cols[4].get_text(strip=True),
                "pct": cols[6].get_text(strip=True),
                "gb": cols[7].get_text(strip=True),
                "kia": team_eng == 'KIA'
            })
        print(f"순위: {len(standings)}팀 수집")
        return standings
    except Exception as e:
        print(f"standings error: {e}")
        return []

def get_kia_schedule():
    url = "https://eng.koreabaseball.com/Schedule/DailySchedule.aspx"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            return []
        rows = table.select("tr")
        games = []
        current_date_raw = ""
        for row in rows:
            cols = row.select("td")
            if not cols:
                continue
            first = cols[0].get_text(strip=True)
            if re.match(r'\d{2}\.\d{2}\(\w+\)', first):
                current_date_raw = first
            col_texts = [c.get_text(strip=True).upper() for c in cols]
            if 'KIA' not in col_texts:
                continue
            for i, txt in enumerate(col_texts):
                score_m = re.match(r'^(\d+):(\d+)$', txt)
                if not score_m or i == 0 or i >= len(col_texts) - 1:
                    continue
                away = col_texts[i-1]
                home = col_texts[i+1]
                if away not in VALID_TEAMS or home not in VALID_TEAMS:
                    continue
                if 'KIA' not in away and 'KIA' not in home:
                    continue
                away_score = int(score_m.group(1))
                home_score = int(score_m.group(2))
                if 'KIA' in away:
                    kia_s, opp_s, opp_eng, venue = away_score, home_score, home, '원정'
                else:
                    kia_s, opp_s, opp_eng, venue = home_score, away_score, away, '홈'
                opp_short = TEAM_ENG_KOR.get(opp_eng, opp_eng).split(' ')[0]
                result = 'win' if kia_s > opp_s else ('lose' if kia_s < opp_s else 'draw')
                day_m = re.search(r'\((\w+)\)', current_date_raw)
                day_kor = DAY_MAP.get(day_m.group(1), '') if day_m else ''
                date_str = f"{current_date_raw[:5]}({day_kor})" if current_date_raw else ""
                games.append({"date": date_str, "opp": f"vs {opp_short}", "score": f"{kia_s}-{opp_s}", "result": result, "venue": venue})
                break
        print(f"KIA 경기: {len(games)}경기 수집")
        return games
    except Exception as e:
        print(f"schedule error: {e}")
        return []

def get_kia_hitters():
    # KIA 팀 필터로 타자 기록 수집
    url = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx"
    params = {"teamCode": "HT", "sort": "HRA_RT"}  # HT = KIA
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            print("타자 테이블 없음")
            return {}
        rows = table.select("tbody tr") or table.select("tr")[1:]
        hitters = {}
        for row in rows:
            cols = row.select("td")
            if len(cols) < 9:
                continue
            name = cols[1].get_text(strip=True)
            team = cols[2].get_text(strip=True)
            if team != 'KIA':
                continue
            try:
                hitters[name] = {
                    "avg": cols[3].get_text(strip=True),
                    "g": cols[4].get_text(strip=True),
                    "ab": cols[6].get_text(strip=True),
                    "r": cols[7].get_text(strip=True),
                    "h": cols[8].get_text(strip=True),
                    "hr": cols[11].get_text(strip=True) if len(cols) > 11 else '0',
                    "rbi": cols[13].get_text(strip=True) if len(cols) > 13 else '0',
                    "bb": '0', "so": '0', "obp": '-', "slg": '-', "ops": '-'
                }
            except:
                continue
        print(f"KIA 타자: {len(hitters)}명 수집 - {list(hitters.keys())[:5]}")
        return hitters
    except Exception as e:
        print(f"hitter error: {e}")
        return {}

def get_kia_pitchers():
    url = "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx"
    params = {"teamCode": "HT", "sort": "ERA_RT"}
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            print("투수 테이블 없음")
            return {}
        rows = table.select("tbody tr") or table.select("tr")[1:]
        pitchers = {}
        for row in rows:
            cols = row.select("td")
            if len(cols) < 10:
                continue
            name = cols[1].get_text(strip=True)
            team = cols[2].get_text(strip=True)
            if team != 'KIA':
                continue
            try:
                pitchers[name] = {
                    "era": cols[3].get_text(strip=True),
                    "g": cols[4].get_text(strip=True),
                    "w": cols[5].get_text(strip=True),
                    "l": cols[6].get_text(strip=True),
                    "sv": cols[7].get_text(strip=True),
                    "ip": cols[10].get_text(strip=True) if len(cols) > 10 else '0.0',
                    "h": cols[11].get_text(strip=True) if len(cols) > 11 else '0',
                    "bb": cols[13].get_text(strip=True) if len(cols) > 13 else '0',
                    "k": cols[15].get_text(strip=True) if len(cols) > 15 else '0',
                    "whip": cols[18].get_text(strip=True) if len(cols) > 18 else '-',
                }
            except:
                continue
        print(f"KIA 투수: {len(pitchers)}명 수집 - {list(pitchers.keys())[:5]}")
        return pitchers
    except Exception as e:
        print(f"pitcher error: {e}")
        return {}

def make_hitter_entry(name, data):
    num = PLAYER_NUM.get(name, '-')
    pos = PLAYER_POS.get(name, '-')
    avg = data.get('avg', '-')
    if avg and avg != '-':
        try:
            avg = f".{int(float(avg)*1000):03d}"
        except:
            pass
    return {
        "name": name, "num": num, "pos": pos,
        "avg": avg,
        "hr": int(data.get('hr', 0) or 0),
        "rbi": int(data.get('rbi', 0) or 0),
        "r": int(data.get('r', 0) or 0),
        "h": int(data.get('h', 0) or 0),
        "ab": int(data.get('ab', 0) or 0),
        "bb": int(data.get('bb', 0) or 0),
        "so": int(data.get('so', 0) or 0),
        "obp": data.get('obp', '-'),
        "slg": data.get('slg', '-'),
        "ops": data.get('ops', '-')
    }

def make_pitcher_entry(name, data):
    num = PLAYER_NUM.get(name, '-')
    era = data.get('era', '-')
    w = int(data.get('w', 0) or 0)
    l = int(data.get('l', 0) or 0)
    sv = int(data.get('sv', 0) or 0)
    return {
        "name": name, "num": num, "pos": "선발" if name in ['네일','올러','양현종','이의리','김태형'] else "불펜",
        "era": era, "w": w, "l": l, "sv": sv,
        "ip": data.get('ip', '0.0'),
        "h": int(data.get('h', 0) or 0),
        "bb": int(data.get('bb', 0) or 0),
        "k": int(data.get('k', 0) or 0),
        "whip": data.get('whip', '-'), "qs": 0
    }

def build_html(standings, games, hitters, pitchers):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now()
    today = now.strftime("%Y.%m.%d")

    # standings 교체
    if standings:
        s_json = json.dumps(standings, ensure_ascii=False)
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,800}?standings:\s*)\[[\s\S]*?\],',
            r'\g<1>' + s_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ standings 교체 ({len(standings)}팀)")

    # recentGames 교체
    if games:
        recent = games[-10:]
        g_json = json.dumps(recent, ensure_ascii=False)
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,200}?recentGames:\s*)\[[\s\S]*?\],',
            r'\g<1>' + g_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ recentGames 교체 ({len(recent)}경기)")

    # kiaHitters 교체
    if hitters:
        main_h = []
        for name in MAIN_HITTERS:
            if name in hitters:
                main_h.append(make_hitter_entry(name, hitters[name]))
            else:
                main_h.append({"name": name, "num": PLAYER_NUM.get(name,'-'), "pos": PLAYER_POS.get(name,'-'), "avg": '-', "hr": 0, "rbi": 0, "r": 0, "h": 0, "ab": 0, "bb": 0, "so": 0, "obp": '-', "slg": '-', "ops": '-'})

        fav_h = []
        for name in FAV_HITTERS:
            if name in hitters:
                fav_h.append(make_hitter_entry(name, hitters[name]))
            else:
                fav_h.append({"name": name, "num": PLAYER_NUM.get(name,'-'), "pos": PLAYER_POS.get(name,'-'), "avg": '-', "hr": 0, "rbi": 0, "r": 0, "h": 0, "ab": 0, "bb": 0, "so": 0, "obp": '-', "slg": '-', "ops": '-'})

        mh_json = json.dumps(main_h, ensure_ascii=False)
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,2000}?kiaHitters:\s*)\[[\s\S]*?\],',
            r'\g<1>' + mh_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ kiaHitters 교체 ({len(main_h)}명)")

        fh_json = json.dumps(fav_h, ensure_ascii=False)
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,3000}?kiaFavHitters:\s*)\[[\s\S]*?\],',
            r'\g<1>' + fh_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ kiaFavHitters 교체 ({len(fav_h)}명)")

    # kiaPitchers 교체
    if pitchers:
        main_p = []
        for name in MAIN_PITCHERS:
            if name in pitchers:
                main_p.append(make_pitcher_entry(name, pitchers[name]))
            else:
                main_p.append({"name": name, "num": PLAYER_NUM.get(name,'-'), "pos": "선발", "era": '-', "w": 0, "l": 0, "sv": 0, "ip": '0.0', "h": 0, "bb": 0, "k": 0, "whip": '-', "qs": 0})

        fav_p = []
        for name in FAV_PITCHERS:
            if name in pitchers:
                fav_p.append(make_pitcher_entry(name, pitchers[name]))
            else:
                fav_p.append({"name": name, "num": PLAYER_NUM.get(name,'-'), "pos": "불펜", "era": '-', "w": 0, "l": 0, "sv": 0, "ip": '0.0', "h": 0, "bb": 0, "k": 0, "whip": '-', "qs": 0})

        mp_json = json.dumps(main_p, ensure_ascii=False)
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,2000}?kiaPitchers:\s*)\[[\s\S]*?\],',
            r'\g<1>' + mp_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ kiaPitchers 교체 ({len(main_p)}명)")

        fp_json = json.dumps(fav_p, ensure_ascii=False)
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,4000}?kiaFavPitchers:\s*)\[[\s\S]*?\],',
            r'\g<1>' + fp_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ kiaFavPitchers 교체 ({len(fav_p)}명)")

    html = re.sub(r'2026 KBO 리그 · .*? 기준', f'2026 KBO 리그 · {today} 기준', html)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html 업데이트 완료 ({today})")

if __name__ == "__main__":
    print("📡 KBO 데이터 수집 중...")
    standings = get_standings()
    games = get_kia_schedule()
    hitters = get_kia_hitters()
    pitchers = get_kia_pitchers()

    print(f"\n[순위] {len(standings)}팀")
    for s in standings:
        print(f"  {s['rank']}위 {s['team']} {s['w']}승 {s['l']}패")

    print(f"\n[KIA 경기] {len(games)}경기")
    for g in games[-3:]:
        print(f"  {g['date']} {g['opp']} {g['score']} ({g['result']})")

    print(f"\n[KIA 타자] {len(hitters)}명")
    for n, d in list(hitters.items())[:5]:
        print(f"  {n} {d['avg']}")

    print(f"\n[KIA 투수] {len(pitchers)}명")
    for n, d in list(pitchers.items())[:5]:
        print(f"  {n} ERA {d['era']}")

    build_html(standings, games, hitters, pitchers)
