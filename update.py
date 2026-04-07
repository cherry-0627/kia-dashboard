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
    'KIA':'KIA 타이거즈','LG':'LG 트윈스','SAMSUNG':'삼성 라이온즈',
    'HANWHA':'한화 이글스','SSG':'SSG 랜더스','NC':'NC 다이노스',
    'KT':'KT 위즈','LOTTE':'롯데 자이언츠','DOOSAN':'두산 베어스','KIWOOM':'키움 히어로즈'
}
DAY_MAP={'MON':'월','TUE':'화','WED':'수','THU':'목','FRI':'금','SAT':'토','SUN':'일'}
VALID_TEAMS=set(TEAM_ENG_KOR.keys())
VENUE_MAP={'GWANGJU':'광주','JAMSIL':'잠실','MUNHAK':'문학','DAEJEON':'대전',
           'DAEGU':'대구','SAJIK':'사직','CHANGWON':'창원','SUWON':'수원',
           'ICHEON':'이천','GOCHEOK':'고척'}
PLAYER_NUM={'카스트로':'53','김선빈':'3','나성범':'22','데일':'58','김도영':'5',
            '박민':'2','오선우':'56','박재현':'15','네일':'47','올러':'49',
            '양현종':'11','이의리':'35','김태형':'17','최지민':'39','조상우':'1',
            '김호령':'18','윤도현':'99','한준수':'27'}
PLAYER_POS={'카스트로':'지명타자','김선빈':'2루수','나성범':'우익수','데일':'유격수',
            '김도영':'유격수','박민':'3루수','오선우':'1루수','박재현':'외야수',
            '김호령':'중견수','윤도현':'내야수','한준수':'포수'}
MAIN_HITTERS=['카스트로','나성범','김선빈','김도영','데일','박민']
FAV_HITTERS=['오선우','박재현']
MAIN_PITCHERS=['네일','올러','양현종','이의리','김태형']
FAV_PITCHERS=['최지민']

def get_standings():
    try:
        res=requests.get("https://eng.koreabaseball.com/Standings/TeamStandings.aspx",headers=HEADERS,timeout=15)
        soup=BeautifulSoup(res.text,"html.parser")
        rows=soup.select("table")[0].select("tr")[1:]
        out=[]
        for row in rows:
            cols=row.select("td")
            if len(cols)<8: continue
            try: rank=int(cols[0].get_text(strip=True))
            except: continue
            eng=cols[1].get_text(strip=True).upper()
            out.append({"rank":rank,"team":TEAM_ENG_KOR.get(eng,eng),
                        "g":cols[2].get_text(strip=True),"w":cols[3].get_text(strip=True),
                        "l":cols[4].get_text(strip=True),"pct":cols[6].get_text(strip=True),
                        "gb":cols[7].get_text(strip=True),"kia":eng=='KIA'})
        print(f"순위: {len(out)}팀"); return out
    except Exception as e: print(f"standings error: {e}"); return []

