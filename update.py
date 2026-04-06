import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta

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
VENUE_MAP = {
    'GWANGJU': '광주', 'JAMSIL': '잠실', 'MUNHAK': '문학', 'DAEJEON': '대전',
    'DAEGU': '대구', 'SAJIK': '사직', 'CHANGWON': '창원', 'SUWON': '수원',
    'ICHEON': '이천', 'GOCHEOK': '고척'
}
DAY_MAP = {'MON':'월','TUE':'화','WED':'수','THU':'목','FRI':'금','SAT':'토','SUN':'일'}
VALID_TEAMS = set(TEAM_ENG_KOR.keys())

PLAYER_NUM = {
    '카스트로':'53','김선빈':'3','나성범':'22','데일':'58','김도영':'5',
    '박민':'2','오선우':'56','박재현':'15','네일':'47','올러':'49',
    '양현종':'11','이의리':'35','김태형':'17','최지민':'39','조상우':'1',
    '김호령':'18','윤도현':'99','한준수':'27'
}
PLAYER_POS_MAP = {
    '카스트로':'지명타자','김선빈':'2루수','나성범':'우익수','데일':'유격수',
    '김도영':'유격수','박민':'3루수','오선우':'1루수','박재현':'외야수',
    '김호령':'중견수','윤도현':'내야수','한준수':'포수'
}
MAIN_HITTERS  = ['카스트로','나성범','김선빈','김도영','데일','박민']
FAV_HITTERS   = ['오선우','박재현']
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
    """KIA 경기 결과 + 다음 예정 경기 파싱"""
    url = "https://eng.koreabaseball.com/Schedule/DailySchedule.aspx"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            return [], None

        rows = table.select("tr")
        games = []
        next_game = None
        current_date_raw = ""
        now = datetime.now()

        for row in rows:
            cols = row.select("td")
            if not cols:
                continue

            first = cols[0].get_text(strip=True)
            if re.match(r'\d{2}\.\d{2}\(\w+\)', first):
                current_date_raw = first

            col_texts = [c.get_text(strip=True).upper() for c in cols]
            col_orig   = [c.get_text(strip=True) for c in cols]

            if 'KIA' not in col_texts:
                continue

            # 날짜 파싱
            date_m = re.match(r'(\d{2})\.(\d{2})\((\w+)\)', current_date_raw)
            if not date_m:
                continue
            month, day, day_eng = int(date_m.group(1)), int(date_m.group(2)), date_m.group(3)
            day_kor = DAY_MAP.get(day_eng, '')
            date_str = f"{current_date_raw[:5]}({day_kor})"
            game_date = datetime(now.year, month, day)

            # 시간 찾기 (HH:MM 형태)
            time_str = ""
            for txt in col_orig:
                if re.match(r'^\d{2}:\d{2}$', txt):
                    time_str = txt
                    break

            # 스코어 파싱
            score_found = False
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
                    kia_s, opp_s, opp_eng, venue_type = away_score, home_score, home, '원정'
                else:
                    kia_s, opp_s, opp_eng, venue_type = home_score, away_score, away, '홈'

                opp_kor   = TEAM_ENG_KOR.get(opp_eng, opp_eng)
                opp_short = opp_kor.split(' ')[0]
                result    = 'win' if kia_s > opp_s else ('lose' if kia_s < opp_s else 'draw')

                games.append({
                    "date": date_str, "opp": f"vs {opp_short}",
                    "score": f"{kia_s}-{opp_s}", "result": result, "venue": venue_type
                })
                score_found = True
                break

            # 예정 경기 파싱 (스코어 없고 시간만 있는 경우)
            if not score_found and time_str and game_date >= now.replace(hour=0, minute=0, second=0):
                for i, txt in enumerate(col_texts):
                    if txt == time_str.upper():
                        continue
                    if i > 0 and i < len(col_texts) - 1:
                        away, home = col_texts[i-1], col_texts[i+1]
                        # 시간 컬럼 찾기
                for i, orig in enumerate(col_orig):
                    if re.match(r'^\d{2}:\d{2}$', orig) and i > 0 and i < len(col_orig) - 1:
                        away = col_texts[i-1]
                        home = col_texts[i+1]
                        if away not in VALID_TEAMS or home not in VALID_TEAMS:
                            continue
                        if 'KIA' not in away and 'KIA' not in home:
                            continue

                        if 'KIA' in away:
                            opp_eng, venue_type = home, '원정'
                        else:
                            opp_eng, venue_type = away, '홈'

                        opp_kor   = TEAM_ENG_KOR.get(opp_eng, opp_eng)
                        opp_short = opp_kor.split(' ')[0]

                        # 구장 찾기
                        venue_name = venue_type
                        for ct in col_orig:
                            v = VENUE_MAP.get(ct.upper(), '')
                            if v:
                                venue_name = v
                                break

                        # 날짜시간 조합
                        h, m = map(int, orig.split(':'))
                        full_dt = datetime(now.year, month, day, h, m)
                        full_dt_str = full_dt.strftime('%Y-%m-%dT%H:%M:%S')

                        # 가장 가까운 미래 경기를 nextGame으로
                        if next_game is None and full_dt >= now:
                            next_game = {
                                "date": full_dt_str,
                                "opponent": opp_kor,
                                "venue": venue_name,
                                "home": venue_type == '홈'
                            }

                        games.append({
                            "date": date_str, "opp": f"vs {opp_short}",
                            "score": orig, "result": "upcoming",
                            "venue": venue_name, "fullDate": full_dt_str
                        })
                        break

        print(f"KIA 경기: {len(games)}경기")
        if next_game:
            print(f"다음 경기: {next_game['date']} vs {next_game['opponent']} ({next_game['venue']})")
        return games, next_game

    except Exception as e:
        print(f"schedule error: {e}")
        return [], None

