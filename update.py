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

# 선수 정보 (이름 → 번호, 포지션, KBO 선수ID)
HITTER_INFO = {
    '카스트로': {'num':'53','pos':'지명타자','pid':'56626'},
    '나성범':   {'num':'22','pos':'우익수',  'pid':'62947'},
    '김선빈':   {'num':'3', 'pos':'2루수',   'pid':'78603'},
    '김도영':   {'num':'5', 'pos':'유격수',  'pid':'52605'},
    '데일':     {'num':'58','pos':'유격수',  'pid':'56632'},
    '박민':     {'num':'2', 'pos':'3루수',   'pid':'50657'},
    '오선우':   {'num':'56','pos':'1루수',   'pid':'68009'},
    '박재현':   {'num':'15','pos':'외야수',  'pid':'68177'},
}
PITCHER_INFO = {
    '네일':   {'num':'47','pos':'선발','pid':'54640'},
    '올러':   {'num':'49','pos':'선발','pid':'54642'},
    '양현종': {'num':'11','pos':'선발','pid':'62401'},
    '이의리': {'num':'35','pos':'선발','pid':'51648'},
    '김태형': {'num':'17','pos':'선발','pid':'52108'},
    '최지민': {'num':'39','pos':'불펜','pid':'67234'},
}
MAIN_HITTERS  = ['카스트로','나성범','김선빈','김도영','데일','박민']
FAV_HITTERS   = ['오선우','박재현']
MAIN_PITCHERS = ['네일','올러','양현종','이의리','김태형']
FAV_PITCHERS  = ['최지민']

def safe_int(s):
    try: return int(float(str(s).strip()) if s else 0)
    except: return 0

def safe_avg(s):
    try:
        f = float(s)
        return f".{int(f*1000):03d}" if f < 1 else f"{f:.3f}"
    except: return '-'