def get_kia_schedule():
    try:
        res=requests.get("https://eng.koreabaseball.com/Schedule/DailySchedule.aspx",headers=HEADERS,timeout=15)
        soup=BeautifulSoup(res.text,"html.parser")
        table=soup.select_one("table")
        if not table: return [],None
        rows=table.select("tr")
        games=[]; next_game=None; cur_date=""; now=datetime.now()
        for row in rows:
            cols=row.select("td")
            if not cols: continue
            first=cols[0].get_text(strip=True)
            if re.match(r'\d{2}\.\d{2}\(\w+\)',first): cur_date=first
            col_t=[c.get_text(strip=True).upper() for c in cols]
            col_o=[c.get_text(strip=True) for c in cols]
            if 'KIA' not in col_t: continue
            dm=re.match(r'(\d{2})\.(\d{2})\((\w+)\)',cur_date)
            if not dm: continue
            mo,da,de=int(dm.group(1)),int(dm.group(2)),dm.group(3)
            dk=DAY_MAP.get(de,'')
            date_str=f"{cur_date[:5]}({dk})"
            gdate=datetime(now.year,mo,da)
            found=False
            for i,txt in enumerate(col_t):
                sm=re.match(r'^(\d+):(\d+)$',txt)
                if not sm or i==0 or i>=len(col_t)-1: continue
                away,home=col_t[i-1],col_t[i+1]
                if away not in VALID_TEAMS or home not in VALID_TEAMS: continue
                if 'KIA' not in away and 'KIA' not in home: continue
                as_,hs_=int(sm.group(1)),int(sm.group(2))
                if 'KIA' in away: ks,os_,oe,vt=as_,hs_,home,'원정'
                else: ks,os_,oe,vt=hs_,as_,away,'홈'
                op=TEAM_ENG_KOR.get(oe,oe).split(' ')[0]
                res_='win' if ks>os_ else ('lose' if ks<os_ else 'draw')
                games.append({"date":date_str,"opp":f"vs {op}","score":f"{ks}-{os_}","result":res_,"venue":vt})
                found=True; break
            if not found:
                for i,orig in enumerate(col_o):
                    if not re.match(r'^\d{2}:\d{2}$',orig): continue
                    if i==0 or i>=len(col_t)-1: continue
                    away,home=col_t[i-1],col_t[i+1]
                    if away not in VALID_TEAMS or home not in VALID_TEAMS: continue
                    if 'KIA' not in away and 'KIA' not in home: continue
                    if 'KIA' in away: oe,vt=home,'원정'
                    else: oe,vt=away,'홈'
                    op_kor=TEAM_ENG_KOR.get(oe,oe)
                    op_short=op_kor.split(' ')[0]
                    vname=vt
                    for ct in col_o:
                        v=VENUE_MAP.get(ct.upper(),'')
                        if v: vname=v; break
                    h,m=map(int,orig.split(':'))
                    fdt=datetime(now.year,mo,da,h,m)
                    fdt_str=fdt.strftime('%Y-%m-%dT%H:%M:%S')
                    if next_game is None and fdt>=now:
                        next_game={"date":fdt_str,"opponent":op_kor,"venue":vname,"home":vt=='홈'}
                    games.append({"date":date_str,"opp":f"vs {op_short}","score":orig,"result":"upcoming","venue":vname,"fullDate":fdt_str})
                    break
        print(f"KIA 경기: {len(games)}경기")
        if next_game: print(f"다음 경기: {next_game['date']} vs {next_game['opponent']}")
        return games,next_game
    except Exception as e: print(f"schedule error: {e}"); return [],None

def scrape_kia_hitters():
    """KBO 전체 타자 기록에서 KIA 선수만 추출 - 모든 페이지 순회"""
    base_url = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx"
    kia = {}
    
    # 첫 페이지 가져오기 + ViewState 추출
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # ViewState 추출
        vs = soup.find('input', {'id': '__VIEWSTATE'})
        vsgen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
        ev = soup.find('input', {'id': '__EVENTVALIDATION'})
        
        viewstate = vs['value'] if vs else ''
        viewstategenerator = vsgen['value'] if vsgen else ''
        eventvalidation = ev['value'] if ev else ''
        
        def parse_page(soup):
            table = soup.select_one("table")
            if not table: return
            for row in table.select("tbody tr") or table.select("tr")[1:]:
                cols = row.select("td")
                if len(cols) < 9: continue
                team = cols[2].get_text(strip=True)
                if team != 'KIA': continue
                name = cols[1].get_text(strip=True)
                try:
                    ar = cols[3].get_text(strip=True)
                    avg = f".{int(float(ar)*1000):03d}" if ar and ar not in ['-',''] else '-'
                except: avg = '-'
                kia[name] = {
                    "avg": avg,
                    "h":   int(cols[8].get_text(strip=True) or 0),
                    "ab":  int(cols[6].get_text(strip=True) or 0),
                    "r":   int(cols[7].get_text(strip=True) or 0),
                    "hr":  int(cols[11].get_text(strip=True) or 0) if len(cols)>11 else 0,
                    "rbi": int(cols[13].get_text(strip=True) or 0) if len(cols)>13 else 0,
                }
        
        parse_page(soup)
        
        # 페이지 수 확인
        pager = soup.select('.pager a, .paginate a, [id*="ucPager"] a')
        page_nums = []
        for a in pager:
            try: page_nums.append(int(a.get_text(strip=True)))
            except: pass
        max_page = max(page_nums) if page_nums else 1
        print(f"  타자 총 {max_page}페이지")
        
        # 2페이지부터 POST로 가져오기
        for page in range(2, max_page+1):
            try:
                post_data = {
                    '__VIEWSTATE': viewstate,
                    '__VIEWSTATEGENERATOR': viewstategenerator,
                    '__EVENTVALIDATION': eventvalidation,
                    '__EVENTTARGET': f'ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$ucPager$btnNo{page}',
                    '__EVENTARGUMENT': '',
                }
                r2 = requests.post(base_url, headers={**HEADERS, 'Content-Type': 'application/x-www-form-urlencoded'}, data=post_data, timeout=15)
                s2 = BeautifulSoup(r2.text, "html.parser")
                parse_page(s2)
                # 다음 페이지용 ViewState 업데이트
                vs2 = s2.find('input', {'id': '__VIEWSTATE'})
                ev2 = s2.find('input', {'id': '__EVENTVALIDATION'})
                if vs2: viewstate = vs2['value']
                if ev2: eventvalidation = ev2['value']
            except Exception as e:
                print(f"  페이지 {page} 오류: {e}")
                break
                
    except Exception as e: print(f"hitter error: {e}")
    
    print(f"KIA 타자: {len(kia)}명 - {list(kia.keys())}"); return kia