def scrape_kia_hitters():
    base_url = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx"
    kia = {}
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            return kia
        for row in table.select("tbody tr") or table.select("tr")[1:]:
            cols = row.select("td")
            if len(cols) < 9 or cols[2].get_text(strip=True) != 'KIA':
                continue
            name = cols[1].get_text(strip=True)
            try:
                avg_raw = cols[3].get_text(strip=True)
                avg = f".{int(float(avg_raw)*1000):03d}" if avg_raw and avg_raw not in ['-',''] else '-'
            except:
                avg = '-'
            kia[name] = {
                "avg": avg,
                "h":   int(cols[8].get_text(strip=True) or 0),
                "ab":  int(cols[6].get_text(strip=True) or 0),
                "r":   int(cols[7].get_text(strip=True) or 0),
                "hr":  int(cols[11].get_text(strip=True) or 0) if len(cols) > 11 else 0,
                "rbi": int(cols[13].get_text(strip=True) or 0) if len(cols) > 13 else 0,
            }
    except Exception as e:
        print(f"hitter error: {e}")
    print(f"KIA 타자: {len(kia)}명 - {list(kia.keys())}")
    return kia

def scrape_kia_pitchers():
    base_url = "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx"
    kia = {}
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            return kia
        for row in table.select("tbody tr") or table.select("tr")[1:]:
            cols = row.select("td")
            if len(cols) < 10 or cols[2].get_text(strip=True) != 'KIA':
                continue
            name = cols[1].get_text(strip=True)
            kia[name] = {
                "era":  cols[3].get_text(strip=True),
                "w":    int(cols[5].get_text(strip=True) or 0),
                "l":    int(cols[6].get_text(strip=True) or 0),
                "sv":   int(cols[7].get_text(strip=True) or 0),
                "ip":   cols[10].get_text(strip=True) if len(cols) > 10 else '0.0',
                "h":    int(cols[11].get_text(strip=True) or 0) if len(cols) > 11 else 0,
                "bb":   int(cols[13].get_text(strip=True) or 0) if len(cols) > 13 else 0,
                "k":    int(cols[15].get_text(strip=True) or 0) if len(cols) > 15 else 0,
                "whip": cols[18].get_text(strip=True) if len(cols) > 18 else '-',
            }
    except Exception as e:
        print(f"pitcher error: {e}")
    print(f"KIA 투수: {len(kia)}명 - {list(kia.keys())}")
    return kia

