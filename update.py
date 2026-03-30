import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

TEAM_ENG_KOR = {
    'KIA': 'KIA 타이거즈', 'LG': 'LG 트윈스', 'SAMSUNG': '삼성 라이온즈',
    'HANWHA': '한화 이글스', 'SSG': 'SSG 랜더스', 'NC': 'NC 다이노스',
    'KT': 'KT 위즈', 'LOTTE': '롯데 자이언츠', 'DOOSAN': '두산 베어스',
    'KIWOOM': '키움 히어로즈'
}
DAY_MAP = {'MON':'월','TUE':'화','WED':'수','THU':'목','FRI':'금','SAT':'토','SUN':'일'}
VALID_TEAMS = set(TEAM_ENG_KOR.keys())

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
                "rank": rank,
                "team": team_kor,
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
                if not score_m:
                    continue
                if i == 0 or i >= len(col_texts) - 1:
                    continue

                away = col_texts[i-1]
                home = col_texts[i+1]

                # 유효한 팀명만 허용 (REGULAR 등 오염 방지)
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

                games.append({
                    "date": date_str,
                    "opp": f"vs {opp_short}",
                    "score": f"{kia_s}-{opp_s}",
                    "result": result,
                    "venue": venue
                })
                break

        print(f"KIA 경기: {len(games)}경기 수집")
        return games
    except Exception as e:
        print(f"schedule error: {e}")
        return []

def build_html(standings, games):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now()
    today = now.strftime("%Y.%m.%d")

    if standings:
        s_json = json.dumps(standings, ensure_ascii=False)
        # regular: { ... standings: [...], 패턴
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,500}?standings:\s*)\[[\s\S]*?\],',
            r'\g<1>' + s_json + ',',
            html, count=1
        )
        if new_html != html:
            html = new_html
            print(f"✅ standings 교체 성공 ({len(standings)}팀)")
        else:
            print(f"⚠️ standings 패턴 실패")

    if games:
        recent = games[-10:]
        g_json = json.dumps(recent, ensure_ascii=False)
        new_html = re.sub(
            r'(regular:\s*\{[\s\S]{0,100}?recentGames:\s*)\[[\s\S]*?\],',
            r'\g<1>' + g_json + ',',
            html, count=1
        )
        if new_html != html:
            html = new_html
            print(f"✅ recentGames 교체 성공 ({len(recent)}경기)")
        else:
            print(f"⚠️ recentGames 패턴 실패")

    html = re.sub(r'2026 KBO 리그 · .*? 기준', f'2026 KBO 리그 · {today} 기준', html)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html 업데이트 완료 ({today})")

if __name__ == "__main__":
    print("📡 KBO 영문 사이트에서 데이터 수집 중...")
    standings = get_standings()
    games = get_kia_schedule()

    print(f"\n[순위] {len(standings)}팀")
    for s in standings:
        print(f"  {s['rank']}위 {s['team']} {s['w']}승 {s['l']}패 {s['pct']}")

    print(f"\n[KIA 경기] {len(games)}경기")
    for g in games:
        print(f"  {g['date']} {g['opp']} {g['score']} ({g['result']}) {g['venue']}")

    build_html(standings, games)