def scrape_kia_pitchers():
    """KBO 전체 투수 기록에서 KIA 선수만 추출 - 모든 페이지"""
    base_url = "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx"
    kia = {}
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        vs = soup.find('input', {'id': '__VIEWSTATE'})
        ev = soup.find('input', {'id': '__EVENTVALIDATION'})
        viewstate = vs['value'] if vs else ''
        eventvalidation = ev['value'] if ev else ''
        
        def parse_page(soup):
            table = soup.select_one("table")
            if not table: return
            for row in table.select("tbody tr") or table.select("tr")[1:]:
                cols = row.select("td")
                if len(cols)<10 or cols[2].get_text(strip=True)!='KIA': continue
                name = cols[1].get_text(strip=True)
                kia[name] = {
                    "era":  cols[3].get_text(strip=True),
                    "w":    int(cols[5].get_text(strip=True) or 0),
                    "l":    int(cols[6].get_text(strip=True) or 0),
                    "sv":   int(cols[7].get_text(strip=True) or 0),
                    "ip":   cols[10].get_text(strip=True) if len(cols)>10 else '0.0',
                    "h":    int(cols[11].get_text(strip=True) or 0) if len(cols)>11 else 0,
                    "bb":   int(cols[13].get_text(strip=True) or 0) if len(cols)>13 else 0,
                    "k":    int(cols[15].get_text(strip=True) or 0) if len(cols)>15 else 0,
                    "whip": cols[18].get_text(strip=True) if len(cols)>18 else '-',
                }
        
        parse_page(soup)
        pager = soup.select('[id*="ucPager"] a')
        page_nums = []
        for a in pager:
            try: page_nums.append(int(a.get_text(strip=True)))
            except: pass
        max_page = max(page_nums) if page_nums else 1
        
        for page in range(2, max_page+1):
            try:
                post_data = {
                    '__VIEWSTATE': viewstate,
                    '__EVENTVALIDATION': eventvalidation,
                    '__EVENTTARGET': f'ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$ucPager$btnNo{page}',
                    '__EVENTARGUMENT': '',
                }
                r2 = requests.post(base_url, headers={**HEADERS, 'Content-Type': 'application/x-www-form-urlencoded'}, data=post_data, timeout=15)
                s2 = BeautifulSoup(r2.text, "html.parser")
                parse_page(s2)
                vs2 = s2.find('input', {'id': '__VIEWSTATE'})
                ev2 = s2.find('input', {'id': '__EVENTVALIDATION'})
                if vs2: viewstate = vs2['value']
                if ev2: eventvalidation = ev2['value']
            except Exception as e: print(f"  투수 페이지 {page} 오류: {e}"); break
                
    except Exception as e: print(f"pitcher error: {e}")
    print(f"KIA 투수: {len(kia)}명 - {list(kia.keys())}"); return kia

def mh(n,d): return {"name":n,"num":PLAYER_NUM.get(n,'-'),"pos":PLAYER_POS.get(n,'-'),"avg":d.get("avg",'-'),"hr":d.get("hr",0),"rbi":d.get("rbi",0),"r":d.get("r",0),"h":d.get("h",0),"ab":d.get("ab",0),"bb":0,"so":0,"obp":'-',"slg":'-',"ops":'-'}
def me(n): return {"name":n,"num":PLAYER_NUM.get(n,'-'),"pos":PLAYER_POS.get(n,'-'),"avg":'-',"hr":0,"rbi":0,"r":0,"h":0,"ab":0,"bb":0,"so":0,"obp":'-',"slg":'-',"ops":'-'}
def mp(n,d): pos="불펜" if n in FAV_PITCHERS else "선발"; return {"name":n,"num":PLAYER_NUM.get(n,'-'),"pos":pos,"era":d.get("era",'-'),"w":d.get("w",0),"l":d.get("l",0),"sv":d.get("sv",0),"ip":d.get("ip",'0.0'),"h":d.get("h",0),"bb":d.get("bb",0),"k":d.get("k",0),"whip":d.get("whip",'-'),"qs":0}
def mpe(n): pos="불펜" if n in FAV_PITCHERS else "선발"; return {"name":n,"num":PLAYER_NUM.get(n,'-'),"pos":pos,"era":'-',"w":0,"l":0,"sv":0,"ip":'0.0',"h":0,"bb":0,"k":0,"whip":'-',"qs":0}