def mh(name, d):
    return {"name":name,"num":PLAYER_NUM.get(name,'-'),"pos":PLAYER_POS_MAP.get(name,'-'),
            "avg":d.get("avg",'-'),"hr":d.get("hr",0),"rbi":d.get("rbi",0),
            "r":d.get("r",0),"h":d.get("h",0),"ab":d.get("ab",0),
            "bb":0,"so":0,"obp":'-',"slg":'-',"ops":'-'}

def me(name):
    return {"name":name,"num":PLAYER_NUM.get(name,'-'),"pos":PLAYER_POS_MAP.get(name,'-'),
            "avg":'-',"hr":0,"rbi":0,"r":0,"h":0,"ab":0,"bb":0,"so":0,"obp":'-',"slg":'-',"ops":'-'}

def mp(name, d):
    pos = "불펜" if name in FAV_PITCHERS else "선발"
    return {"name":name,"num":PLAYER_NUM.get(name,'-'),"pos":pos,
            "era":d.get("era",'-'),"w":d.get("w",0),"l":d.get("l",0),
            "sv":d.get("sv",0),"ip":d.get("ip",'0.0'),
            "h":d.get("h",0),"bb":d.get("bb",0),"k":d.get("k",0),
            "whip":d.get("whip",'-'),"qs":0}

def mpe(name):
    pos = "불펜" if name in FAV_PITCHERS else "선발"
    return {"name":name,"num":PLAYER_NUM.get(name,'-'),"pos":pos,
            "era":'-',"w":0,"l":0,"sv":0,"ip":'0.0',"h":0,"bb":0,"k":0,"whip":'-',"qs":0}

def replace_block(html, pattern, data, label):
    j = json.dumps(data, ensure_ascii=False)
    new = re.sub(pattern, r'\g<1>' + j + ',', html, count=1)
    if new != html:
        print(f"✅ {label} 교체")
        return new
    print(f"⚠️ {label} 패턴 실패")
    return html

def build_html(standings, games, next_game, hitters, pitchers):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now()
    today = now.strftime("%Y.%m.%d")

    if standings:
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,800}?standings:\s*)\[[\s\S]*?\],',
            standings, f"standings({len(standings)}팀)")

    if games:
        # 완료 경기만 최근 10개
        done = [g for g in games if g['result'] != 'upcoming'][-10:]
        # 예정 경기 최대 3개
        upcoming = [g for g in games if g['result'] == 'upcoming'][:3]
        recent = done + upcoming
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,200}?recentGames:\s*)\[[\s\S]*?\],',
            recent, f"recentGames({len(recent)}경기)")

    if next_game:
        ng_json = json.dumps(next_game, ensure_ascii=False)
        new = re.sub(
            r'(regular:\s*\{[\s\S]{0,150}?nextGame:\s*)\{[^\}]*\},',
            r'\g<1>' + ng_json + ',', html, count=1)
        if new != html:
            html = new
            print(f"✅ nextGame 교체 ({next_game['opponent']})")
        else:
            print(f"⚠️ nextGame 패턴 실패")

    if hitters:
        main_h = [mh(n, hitters[n]) if n in hitters else me(n) for n in MAIN_HITTERS]
        fav_h  = [mh(n, hitters[n]) if n in hitters else me(n) for n in FAV_HITTERS]
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,2500}?kiaHitters:\s*)\[[\s\S]*?\],',
            main_h, f"kiaHitters({len(main_h)}명)")
        html = replace_block(html,
            r'(regular:\s*\{[\s\S]{0,3500}?kiaFavHitters:\s*)\[[\s\S]*?\],',
            fav_h, f"kiaFavHitters({len(fav_h)}명)")

    if pitchers:
        main_p = [mp(n, pitchers[n]) if n in pitchers else mpe(n) for n in MAIN_PITCHERS]
        fav_p  = [mp(n, pitchers[n]) if n in pitchers else mpe(n) for n in FAV_PITCHERS]
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
    standings          = get_standings()
    games, next_game   = get_kia_schedule()
    hitters            = scrape_kia_hitters()
    pitchers           = scrape_kia_pitchers()
    build_html(standings, games, next_game, hitters, pitchers)