def get_kia_player_ids():
    """BasicOld.aspx에서 KIA 선수 이름→playerId 자동 수집"""
    ids = {}
    base = "https://www.koreabaseball.com/Record/Player/HitterBasic/BasicOld.aspx"
    try:
        res = requests.get(base, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.select("table a[href*='playerId']"):
            name = a.get_text(strip=True)
            href = a.get('href','')
            m = re.search(r'playerId=(\d+)', href)
            if m:
                # 팀 확인
                tr = a.find_parent('tr')
                if tr:
                    cols = tr.select("td")
                    if len(cols) > 2 and cols[2].get_text(strip=True) == 'KIA':
                        ids[name] = m.group(1)
    except Exception as e:
        print(f"player ID 수집 오류: {e}")
    
    # 투수도 수집
    base2 = "https://www.koreabaseball.com/Record/Player/PitcherBasic/BasicOld.aspx"
    try:
        res = requests.get(base2, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.select("table a[href*='playerId']"):
            name = a.get_text(strip=True)
            href = a.get('href','')
            m = re.search(r'playerId=(\d+)', href)
            if m:
                tr = a.find_parent('tr')
                if tr:
                    cols = tr.select("td")
                    if len(cols) > 2 and cols[2].get_text(strip=True) == 'KIA':
                        ids[name] = m.group(1)
    except Exception as e:
        print(f"투수 ID 수집 오류: {e}")
    
    print(f"KIA 선수 ID 수집: {len(ids)}명 - {list(ids.keys())}")
    return ids

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
                    h,m_=map(int,orig.split(':'))
                    fdt=datetime(now.year,mo,da,h,m_)
                    fdt_str=fdt.strftime('%Y-%m-%dT%H:%M:%S')
                    if next_game is None and fdt>=now:
                        next_game={"date":fdt_str,"opponent":op_kor,"venue":vname,"home":vt=='홈'}
                    games.append({"date":date_str,"opp":f"vs {op_short}","score":orig,"result":"upcoming","venue":vname,"fullDate":fdt_str})
                    break
        print(f"KIA 경기: {len(games)}경기")
        if next_game: print(f"다음 경기: {next_game['date']} vs {next_game['opponent']}")
        return games,next_game
    except Exception as e: print(f"schedule error: {e}"); return [],None

def fetch_hitter(name, info):
    """선수 개인 페이지에서 타격 기록 조회"""
    url = f"https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId={info['pid']}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        # 타자 테이블: 팀명(0) AVG(1) G(2) PA(3) AB(4) R(5) H(6) 2B(7) 3B(8) HR(9) TB(10) RBI(11)
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.select("td")
                if len(cols) < 10: continue
                if cols[0].get_text(strip=True) != 'KIA': continue
                try:
                    ar = cols[1].get_text(strip=True)
                    avg = safe_avg(ar)
                except:
                    avg = '-'
                return {
                    "avg": avg,
                    "h":   safe_int(cols[6].get_text(strip=True)),
                    "ab":  safe_int(cols[4].get_text(strip=True)),
                    "r":   safe_int(cols[5].get_text(strip=True)),
                    "hr":  safe_int(cols[9].get_text(strip=True)) if len(cols)>9 else 0,
                    "rbi": safe_int(cols[11].get_text(strip=True)) if len(cols)>11 else 0,
                }
    except Exception as e:
        print(f"  {name} 오류: {e}")
    return None

def fetch_pitcher(name, info):
    """선수 개인 페이지에서 투구 기록 조회"""
    url = f"https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId={info['pid']}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        # KIA 팀명이 첫 컬럼인 행 찾기
        # 투수 테이블: 팀명(0) ERA(1) G(2) W(3) L(4) SV(5) HLD(6) WPCT(7) IP(8) H(9) HR(10) BB(11) HBP(12) SO(13) R(14) ER(15) WHIP(16)
        for table in soup.select("table"):
            for row in table.select("tr"):
                cols = row.select("td")
                if len(cols) < 10: continue
                if cols[0].get_text(strip=True) != 'KIA': continue
                return {
                    "era":  cols[1].get_text(strip=True) or '-',
                    "w":    safe_int(cols[3].get_text(strip=True)),
                    "l":    safe_int(cols[4].get_text(strip=True)),
                    "sv":   safe_int(cols[5].get_text(strip=True)),
                    "ip":   cols[8].get_text(strip=True) if len(cols)>8 else '0.0',
                    "h":    safe_int(cols[9].get_text(strip=True)) if len(cols)>9 else 0,
                    "bb":   safe_int(cols[11].get_text(strip=True)) if len(cols)>11 else 0,
                    "k":    safe_int(cols[13].get_text(strip=True)) if len(cols)>13 else 0,
                    "whip": cols[16].get_text(strip=True) if len(cols)>16 else '-',
                }
    except Exception as e:
        print(f"  {name} 오류: {e}")
    return None

def scrape_all_hitters(auto_ids=None):
    all_names = list(set(MAIN_HITTERS + FAV_HITTERS))
    result = {}
    for name in all_names:
        info = HITTER_INFO.get(name, {}).copy()
        # 자동 수집된 ID가 있으면 우선 사용
        if auto_ids and name in auto_ids:
            info['pid'] = auto_ids[name]
        if not info.get('pid'): continue
        data = fetch_hitter(name, info)
        if data:
            result[name] = data
            print(f"  타자 {name}: {data['avg']}")
        else:
            print(f"  타자 {name}: 기록 없음")
    print(f"KIA 타자: {len(result)}명")
    return result

def scrape_all_pitchers(auto_ids=None):
    all_names = list(set(MAIN_PITCHERS + FAV_PITCHERS))
    result = {}
    for name in all_names:
        info = PITCHER_INFO.get(name, {}).copy()
        if auto_ids and name in auto_ids:
            info['pid'] = auto_ids[name]
        if not info.get('pid'): continue
        data = fetch_pitcher(name, info)
        if data:
            result[name] = data
            print(f"  투수 {name}: ERA {data['era']}")
        else:
            print(f"  투수 {name}: 기록 없음")
    print(f"KIA 투수: {len(result)}명")
    return result

def mh(n,d,info): return {"name":n,"num":info['num'],"pos":info['pos'],"avg":d.get("avg",'-'),"hr":d.get("hr",0),"rbi":d.get("rbi",0),"r":d.get("r",0),"h":d.get("h",0),"ab":d.get("ab",0),"bb":0,"so":0,"obp":'-',"slg":'-',"ops":'-'}
def me(n,info): return {"name":n,"num":info['num'],"pos":info['pos'],"avg":'-',"hr":0,"rbi":0,"r":0,"h":0,"ab":0,"bb":0,"so":0,"obp":'-',"slg":'-',"ops":'-'}
def mp(n,d,info): return {"name":n,"num":info['num'],"pos":info['pos'],"era":d.get("era",'-'),"w":d.get("w",0),"l":d.get("l",0),"sv":d.get("sv",0),"ip":d.get("ip",'0.0'),"h":d.get("h",0),"bb":d.get("bb",0),"k":d.get("k",0),"whip":d.get("whip",'-'),"qs":0}
def mpe(n,info): return {"name":n,"num":info['num'],"pos":info['pos'],"era":'-',"w":0,"l":0,"sv":0,"ip":'0.0',"h":0,"bb":0,"k":0,"whip":'-',"qs":0}

def replace_in_regular(html, key, new_json_str):
    reg_start = html.find('  regular: {')
    if reg_start == -1: reg_start = html.find('  regular:{')
    if reg_start == -1: print(f"⚠️ regular: 섹션 없음"); return html
    depth = 0; reg_end = reg_start
    for i in range(reg_start, len(html)):
        if html[i] == '{': depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0: reg_end = i; break
    regular_block = html[reg_start:reg_end+1]
    key_search = f'    {key}:'
    key_idx = regular_block.find(key_search)
    if key_idx == -1: print(f"⚠️ {key} 패턴 실패"); return html
    colon_pos = regular_block.find(':', key_idx + len(key_search) - 1)
    sb = regular_block.find('[', colon_pos)
    sc = regular_block.find('{', colon_pos)
    if sb == -1: start = sc
    elif sc == -1: start = sb
    else: start = min(sb, sc)
    if start == -1: print(f"⚠️ {key} 시작 괄호 없음"); return html
    oc = regular_block[start]
    cc = ']' if oc == '[' else '}'
    depth2 = 0; end = start
    for i in range(start, len(regular_block)):
        if regular_block[i] == oc: depth2 += 1
        elif regular_block[i] == cc:
            depth2 -= 1
            if depth2 == 0: end = i; break
    new_block = regular_block[:start] + new_json_str + regular_block[end+1:]
    print(f"✅ {key} 교체")
    return html[:reg_start] + new_block + html[reg_end+1:]

def build_html(standings, games, next_game, hitters, pitchers):
    with open("index.html","r",encoding="utf-8") as f: html=f.read()
    now=datetime.now(); today=now.strftime("%Y.%m.%d")
    if standings:
        html=replace_in_regular(html,'standings',json.dumps(standings,ensure_ascii=False))
    if games:
        done=[g for g in games if g['result']!='upcoming'][-10:]
        upcoming=[g for g in games if g['result']=='upcoming'][:3]
        html=replace_in_regular(html,'recentGames',json.dumps(done+upcoming,ensure_ascii=False))
    if next_game:
        html=replace_in_regular(html,'nextGame',json.dumps(next_game,ensure_ascii=False))
    if hitters:
        main_h=[mh(n,hitters[n],HITTER_INFO[n]) if n in hitters else me(n,HITTER_INFO[n]) for n in MAIN_HITTERS if n in HITTER_INFO]
        fav_h =[mh(n,hitters[n],HITTER_INFO[n]) if n in hitters else me(n,HITTER_INFO[n]) for n in FAV_HITTERS  if n in HITTER_INFO]
        html=replace_in_regular(html,'kiaHitters',json.dumps(main_h,ensure_ascii=False))
        html=replace_in_regular(html,'kiaFavHitters',json.dumps(fav_h,ensure_ascii=False))
    if pitchers:
        main_p=[mp(n,pitchers[n],PITCHER_INFO[n]) if n in pitchers else mpe(n,PITCHER_INFO[n]) for n in MAIN_PITCHERS if n in PITCHER_INFO]
        fav_p =[mp(n,pitchers[n],PITCHER_INFO[n]) if n in pitchers else mpe(n,PITCHER_INFO[n]) for n in FAV_PITCHERS  if n in PITCHER_INFO]
        html=replace_in_regular(html,'kiaPitchers',json.dumps(main_p,ensure_ascii=False))
        html=replace_in_regular(html,'kiaFavPitchers',json.dumps(fav_p,ensure_ascii=False))
    html=re.sub(r'2026 KBO 리그 · .*? 기준',f'2026 KBO 리그 · {today} 기준',html)
    with open("index.html","w",encoding="utf-8") as f: f.write(html)
    print(f"✅ index.html 완료 ({today})")

if __name__=="__main__":
    print("📡 KBO 데이터 수집 중...")
    standings        = get_standings()
    games,next_game  = get_kia_schedule()
    auto_ids         = get_kia_player_ids()
    hitters          = scrape_all_hitters(auto_ids)
    pitchers         = scrape_all_pitchers(auto_ids)
    build_html(standings,games,next_game,hitters,pitchers)
