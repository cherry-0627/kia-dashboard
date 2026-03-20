import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://sports.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9"
}

def get_standings():
    url = "https://sports.naver.com/kbaseball/standings/team"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tbody tr")
        standings = []
        for i, row in enumerate(rows[:10]):
            cols = row.select("td")
            if len(cols) < 6:
                continue
            team = cols[1].get_text(strip=True)
            is_kia = "KIA" in team or "기아" in team
            standings.append({
                "rank": i + 1,
                "team": team,
                "g": cols[2].get_text(strip=True),
                "w": cols[3].get_text(strip=True),
                "l": cols[4].get_text(strip=True),
                "pct": cols[5].get_text(strip=True),
                "gb": cols[6].get_text(strip=True) if len(cols) > 6 else "-",
                "kia": is_kia
            })
        return standings
    except Exception as e:
        print(f"standings error: {e}")
        return []

def get_schedule():
    url = "https://sports.naver.com/kbaseball/schedule/index"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        games = []
        rows = soup.select(".tb_wrap tbody tr")
        for row in rows:
            text = row.get_text()
            if "KIA" in text or "기아" in text:
                cols = row.select("td")
                if len(cols) >= 4:
                    games.append({
                        "date": cols[0].get_text(strip=True),
                        "opp": cols[1].get_text(strip=True),
                        "score": cols[2].get_text(strip=True),
                        "result": "win" if "승" in text else "lose" if "패" in text else "upcoming",
                        "venue": cols[3].get_text(strip=True) if len(cols) > 3 else ""
                    })
        return games[:5]
    except Exception as e:
        print(f"schedule error: {e}")
        return []

def get_batters():
    url = "https://sports.naver.com/kbaseball/record/batter"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tbody tr")
        batters = []
        for i, row in enumerate(rows[:10]):
            cols = row.select("td")
            if len(cols) < 6:
                continue
            team = cols[2].get_text(strip=True)
            is_kia = "KIA" in team or "기아" in team
            batters.append({
                "rank": i + 1,
                "name": cols[1].get_text(strip=True),
                "team": team,
                "avg": cols[3].get_text(strip=True),
                "h": cols[4].get_text(strip=True),
                "hr": cols[5].get_text(strip=True),
                "rbi": cols[6].get_text(strip=True) if len(cols) > 6 else "0",
                "kia": is_kia
            })
        return batters
    except Exception as e:
        print(f"batters error: {e}")
        return []

def get_pitchers():
    url = "https://sports.naver.com/kbaseball/record/pitcher"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tbody tr")
        pitchers = []
        for i, row in enumerate(rows[:10]):
            cols = row.select("td")
            if len(cols) < 6:
                continue
            team = cols[2].get_text(strip=True)
            is_kia = "KIA" in team or "기아" in team
            pitchers.append({
                "rank": i + 1,
                "name": cols[1].get_text(strip=True),
                "team": team,
                "era": cols[3].get_text(strip=True),
                "ip": cols[4].get_text(strip=True),
                "k": cols[5].get_text(strip=True),
                "wl": cols[6].get_text(strip=True) if len(cols) > 6 else "-",
                "kia": is_kia
            })
        return pitchers
    except Exception as e:
        print(f"pitchers error: {e}")
        return []

def build_html(standings, schedule, batters, pitchers):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # standings JSON 교체
    if standings:
        s_json = json.dumps(standings, ensure_ascii=False)
        html = re.sub(r'standings:\s*\[.*?\],', f'standings: {s_json},', html, flags=re.DOTALL)

    # schedule JSON 교체
    if schedule:
        sc_json = json.dumps(schedule, ensure_ascii=False)
        html = re.sub(r'recentGames:\s*\[.*?\],', f'recentGames: {sc_json},', html, flags=re.DOTALL)

    # batters JSON 교체
    if batters:
        b_json = json.dumps(batters, ensure_ascii=False)
        html = re.sub(r'batters:\s*\[.*?\],', f'batters: {b_json},', html, flags=re.DOTALL)

    # pitchers JSON 교체
    if pitchers:
        p_json = json.dumps(pitchers, ensure_ascii=False)
        html = re.sub(r'pitchers:\s*\[.*?\],', f'pitchers: {p_json},', html, flags=re.DOTALL)

    # 날짜 업데이트
    today = datetime.now().strftime("%Y.%m.%d")
    html = re.sub(
        r'2026 KBO 리그 · .*? 기준',
        f'2026 KBO 리그 · {today} 기준',
        html
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html 업데이트 완료 ({today})")

if __name__ == "__main__":
    print("📡 데이터 수집 중...")
    standings = get_standings()
    schedule = get_schedule()
    batters = get_batters()
    pitchers = get_pitchers()
    print(f"순위: {len(standings)}팀 / 일정: {len(schedule)}경기 / 타자: {len(batters)}명 / 투수: {len(pitchers)}명")
    build_html(standings, schedule, batters, pitchers)
