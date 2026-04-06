import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.koreabaseball.com/"
}

TEAM_ENG_KOR = {
    'KIA': 'KIA 타이거즈', 'LG': 'LG 트윈스', 'SAMSUNG': '삼성 라이온즈',
    'HANWHA': '한화 이글스', 'SSG': 'SSG 랜더스', 'NC': 'NC 다이노스',
    'KT': 'KT 위즈', 'LOTTE': '롯데 자이언츠', 'DOOSAN': '두산 베어스',
    'KIWOOM': '키움 히어로즈'
}
DAY_MAP = {'MON':'월','TUE':'화','WED':'수','THU':'목','FRI':'금','SAT':'토','SUN':'일'}
VALID_TEAMS = set(TEAM_ENG_KOR.keys())

PLAYER_NUM = {
    '카스트로':'53','김선빈':'3','나성범':'22','데일':'58','김도영':'5',
    '박민':'2','오선우':'56','박재현':'15','네일':'47','올러':'49',
    '양현종':'11','이의리':'35','김태형':'17','최지민':'39','조상우':'1',
    '이의리':'35','김호령':'18','윤도현':'99','한준수':'27'
}
PLAYER_POS_MAP = {
    '카스트로':'지명타자','김선빈':'2루수','나성범':'우익수','데일':'유격수',
    '김도영':'유격수','박민':'3루수','오선우':'1루수','박재현':'외야수',
    '김호령':'중견수','윤도현':'내야수','한준수':'포수'
}
MAIN_HITTERS = ['카스트로','나성범','김선빈','김도영','데일','박민']
FAV_HITTERS  = ['오선우','박재현']
MAIN_PITCHERS = ['네일','올러','양현종','이의리','김태형']
FAV_PITCHERS  = ['최지민']

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
            standings.append({
                "rank": rank,
                "team": TEAM_ENG_KOR.get(team_eng, team_eng),
                "g": cols[2].get_text(strip=True),
                "w": cols[3].get_text(strip=True),
                "l": cols[4].get_text(strip=True),
                "pct": cols[6].get_text(strip=True),
                "gb": cols[7].get_text(strip=True),
                "kia": team_eng == 'KIA'
            })
        print(f"순위: {len(standings)}팀")
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
                away, home = col_texts[i-1], col_texts[i+1]
                if away not in VALID_TEAMS or home not in VALID_TEAMS:
                    continue
                if 'KIA' not in away and 'KIA' not in home:
                    continue
                away_score, home_score = int(score_m.group(1)), int(score_m.group(2))
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
        print(f"KIA 경기: {len(games)}경기")
        return games
    except Exception as e:
        print(f"schedule error: {e}")
        return []

def scrape_kia_hitters():
    """전체 타자 목록에서 KIA 선수만 추출 (여러 페이지 순회)"""
    base_url = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx"
    kia_hitters = {}
    
    # 최대 3페이지까지 순회
    for page in range(1, 4):
        try:
            if page == 1:
                res = requests.get(base_url, headers=HEADERS, timeout=15)
            else:
                # 페이지 이동은 __doPostBack 방식 - viewstate 필요
                # 대신 sort 파라미터로 접근 시도
                break
            
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.select_one("table")
            if not table:
                break
            rows = table.select("tbody tr") or table.select("tr")[1:]
            found_kia = False
            for row in rows:
                cols = row.select("td")
                if len(cols) < 9:
                    continue
                team = cols[2].get_text(strip=True)
                if team != 'KIA':
                    continue
                found_kia = True
                name = cols[1].get_text(strip=True)
                try:
                    avg_raw = cols[3].get_text(strip=True)
                    avg = f".{int(float(avg_raw)*1000):03d}" if avg_raw and avg_raw != '-' else '-'
                except:
                    avg = '-'
                kia_hitters[name] = {
                    "avg": avg,
                    "g": int(cols[4].get_text(strip=True) or 0),
                    "ab": int(cols[6].get_text(strip=True) or 0),
                    "r": int(cols[7].get_text(strip=True) or 0),
                    "h": int(cols[8].get_text(strip=True) or 0),
                    "hr": int(cols[11].get_text(strip=True) or 0) if len(cols) > 11 else 0,
                    "rbi": int(cols[13].get_text(strip=True) or 0) if len(cols) > 13 else 0,
                    "bb": 0, "so": 0, "obp": '-', "slg": '-', "ops": '-'
                }
            if not found_kia:
                break
        except Exception as e:
            print(f"hitter page {page} error: {e}")
            break
    
    print(f"KIA 타자: {len(kia_hitters)}명 - {list(kia_hitters.keys())}")
    return kia_hitters

