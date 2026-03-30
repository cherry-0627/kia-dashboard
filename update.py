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

def get_standings():
    url = "https://eng.koreabaseball.com/Standings/TeamStandings.aspx"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            print("순위 테이블 없음")
            return []
        rows = table.select("tbody tr") or table.select("tr")[1:]
        standings = []
        for row in rows[:10]:
            cols = row.select("td")
            if len(cols) < 5:
                continue
            try:
                rank = int(cols[0].get_text(strip=True))
            except:
                continue
            team_eng = cols[1].get_text(strip=True).upper()
            team_kor = TEAM_ENG_KOR.get(team_eng, team_eng)
            is_kia = team_eng == 'KIA'
            standings.append({
                "rank": rank,
                "team": team_kor,
                "g": cols[2].get_text(strip=True),
                "w": cols[3].get_text(strip=True),
                "l": cols[4].get_text(strip=True),
                "pct": cols[5].get_text(strip=True) if len(cols) > 5 else '-',
                "gb": cols[6].get_text(strip=True) if len(cols) > 6 else '-',
                "kia": is_kia
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
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table:
            print("일정 테이블 없음")
            return []

        rows = table.select("tr")
        games = []
        current_date = ""

        for row in rows:
            cols = row.select("td")
            if not cols:
                continue
            first = cols[0].get_text(strip=True)
            if re.match(r'\d{2}\.\d{2}', first):
                current_date = first

            row_text = ' '.join([c.get_text(strip=True) for c in cols])
            if 'KIA' not in row_text:
                continue

            # 스코어 파싱
            for i, col in enumerate(cols):
                txt = col.get_text(strip=True)
                score_m = re.match(r'^(\d+):(\d+)$', txt)
                if not score_m:
                    continue
                away = cols[i-1].get_text(strip=True).upper() if i > 0 else ''
                home = cols[i+1].get_text(strip=True).upper() if i+1 < len(cols) else ''
                if 'KIA' not in away and 'KIA' not in home:
                    continue
                away_score = int(score_m.group(1))
                home_score = int(score_m.group(2))
                if 'KIA' in away:
                    kia_s, opp_s = away_score, home_score
                    opp_eng = home
                    venue = '원정'
                else:
                    kia_s, opp_s = home_score, away_score
                    opp_eng = away
                    venue = '홈'
                opp_kor = TEAM_ENG_KOR.get(opp_eng, opp_eng)
                opp_short = opp_kor.split(' ')[0]
                if kia_s > opp_s:
                    result = 'win'
                elif kia_s < opp_s:
                    result = 'lose'
                else:
                    result = 'draw'
                if current_date:
                    games.append({
                        "date": current_date,
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
    is_regular = now >= datetime(2026, 3, 28)
    season_key = 'regular' if is_regular else 'preseason'

    if standings:
        s_json = json.dumps(standings, ensure_ascii=False)
        pattern = rf"('{season_key}'[\s\S]{{0,500}}?standings:\s*)\[[\s\S]*?\],"
        new_html = re.sub(pattern, r'\g<1>' + s_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ standings 교체 성공 ({len(standings)}팀)")
        else:
            print(f"⚠️ standings 패턴 실패")

    if games:
        recent = games[-10:]
        g_json = json.dumps(recent, ensure_ascii=False)
        pattern = rf"('{season_key}'[\s\S]{{0,200}}?recentGames:\s*)\[[\s\S]*?\],"
        new_html = re.sub(pattern, r'\g<1>' + g_json + ',', html, count=1)
        if new_html != html:
            html = new_html
            print(f"✅ recentGames 교체 성공 ({len(recent)}경기)")

    today = now.strftime("%Y.%m.%d")
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
    for g in games[-5:]:
        print(f"  {g['date']} {g['opp']} {g['score']} ({g['result']}) {g['venue']}")

    build_html(standings, games)
