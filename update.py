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
    '오선우':   {'num':'56','pos':'1루수',   'pid':'69636'},
    '박재현':   {'num':'15','pos':'외야수',  'pid':'55636'},
}
PITCHER_INFO = {
    '네일':   {'num':'47','pos':'선발','pid':'54640'},
    '올러':   {'num':'49','pos':'선발','pid':'54642'},
    '양현종': {'num':'11','pos':'선발','pid':'62401'},
    '이의리': {'num':'35','pos':'선발','pid':'51648'},
    '김태형': {'num':'17','pos':'선발','pid':'77637'},
    '최지민': {'num':'39','pos':'불펜','pid':'52639'},
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
    """BasicOld.aspx 전체 페이지에서 KIA 선수 ID 수집 (POST 페이지네이션)"""
    ids = {}
    
    def parse_kia_from_soup(soup, hitter=True):
        path = 'HitterDetail' if hitter else 'PitcherDetail'
        for a in soup.select(f"table a[href*='{path}']"):
            name = a.get_text(strip=True)
            m = re.search(r'playerId=(\d+)', a.get('href',''))
            if not m: continue
            tr = a.find_parent('tr')
            if not tr: continue
            cols = tr.select('td')
            if len(cols) > 2 and cols[2].get_text(strip=True) == 'KIA':
                ids[name] = m.group(1)
    
    def fetch_all_pages(base_url, hitter=True):
        try:
            res = requests.get(base_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            parse_kia_from_soup(soup, hitter)
            
            # ViewState 추출
            vs = soup.find('input', {'id': '__VIEWSTATE'})
            ev = soup.find('input', {'id': '__EVENTVALIDATION'})
            if not vs: return
            
            viewstate = vs['value']
            eventvalidation = ev['value'] if ev else ''
            
            # 페이지 수 파악 (onclick에서)
            max_page = 1
            for tag in soup.find_all(attrs={'href': True}):
                m = re.search(r'btnNo(\d+)', tag.get('href',''))
                if m: max_page = max(max_page, int(m.group(1)))
            for tag in soup.find_all(attrs={'onclick': True}):
                m = re.search(r'btnNo(\d+)', tag.get('onclick',''))
                if m: max_page = max(max_page, int(m.group(1)))
            
            # 2페이지부터 POST
            for page in range(2, max_page + 1):
                try:
                    post_data = {
                        '__VIEWSTATE': viewstate,
                        '__EVENTVALIDATION': eventvalidation,
                        '__EVENTTARGET': f'ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$ucPager$btnNo{page}',
                        '__EVENTARGUMENT': '',
                    }
                    r2 = requests.post(base_url,
                        headers={**HEADERS, 'Content-Type': 'application/x-www-form-urlencoded'},
                        data=post_data, timeout=15)
                    s2 = BeautifulSoup(r2.text, 'html.parser')
                    parse_kia_from_soup(s2, hitter)
                    vs2 = s2.find('input', {'id': '__VIEWSTATE'})
                    ev2 = s2.find('input', {'id': '__EVENTVALIDATION'})
                    if vs2: viewstate = vs2['value']
                    if ev2: eventvalidation = ev2['value']
                except Exception as e:
                    print(f"  페이지 {page} 오류: {e}")
                    break
        except Exception as e:
            print(f"  ID 수집 오류: {e}")
    
    fetch_all_pages("https://www.koreabaseball.com/Record/Player/HitterBasic/BasicOld.aspx", hitter=True)
    fetch_all_pages("https://www.koreabaseball.com/Record/Player/PitcherBasic/BasicOld.aspx", hitter=False)
    
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
    """KBO 한국어 사이트에서 이번달 KIA 경기 일정 파싱"""
    from datetime import datetime, timedelta
    now = datetime.now()
    
    # 월별 일정 URL
    url = f"https://www.koreabaseball.com/Schedule/Schedule.aspx"
    
    games = []
    next_game = None
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 일정 테이블 찾기
        tables = soup.select("table.tbl")
        if not tables:
            tables = soup.select("table")
        
        DAY_KOR = {'월':'월','화':'화','수':'수','목':'목','금':'금','토':'토','일':'일'}
        TEAM_SHORT = {
            'KIA':'KIA','LG':'LG','삼성':'삼성','한화':'한화','SSG':'SSG',
            'NC':'NC','KT':'KT','롯데':'롯데','두산':'두산','키움':'키움'
        }
        
        cur_month = now.month
        cur_year = now.year
        
        for table in tables:
            rows = table.select("tr")
            cur_date_str = ""
            cur_day = None
            
            for row in rows:
                cols = row.select("td, th")
                if not cols: continue
                
                row_text = row.get_text()
                
                # 날짜 행 감지 (숫자로 시작하는 경우)
                first = cols[0].get_text(strip=True)
                
                # KIA 포함 행 파싱
                if 'KIA' not in row_text: continue
                
                # 각 컬럼에서 팀명과 스코어 찾기
                texts = [c.get_text(strip=True) for c in cols]
                
                # 날짜 파싱
                for t in texts:
                    import re
                    dm = re.match(r'(\d+)\.(\d+)\((.)\)', t)
                    if dm:
                        cur_day = (int(dm.group(1)), int(dm.group(2)), dm.group(3))
                        break
                
                if not cur_day: continue
                mo, da, dw = cur_day
                date_str = f"{mo:02d}.{da:02d}({dw})"
                
                # 스코어 또는 시간 찾기
                score_found = False
                for i, t in enumerate(texts):
                    # 결과 스코어: 숫자:숫자
                    sm = re.match(r'^(\d+):(\d+)$', t)
                    if sm and i > 0 and i < len(texts)-1:
                        # KIA가 홈인지 원정인지
                        away_text = texts[i-1] if i > 0 else ''
                        home_text = texts[i+1] if i < len(texts)-1 else ''
                        
                        if 'KIA' in away_text:
                            ks, os_ = int(sm.group(1)), int(sm.group(2))
                            opp = home_text.replace('KIA','').strip()
                            vt = '원정'
                        elif 'KIA' in home_text:
                            os_, ks = int(sm.group(1)), int(sm.group(2))
                            opp = away_text.replace('KIA','').strip()
                            vt = '홈'
                        else:
                            continue
                        
                        result = 'win' if ks > os_ else ('lose' if ks < os_ else 'draw')
                        games.append({
                            "date": date_str,
                            "opp": f"vs {opp[:2]}",
                            "score": f"{ks}-{os_}",
                            "result": result,
                            "venue": vt
                        })
                        score_found = True
                        break
                    
                    # 예정 시간: HH:MM
                    tm = re.match(r'^(\d{2}):(\d{2})$', t)
                    if tm and not score_found:
                        h, m = int(tm.group(1)), int(tm.group(2))
                        
                        # KIA 상대팀 찾기
                        opp = ''
                        vt = '홈'
                        for j, tt in enumerate(texts):
                            if 'KIA' in tt and j != i:
                                # 반대편이 상대
                                other_idx = i-1 if j > i else i+1
                                if 0 <= other_idx < len(texts):
                                    opp = texts[other_idx].replace('KIA','').strip()[:2]
                                break
                        
                        try:
                            fdt = datetime(cur_year, mo, da, h, m)
                            fdt_str = fdt.strftime('%Y-%m-%dT%H:%M:%S')
                            if next_game is None and fdt >= now:
                                next_game = {"date": fdt_str, "opponent": opp or '?', "venue": "광주", "home": True}
                            games.append({
                                "date": date_str,
                                "opp": f"vs {opp}",
                                "score": f"{h:02d}:{m:02d}",
                                "result": "upcoming",
                                "venue": "홈",
                                "fullDate": fdt_str
                            })
                        except:
                            pass
                        break
        
        print(f"KIA 경기: {len(games)}경기")
        
    except Exception as e:
        print(f"schedule error: {e}")
    
    # 파싱 실패시 영문 사이트 폴백
    if len(games) == 0:
        return get_kia_schedule_eng()
    
    return games, next_game

def get_kia_schedule_eng():
    """영문 사이트 폴백"""
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
                    h,m_=map(int,orig.split(':'))
                    fdt=datetime(now.year,mo,da,h,m_)
                    fdt_str=fdt.strftime('%Y-%m-%dT%H:%M:%S')
                    if next_game is None and fdt>=now:
                        next_game={"date":fdt_str,"opponent":op_kor,"venue":"광주","home":True}
                    games.append({"date":date_str,"opp":f"vs {op_short}","score":orig,"result":"upcoming","venue":"홈","fullDate":fdt_str})
                    break
        return games, next_game
    except Exception as e:
        print(f"eng schedule error: {e}")
        return [], None


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
                # 두번째 테이블에서 bb, obp, slg, ops 추출
                bb, obp, slg, ops, so, pa = 0, '-', '-', '-', 0, 0
                pa = safe_int(cols[3].get_text(strip=True))
                # 두번째 테이블 찾기 (BB IBB HBP SO GDP SLG OBP E SB% MH OPS)
                for t2 in soup.select("table"):
                    rows2 = t2.select("tr")
                    for r2 in rows2:
                        c2 = r2.select("td")
                        if len(c2) >= 11:
                            # BB(0) IBB(1) HBP(2) SO(3) GDP(4) SLG(5) OBP(6) E(7) SB%(8) MH(9) OPS(10)
                            first_val = c2[0].get_text(strip=True)
                            try:
                                bb = safe_int(first_val)
                                so = safe_int(c2[3].get_text(strip=True))
                                slg = c2[5].get_text(strip=True)
                                obp = c2[6].get_text(strip=True)
                                ops = c2[10].get_text(strip=True)
                                break
                            except: pass
                return {
                    "avg": avg,
                    "pa":  pa,
                    "ab":  safe_int(cols[4].get_text(strip=True)),
                    "r":   safe_int(cols[5].get_text(strip=True)),
                    "h":   safe_int(cols[6].get_text(strip=True)),
                    "hr":  safe_int(cols[9].get_text(strip=True)) if len(cols)>9 else 0,
                    "rbi": safe_int(cols[11].get_text(strip=True)) if len(cols)>11 else 0,
                    "bb":  bb, "so": so, "obp": obp, "slg": slg, "ops": ops,
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
                # 투수: 팀(0) ERA(1) G(2) W(3) L(4) SV(5) HLD(6) WPCT(7) IP(8) H(9) HR(10) BB(11) HBP(12) SO(13) R(14) ER(15) WHIP(16)
                return {
                    "era":  cols[1].get_text(strip=True) or '-',
                    "w":    safe_int(cols[3].get_text(strip=True)),
                    "l":    safe_int(cols[4].get_text(strip=True)),
                    "sv":   safe_int(cols[5].get_text(strip=True)),
                    "hld":  safe_int(cols[6].get_text(strip=True)) if len(cols)>6 else 0,
                    "ip":   cols[8].get_text(strip=True) if len(cols)>8 else '0.0',
                    "bb":   safe_int(cols[11].get_text(strip=True)) if len(cols)>11 else 0,
                    "k":    safe_int(cols[13].get_text(strip=True)) if len(cols)>13 else 0,
                    "whip": cols[16].get_text(strip=True) if len(cols)>16 else '-',
                }
    except Exception as e:
        print(f"  {name} 오류: {e}")
    return None

def scrape_all_hitters(auto_ids=None):
    # auto_ids에 있는 모든 KIA 선수 + 기존 HITTER_INFO 합쳐서 조회
    all_ids = {}
    # 기존 하드코딩 ID
    for name, info in HITTER_INFO.items():
        all_ids[name] = info['pid']
    # 자동 수집 ID로 덮어쓰기 + 새 선수 추가
    if auto_ids:
        for name, pid in auto_ids.items():
            if name not in PITCHER_INFO:  # 투수 제외
                all_ids[name] = pid
    
    result = {}
    for name, pid in all_ids.items():
        info = HITTER_INFO.get(name, {'num':'-','pos':'-','pid':pid})
        info = info.copy()
        info['pid'] = pid
        data = fetch_hitter(name, info)
        if data:
            result[name] = data
            print(f"  타자 {name}: {data['avg']}")
        else:
            print(f"  타자 {name}: 기록 없음")
    print(f"KIA 타자: {len(result)}명")
    return result

def scrape_all_pitchers(auto_ids=None):
    all_ids = {}
    for name, info in PITCHER_INFO.items():
        all_ids[name] = info['pid']
    if auto_ids:
        for name, pid in auto_ids.items():
            if name not in HITTER_INFO:
                all_ids[name] = pid
    
    result = {}
    for name, pid in all_ids.items():
        info = PITCHER_INFO.get(name, {'num':'-','pos':'투수','pid':pid})
        info = info.copy()
        info['pid'] = pid
        data = fetch_pitcher(name, info)
        if data:
            result[name] = data
            print(f"  투수 {name}: ERA {data['era']}")
        else:
            print(f"  투수 {name}: 기록 없음")
    print(f"KIA 투수: {len(result)}명")
    return result

def mh(n,d,info): return {"name":n,"num":info['num'],"pos":info['pos'],"avg":d.get("avg",'-'),"pa":d.get("pa",0),"ab":d.get("ab",0),"h":d.get("h",0),"r":d.get("r",0),"rbi":d.get("rbi",0),"hr":d.get("hr",0),"bb":d.get("bb",0),"so":d.get("so",0),"obp":d.get("obp",'-'),"slg":d.get("slg",'-'),"ops":d.get("ops",'-')}
def me(n,info): return {"name":n,"num":info['num'],"pos":info['pos'],"avg":'-',"pa":0,"ab":0,"h":0,"r":0,"rbi":0,"hr":0,"bb":0,"so":0,"obp":'-',"slg":'-',"ops":'-'}
def mp(n,d,info): return {"name":n,"num":info['num'],"pos":info['pos'],"era":d.get("era",'-'),"w":d.get("w",0),"l":d.get("l",0),"sv":d.get("sv",0),"hld":d.get("hld",0),"ip":d.get("ip",'0.0'),"bb":d.get("bb",0),"k":d.get("k",0),"whip":d.get("whip",'-')}
def mpe(n,info): return {"name":n,"num":info['num'],"pos":info['pos'],"era":'-',"w":0,"l":0,"sv":0,"hld":0,"ip":'0.0',"bb":0,"k":0,"whip":'-'}


def get_top_batters():
    """BasicOld.aspx에서 전체 타자 순위 상위 10명"""
    try:
        res = requests.get("https://www.koreabaseball.com/Record/Player/HitterBasic/BasicOld.aspx",
                           headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table: return []
        out = []
        for row in table.select("tbody tr") or table.select("tr")[1:]:
            cols = row.select("td")
            if len(cols) < 8: continue
            try: rank = int(cols[0].get_text(strip=True))
            except: continue
            name = cols[1].get_text(strip=True)
            team = cols[2].get_text(strip=True)
            try:
                ar = cols[3].get_text(strip=True)
                avg = f".{int(float(ar)*1000):03d}" if ar and ar != '-' else '-'
            except: avg = '-'
            out.append({"rank":rank,"name":name,"team":team,"avg":avg,
                        "h":safe_int(cols[6].get_text(strip=True)),
                        "hr":safe_int(cols[9].get_text(strip=True)) if len(cols)>9 else 0,
                        "rbi":safe_int(cols[11].get_text(strip=True)) if len(cols)>11 else 0,
                        "kia":team=='KIA'})
            if len(out) >= 10: break
        print(f"타자 순위: {len(out)}명"); return out
    except Exception as e: print(f"batters error: {e}"); return []

def get_top_pitchers():
    """BasicOld.aspx에서 전체 투수 순위 상위 10명"""
    try:
        res = requests.get("https://www.koreabaseball.com/Record/Player/PitcherBasic/BasicOld.aspx",
                           headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table")
        if not table: return []
        out = []
        for row in table.select("tbody tr") or table.select("tr")[1:]:
            cols = row.select("td")
            if len(cols) < 8: continue
            try: rank = int(cols[0].get_text(strip=True))
            except: continue
            name = cols[1].get_text(strip=True)
            team = cols[2].get_text(strip=True)
            out.append({"rank":rank,"name":name,"team":team,
                        "era":cols[3].get_text(strip=True),
                        "ip":cols[8].get_text(strip=True) if len(cols)>8 else '-',
                        "k":safe_int(cols[13].get_text(strip=True)) if len(cols)>13 else 0,
                        "wl":f"{safe_int(cols[5].get_text(strip=True))}-{safe_int(cols[6].get_text(strip=True))}" if len(cols)>6 else '-',
                        "kia":team=='KIA'})
            if len(out) >= 10: break
        print(f"투수 순위: {len(out)}명"); return out
    except Exception as e: print(f"pitchers error: {e}"); return []

def get_kia_stats_from_standings(standings):
    for t in standings:
        if t.get('kia'):
            w,l = safe_int(t['w']),safe_int(t['l'])
            return {"rank":f"{t['rank']}위","record":f"{w} / 0 / {l}",
                    "winrate":t['pct'],"avg":"-","avgRank":"-","era":"-","eraRank":"-","label":"2026 정규시즌 성적"}
    return None

def replace_in_regular(html, key, new_json_str):
    # 공백 무관하게 regular: 섹션 찾기
    import re as _re
    m = _re.search(r'regular\s*:\s*\{', html)
    if not m: print(f"⚠️ regular: 섹션 없음"); return html
    reg_start = m.start()
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

def build_html(standings, games, next_game, hitters, pitchers, batters=None, top_pitchers=None):
    with open("index.html","r",encoding="utf-8") as f: html=f.read()
    now=datetime.now(); today=now.strftime("%Y.%m.%d")
    if standings:
        html=replace_in_regular(html,'standings',json.dumps(standings,ensure_ascii=False))
        kia_stats = get_kia_stats_from_standings(standings)
        if kia_stats:
            html=replace_in_regular(html,'kiaStats',json.dumps(kia_stats,ensure_ascii=False))
    if games:
        done=[g for g in games if g['result']!='upcoming'][-10:]
        upcoming=[g for g in games if g['result']=='upcoming'][:3]
        html=replace_in_regular(html,'recentGames',json.dumps(done+upcoming,ensure_ascii=False))
    if next_game:
        html=replace_in_regular(html,'nextGame',json.dumps(next_game,ensure_ascii=False))
    if hitters:
        # 모든 수집된 KIA 타자 - 타율 순 정렬
        def avg_sort(name):
            d = hitters.get(name, {})
            try: return -float(d.get('avg','-').replace('.','0.') if d.get('avg','-') != '-' else '0')
            except: return 0
        all_hitter_names = sorted(hitters.keys(), key=avg_sort)
        fav_names = [n for n in ['오선우','박재현'] if n in HITTER_INFO]
        main_names = [n for n in all_hitter_names if n not in fav_names]
        
        main_h = [mh(n, hitters[n], HITTER_INFO.get(n, {'num':'-','pos':'-','pid':''})) for n in main_names if n in hitters]
        fav_h  = [mh(n, hitters[n], HITTER_INFO.get(n, {'num':'-','pos':'-','pid':''})) if n in hitters else me(n, HITTER_INFO.get(n, {'num':'-','pos':'-','pid':''})) for n in fav_names]
        html=replace_in_regular(html,'kiaHitters',json.dumps(main_h,ensure_ascii=False))
        html=replace_in_regular(html,'kiaFavHitters',json.dumps(fav_h,ensure_ascii=False))
    if pitchers:
        def era_sort(name):
            d = pitchers.get(name, {})
            try:
                era = d.get('era', '99.99')
                return float(era) if era not in ['-',''] else 99.99
            except: return 99.99
        all_pitcher_names = sorted(pitchers.keys(), key=era_sort)
        fav_p_names = [n for n in ['최지민'] if n in PITCHER_INFO]
        main_p_names = [n for n in all_pitcher_names if n not in fav_p_names]
        
        main_p = [mp(n, pitchers[n], PITCHER_INFO.get(n, {'num':'-','pos':'투수','pid':''})) for n in main_p_names if n in pitchers]
        fav_p  = [mp(n, pitchers[n], PITCHER_INFO.get(n, {'num':'-','pos':'불펜','pid':''})) if n in pitchers else mpe(n, PITCHER_INFO.get(n, {'num':'-','pos':'불펜','pid':''})) for n in fav_p_names]
        html=replace_in_regular(html,'kiaPitchers',json.dumps(main_p,ensure_ascii=False))
        html=replace_in_regular(html,'kiaFavPitchers',json.dumps(fav_p,ensure_ascii=False))
    if batters:
        html=replace_in_regular(html,'batters',json.dumps(batters,ensure_ascii=False))
    if top_pitchers:
        html=replace_in_regular(html,'pitchers',json.dumps(top_pitchers,ensure_ascii=False))
    # JS 변수 초기화 패치
    if 'let currentPlayerTab' not in html:
        html = html.replace(
            "let currentSeason = 'regular'; // 정규시즌 고정",
            "let currentSeason = 'regular'; // 정규시즌 고정\nlet currentPlayerTab = 'hitters';\nlet currentFavTab = 'hitters';"
        )
    html=re.sub(r'2026 KBO 리그 · .*? 기준',f'2026 KBO 리그 · {today} 기준',html)
    with open("index.html","w",encoding="utf-8") as f: f.write(html)
    print(f"✅ index.html 완료 ({today})")

if __name__=="__main__":
    print("📡 KBO 데이터 수집 중...")
    standings        = get_standings()
    games,next_game  = get_kia_schedule()
    auto_ids         = get_kia_player_ids()
    hitters          = scrape_all_hitters(auto_ids)
    pitchers_data    = scrape_all_pitchers(auto_ids)
    batters          = get_top_batters()
    top_pitchers     = get_top_pitchers()
    build_html(standings,games,next_game,hitters,pitchers_data,batters,top_pitchers)