def scrape_kia_pitchers():
    """전체 투수 목록에서 KIA 선수만 추출"""
    base_url = "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx"
    kia_pitchers = {}
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            return {}
        rows = table.select("tbody tr") or table.select("tr")[1:]
        for row in rows:
            cols = row.select("td")
            if len(cols) < 10:
                continue
            team = cols[2].get_text(strip=True)
            if team != 'KIA':
                continue
            name = cols[1].get_text(strip=True)
            kia_pitchers[name] = {
                "era": cols[3].get_text(strip=True),
                "g": int(cols[4].get_text(strip=True) or 0),
                "w": int(cols[5].get_text(strip=True) or 0),
                "l": int(cols[6].get_text(strip=True) or 0),
                "sv": int(cols[7].get_text(strip=True) or 0),
                "ip": cols[10].get_text(strip=True) if len(cols) > 10 else '0.0',
                "h": int(cols[11].get_text(strip=True) or 0) if len(cols) > 11 else 0,
                "bb": int(cols[13].get_text(strip=True) or 0) if len(cols) > 13 else 0,
                "k": int(cols[15].get_text(strip=True) or 0) if len(cols) > 15 else 0,
                "whip": cols[18].get_text(strip=True) if len(cols) > 18 else '-',
            }
    except Exception as e:
        print(f"pitcher error: {e}")
    print(f"KIA 투수: {len(kia_pitchers)}명 - {list(kia_pitchers.keys())}")
    return kia_pitchers

def make_hitter(name, d):
    return {
        "name": name, "num": PLAYER_NUM.get(name, '-'),
        "pos": PLAYER_POS_MAP.get(name, '-'),
        "avg": d.get("avg", '-'), "hr": d.get("hr", 0),
        "rbi": d.get("rbi", 0), "r": d.get("r", 0),
        "h": d.get("h", 0), "ab": d.get("ab", 0),
        "bb": 0, "so": 0, "obp": '-', "slg": '-', "ops": '-'
    }

def make_hitter_empty(name):
    return {"name": name, "num": PLAYER_NUM.get(name, '-'), "pos": PLAYER_POS_MAP.get(name, '-'),
            "avg": '-', "hr": 0, "rbi": 0, "r": 0, "h": 0, "ab": 0, "bb": 0, "so": 0, "obp": '-', "slg": '-', "ops": '-'}

def make_pitcher(name, d):
    pos = "불펜" if name in FAV_PITCHERS else "선발"
    return {
        "name": name, "num": PLAYER_NUM.get(name, '-'), "pos": pos,
        "era": d.get("era", '-'), "w": d.get("w", 0), "l": d.get("l", 0),
        "sv": d.get("sv", 0), "ip": d.get("ip", '0.0'),
        "h": d.get("h", 0), "bb": d.get("bb", 0), "k": d.get("k", 0),
        "whip": d.get("whip", '-'), "qs": 0
    }

def make_pitcher_empty(name):
    pos = "불펜" if name in FAV_PITCHERS else "선발"
    return {"name": name, "num": PLAYER_NUM.get(name, '-'), "pos": pos,
            "era": '-', "w": 0, "l": 0, "sv": 0, "ip": '0.0',
            "h": 0, "bb": 0, "k": 0, "whip": '-', "qs": 0}

def build_html(standings, games, hitters, pitchers):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now()
    today = now.strftime("%Y.%m.%d")

    def replace_block(html, pattern, data, label):
        j = json.dumps(data, ensure_ascii=False)
        new = re.sub(pattern, r'\g<1>' + j + ',', html, count=1)
        if new != html:
            print(f"✅ {label} 교체")
            return new
        print(f"⚠️ {label} 패턴 실패")
        return html

    if standings:
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,800}?standings:\s*)\[[\s\S]*?\],',
            standings, f"standings({len(standings)}팀)")

    if games:
        recent = games[-10:]
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,200}?recentGames:\s*)\[[\s\S]*?\],',
            recent, f"recentGames({len(recent)}경기)")

    if hitters:
        main_h = [make_hitter(n, hitters[n]) if n in hitters else make_hitter_empty(n) for n in MAIN_HITTERS]
        fav_h  = [make_hitter(n, hitters[n]) if n in hitters else make_hitter_empty(n) for n in FAV_HITTERS]
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,2500}?kiaHitters:\s*)\[[\s\S]*?\],',
            main_h, f"kiaHitters({len(main_h)}명)")
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,3500}?kiaFavHitters:\s*)\[[\s\S]*?\],',
            fav_h, f"kiaFavHitters({len(fav_h)}명)")

    if pitchers:
        main_p = [make_pitcher(n, pitchers[n]) if n in pitchers else make_pitcher_empty(n) for n in MAIN_PITCHERS]
        fav_p  = [make_pitcher(n, pitchers[n]) if n in pitchers else make_pitcher_empty(n) for n in FAV_PITCHERS]
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,2500}?kiaPitchers:\s*)\[[\s\S]*?\],',
            main_p, f"kiaPitchers({len(main_p)}명)")
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,4500}?kiaFavPitchers:\s*)\[[\s\S]*?\],',
            fav_p, f"kiaFavPitchers({len(fav_p)}명)")

    html = re.sub(r'2026 KBO 리그 · .*? 기준', f'2026 KBO 리그 · {today} 기준', html)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html 완료 ({today})")

if __name__ == "__main__":
    print("📡 KBO 데이터 수집 중...")
    standings = get_standings()
    games     = get_kia_schedule()
    hitters   = scrape_kia_hitters()
    pitchers  = scrape_kia_pitchers()
    build_html(standings, games, hitters, pitchers)
