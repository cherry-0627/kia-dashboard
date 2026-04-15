import requests
import json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.koreabaseball.com/"
}

res = requests.post(
    "https://www.koreabaseball.com/ws/Schedule.asmx/GetMonthSchedule",
    headers={**HEADERS,
             "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
             "X-Requested-With": "XMLHttpRequest"},
    data={"leId": "1", "srIdList": "0,9,6", "seasonId": "2026", "gameMonth": "04"},
    timeout=15
)

data = json.loads(res.text)

# 예정 경기(KIA 포함)의 Text 전체 출력
print("=== 예정 경기 KIA 포함 셀 전체 HTML ===")
found = 0
for row_obj in data.get("rows", []):
    for cell in row_obj.get("row", []):
        cls = cell.get("Class", "") or ""
        html = cell.get("Text", "")
        if "endGame" in cls:
            continue
        if "KIA" not in html:
            continue
        print(f"\n[class='{cls}']")
        print(html[:500])
        found += 1
        if found >= 5:
            break
    if found >= 5:
        break