def replace_in_regular(html, key, new_json_str):
    """regular: 섹션 안에서만 key를 찾아서 교체"""
    # regular: 블록 끝 위치 먼저 찾기
    reg_start = html.find('  regular: {')
    if reg_start == -1: reg_start = html.find('  regular:{')
    if reg_start == -1: print(f"⚠️ regular: 섹션 없음"); return html
    
    # regular: 블록의 끝 찾기 (중첩 중괄호 추적)
    depth = 0; reg_end = reg_start
    for i in range(reg_start, len(html)):
        if html[i] == '{': depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0: reg_end = i; break
    
    # regular 섹션만 추출
    regular_block = html[reg_start:reg_end+1]
    
    # key 찾기
    key_search = f'    {key}:'
    key_idx = regular_block.find(key_search)
    if key_idx == -1:
        key_search = f'    {key} :'
        key_idx = regular_block.find(key_search)
    if key_idx == -1:
        print(f"⚠️ {key} 패턴 실패 (regular 섹션 내)"); return html
    
    # [ 또는 { 시작
    colon_pos = regular_block.find(':', key_idx + len(key_search) - 1)
    start_bracket = regular_block.find('[', colon_pos)
    start_brace   = regular_block.find('{', colon_pos)
    if start_bracket == -1: start = start_brace
    elif start_brace  == -1: start = start_bracket
    else: start = min(start_bracket, start_brace)
    
    if start == -1: print(f"⚠️ {key} 시작 괄호 없음"); return html
    
    # 닫는 괄호
    open_ch = regular_block[start]
    close_ch = ']' if open_ch == '[' else '}'
    depth2 = 0; end = start
    for i in range(start, len(regular_block)):
        if regular_block[i] == open_ch: depth2 += 1
        elif regular_block[i] == close_ch:
            depth2 -= 1
            if depth2 == 0: end = i; break
    
    # 교체
    new_block = regular_block[:start] + new_json_str + regular_block[end+1:]
    result = html[:reg_start] + new_block + html[reg_end+1:]
    print(f"✅ {key} 교체")
    return result

def build_html(standings, games, next_game, hitters, pitchers):
    with open("index.html","r",encoding="utf-8") as f: html=f.read()
    now=datetime.now(); today=now.strftime("%Y.%m.%d")

    if standings:
        html = replace_in_regular(html, 'standings', json.dumps(standings, ensure_ascii=False))

    if games:
        done = [g for g in games if g['result']!='upcoming'][-10:]
        upcoming = [g for g in games if g['result']=='upcoming'][:3]
        html = replace_in_regular(html, 'recentGames', json.dumps(done+upcoming, ensure_ascii=False))

    if next_game:
        html = replace_in_regular(html, 'nextGame', json.dumps(next_game, ensure_ascii=False))

    if hitters:
        main_h = [mh(n,hitters[n]) if n in hitters else me(n) for n in MAIN_HITTERS]
        fav_h  = [mh(n,hitters[n]) if n in hitters else me(n) for n in FAV_HITTERS]
        html = replace_in_regular(html, 'kiaHitters', json.dumps(main_h, ensure_ascii=False))
        html = replace_in_regular(html, 'kiaFavHitters', json.dumps(fav_h, ensure_ascii=False))

    if pitchers:
        main_p = [mp(n,pitchers[n]) if n in pitchers else mpe(n) for n in MAIN_PITCHERS]
        fav_p  = [mp(n,pitchers[n]) if n in pitchers else mpe(n) for n in FAV_PITCHERS]
        html = replace_in_regular(html, 'kiaPitchers', json.dumps(main_p, ensure_ascii=False))
        html = replace_in_regular(html, 'kiaFavPitchers', json.dumps(fav_p, ensure_ascii=False))

    html = re.sub(r'2026 KBO 리그 · .*? 기준', f'2026 KBO 리그 · {today} 기준', html)
    with open("index.html","w",encoding="utf-8") as f: f.write(html)
    print(f"✅ index.html 완료 ({today})")

if __name__=="__main__":
    print("📡 KBO 데이터 수집 중...")
    standings         = get_standings()
    games, next_game  = get_kia_schedule()
    hitters           = scrape_kia_hitters()
    pitchers          = scrape_kia_pitchers()
    build_html(standings, games, next_game, hitters, pitchers)
