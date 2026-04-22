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

PLAYER_INFO = {
    # 타자: 번호, 포지션
    '카스트로':{'num':'53','pos':'지명타자'}, '나성범':  {'num':'22','pos':'우익수'},
    '김선빈':  {'num':'3', 'pos':'2루수'},    '김도영':  {'num':'5', 'pos':'유격수'},
    '데일':    {'num':'58','pos':'1루수'},    '박민':    {'num':'2', 'pos':'3루수'},
    '오선우':  {'num':'56','pos':'1루수'},    '박재현':  {'num':'15','pos':'외야수'},
    '김호령':  {'num':'18','pos':'중견수'},   '한준수':  {'num':'55','pos':'포수'},
    '윤도현':  {'num':'44','pos':'내야수'},   '박상준':  {'num':'41','pos':'외야수'},
    '고종욱':  {'num':'30','pos':'외야수'},   '김규성':  {'num':'25','pos':'내야수'},
    '이창진':  {'num':'32','pos':'외야수'},   '박정우':  {'num':'38','pos':'내야수'},
    '김태군':  {'num':'57','pos':'포수'},
    # 투수: 번호, 포지션
    '네일':    {'num':'47','pos':'선발'},     '올러':    {'num':'49','pos':'선발'},
    '양현종':  {'num':'11','pos':'선발'},     '이의리':  {'num':'35','pos':'선발'},
    '김태형':  {'num':'17','pos':'선발'},     '최지민':  {'num':'39','pos':'불펜'},
    '성영탁':  {'num':'57','pos':'불펜'},     '이태양':  {'num':'29','pos':'불펜'},
    '조상우':  {'num':'1', 'pos':'불펜'},     '김범수':  {'num':'48','pos':'불펜'},
    '김기훈':  {'num':'55','pos':'불펜'},     '정해영':  {'num':'43','pos':'불펜'},
    '김시훈':  {'num':'33','pos':'불펜'},     '전상현':  {'num':'50','pos':'불펜'},
    '홍민규':  {'num':'21','pos':'불펜'},     '황동하':  {'num':'44','pos':'불펜'},
}
FAV_HITTERS = ['오선우','박재현']
FAV_PITCHERS = ['최지민']
FAV_PLAYER_IDS = {
    '오선우': ('hitter', '69636'),
    '박재현': ('hitter', '55636'),
    '최지민': ('pitcher', '52639'),
}
# KIA 타자 전체 playerId (개인 상세 페이지 직접 수집용)
KIA_HITTER_IDS = {
    '카스트로': '56626', '나성범': '62947', '김선빈': '78603', '김도영': '52605',
    '데일':    '56632', '박민':  '50657', '오선우': '69636', '박재현': '55636',
    '김호령':  '65653', '한준수': '68646', '윤도현': '52667', '박상준': '52634',
    '고종욱':  '61353', '김규성': '66614', '이창진': '64560', '박정우': '67609',
    '김태군':  '78122',
}
# KIA 투수 전체 playerId
KIA_PITCHER_IDS = {
    '네일':   '54640', '올러':   '55633', '양현종': '77637', '이의리': '51648',
    '김태형': '55610', '최지민': '52639', '성영탁': '54610', '이태양': '60768',
    '조상우': '63342', '김범수': '65769', '김기훈': '69620', '정해영': '50662',
    '김시훈': '68928', '전상현': '66609', '홍민규': '55267', '황동하': '52641',
}

def safe_int(s):
    try: return int(float(str(s).strip()) if s else 0)
    except: return 0

def safe_avg(s):
    try:
        f = float(s)
        return f".{int(f*1000):03d}" if f < 1 else f"{f:.3f}"
    except: return '-'

def scrape_kia_hitters():
    """KIA 타자 전체를 개인 상세 페이지에서 수집 후 타율순 정렬"""
    result = {}
    for name, pid in KIA_HITTER_IDS.items():
        d = fetch_fav_player(name, 'hitter', pid)
        if d:
            result[name] = d
    print(f"KIA 타자 수집: {len(result)}명")
    return result

def scrape_kia_pitchers():
    """KIA 투수 전체를 개인 상세 페이지에서 수집"""
    result = {}
    for name, pid in KIA_PITCHER_IDS.items():
        d = fetch_fav_player(name, 'pitcher', pid)
        if d:
            result[name] = d
    print(f"KIA 투수 수집: {len(result)}명")
    return result

def scrape_basicold_pages(base_url, is_hitter=True):
    """하위 호환용 — scrape_kia_hitters/pitchers로 대체됨"""
    if is_hitter: return scrape_kia_hitters()
    else: return scrape_kia_pitchers()

def fetch_fav_player(name, kind, pid):
    """즐겨찾기 선수 개인 상세 페이지에서 시즌 스탯 수집"""
    try:
        path = 'HitterDetail' if kind == 'hitter' else 'PitcherDetail'
        url = f"https://www.koreabaseball.com/Record/Player/{path}/Basic.aspx?playerId={pid}"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.select("table")
        if not tables: return None
        if kind == 'hitter':
            # 테이블0: AVG PA AB R H HR RBI BB SO SLG OBP OPS
            row = tables[0].select("tr")
            stat_row = row[1].select("td") if len(row) > 1 else []
            # 테이블1: BB IBB HBP SO GDP SLG OBP E ... OPS
            row1 = tables[1].select("tr")
            stat_row1 = row1[1].select("td") if len(row1) > 1 else []
            def g(r, i): return r[i].get_text(strip=True) if len(r) > i else '-'
            return {
                'pid': pid,
                'avg': safe_avg(g(stat_row, 1)),
                'pa':  safe_int(g(stat_row, 3)),
                'ab':  safe_int(g(stat_row, 4)),
                'r':   safe_int(g(stat_row, 5)),
                'h':   safe_int(g(stat_row, 6)),
                'hr':  safe_int(g(stat_row, 9)),
                'rbi': safe_int(g(stat_row, 11)),
                'bb':  safe_int(g(stat_row1, 0)),
                'so':  safe_int(g(stat_row1, 3)),
                'slg': g(stat_row1, 5),
                'obp': g(stat_row1, 6),
                'ops': g(stat_row1, 10),
            }
        else:
            # 투수 테이블0: 팀(0) ERA(1) G(2) CG(3) SHO(4) W(5) L(6) SV(7) HLD(8) WPCT(9) TBF(10) NP(11) IP(12) H(13)
            # 투수 테이블1: SAC(0) SF(1) BB(2) IBB(3) SO(4) WP(5) BK(6) R(7) ER(8) BSV(9) WHIP(10)
            row0 = tables[0].select("tr")
            row1 = tables[1].select("tr") if len(tables) > 1 else []
            s0 = row0[1].select("td") if len(row0) > 1 else []
            s1 = row1[1].select("td") if len(row1) > 1 else []
            def g(r, i): return r[i].get_text(strip=True) if len(r) > i else '-'
            ip = g(s0, 12)
            h  = safe_int(g(s0, 13))
            bb = safe_int(g(s1, 2))
            whip = g(s1, 10)
            return {
                'pid': pid,
                'era': g(s0, 1),
                'w':   safe_int(g(s0, 5)),
                'l':   safe_int(g(s0, 6)),
                'sv':  safe_int(g(s0, 7)),
                'hld': safe_int(g(s0, 8)),
                'ip':  ip,
                'h':   h,
                'bb':  bb,
                'k':   safe_int(g(s1, 4)),
                'whip': whip,
            }
    except Exception as e:
        print(f"  {name} 스탯 오류: {e}")
        return None

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

def _parse_schedule_table(table, now, games, next_game_ref):
    """테이블에서 KIA 경기 파싱. next_game_ref = [next_game] (mutable)"""
    cur_date=""
    for row in table.select("tr"):
        cols=row.select("td")
        if not cols: continue
        first=cols[0].get_text(strip=True)
        if re.match(r'\d{2}\.\d{2}\(\w+\)',first): cur_date=first
        col_t=[c.get_text(strip=True).upper() for c in cols]
        col_o=[c.get_text(strip=True) for c in cols]
        if 'KIA' not in col_t or not cur_date: continue
        dm=re.match(r'(\d{2})\.(\d{2})\((\w+)\)',cur_date)
        if not dm: continue
        mo,da,de=int(dm.group(1)),int(dm.group(2)),dm.group(3)
        date_str=f"{cur_date[:5]}({DAY_MAP.get(de,'')})"
        found=False
        for i,orig in enumerate(col_o):
            sm=re.match(r'^(\d{1,2}):(\d{1,2})$',orig)
            if not sm or i==0 or i>=len(col_t)-1: continue
            away,home=col_t[i-1],col_t[i+1]
            if away not in VALID_TEAMS or home not in VALID_TEAMS: continue
            if 'KIA' not in away and 'KIA' not in home: continue
            as_,hs_=int(sm.group(1)),int(sm.group(2))
            if 'KIA' in away: ks,os_,oe,vt=as_,hs_,home,'원정'
            else: ks,os_,oe,vt=hs_,as_,away,'홈'
            op=TEAM_ENG_KOR.get(oe,oe).split(' ')[0]
            # 중복 방지
            key=f"{date_str}-{op}"
            if not any(g['date']==date_str and g['opp']==f"vs {op}" for g in games):
                games.append({"date":date_str,"opp":f"vs {op}","score":f"{ks}-{os_}",
                              "result":'win' if ks>os_ else('lose' if ks<os_ else 'draw'),"venue":vt})
            found=True; break
        if not found:
            for i,orig in enumerate(col_o):
                tm=re.match(r'^(\d{2}):(\d{2})$',orig)
                if not tm or i==0 or i>=len(col_t)-1: continue
                h_,m_=int(tm.group(1)),int(tm.group(2))
                if h_<10 or h_>23: continue
                away,home=col_t[i-1],col_t[i+1]
                if away not in VALID_TEAMS or home not in VALID_TEAMS: continue
                if 'KIA' not in away and 'KIA' not in home: continue
                oe=home if 'KIA' in away else away
                vt='원정' if 'KIA' in away else '홈'
                op_kor=TEAM_ENG_KOR.get(oe,oe)
                op_short=op_kor.split(' ')[0]
                try:
                    fdt=datetime(now.year,mo,da,h_,m_)
                    fdt_str=fdt.strftime('%Y-%m-%dT%H:%M:%S')
                    # 중복 방지
                    if not any(g['date']==date_str and g['opp']==f"vs {op_short}" for g in games):
                        if next_game_ref[0] is None and fdt>=now:
                            next_game_ref[0]={"date":fdt_str,"opponent":op_kor,"venue":"","home":vt=='홈'}
                        games.append({"date":date_str,"opp":f"vs {op_short}",
                                      "score":orig,"result":"upcoming","venue":vt,"fullDate":fdt_str})
                except: pass
                break

def _scrape_monthly_schedule(year, month, now, games, next_game_ref):
    """KBO GetMonthSchedule API로 월간 KIA 경기 수집"""
    import json as _json
    from bs4 import BeautifulSoup as _BS
    DAY_KOR = ['월','화','수','목','금','토','일']
    # KBO 한글팀명 → 짧은이름 매핑
    KOR_SHORT = {
        'KIA':'KIA','LG':'LG','삼성':'삼성','한화':'한화',
        'SSG':'SSG','NC':'NC','KT':'KT','롯데':'롯데','두산':'두산','키움':'키움'
    }
    KOR_FULL = {
        'KIA':'KIA 타이거즈','LG':'LG 트윈스','삼성':'삼성 라이온즈','한화':'한화 이글스',
        'SSG':'SSG 랜더스','NC':'NC 다이노스','KT':'KT 위즈','롯데':'롯데 자이언츠',
        '두산':'두산 베어스','키움':'키움 히어로즈'
    }
    try:
        res = requests.post(
            "https://www.koreabaseball.com/ws/Schedule.asmx/GetMonthSchedule",
            headers={**HEADERS, 'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                     'X-Requested-With':'XMLHttpRequest'},
            data={'leId':'1','srIdList':'0,9,6','seasonId':str(year),'gameMonth':f'{month:02d}'},
            timeout=15
        )
        if res.status_code != 200:
            print(f"  월간스케줄 API 오류: {res.status_code}")
            return False

        data = _json.loads(res.text)
        before = len(games)

        for row_obj in data.get('rows', []):
            for cell in row_obj.get('row', []):
                html = cell.get('Text', '')
                cls  = cell.get('Class', '') or ''
                if not html or 'KIA' not in html:
                    continue
                soup = _BS(html, 'html.parser')

                # 날짜 추출
                day_tag = soup.find('li', class_='dayNum')
                if not day_tag: continue
                try:
                    da = int(day_tag.get_text(strip=True))
                    fdt_base = datetime(year, month, da)
                    dow = DAY_KOR[fdt_base.weekday()]
                    date_str = f"{month:02d}.{da:02d}({dow})"
                except:
                    continue

                # ── 완료 경기 (endGame) ──
                if 'endGame' in cls:
                    # gameId에서 팀코드 추출: 20260401HTLG0
                    a_tag = soup.find('a', href=True)
                    if not a_tag: continue
                    href = a_tag['href']
                    gm = re.search(r'gameId=(\d{8})([A-Z]{2})([A-Z]{2})\d', href)
                    if not gm: continue
                    away_code, home_code = gm.group(2), gm.group(3)
                    is_home = home_code == 'HT'
                    opp_code = away_code if is_home else home_code
                    # 점수
                    b_tag = soup.find('b')
                    if not b_tag: continue
                    score_txt = b_tag.get_text(strip=True)  # "2 : 7"
                    sm = re.match(r'(\d+)\s*:\s*(\d+)', score_txt)
                    if not sm: continue
                    s1, s2 = int(sm.group(1)), int(sm.group(2))
                    # gameId의 점수는 away:home 순
                    ks  = s2 if is_home else s1
                    os_ = s1 if is_home else s2
                    # 상대팀 한글
                    eng2kor = {'HT':'KIA','LG':'LG','SS':'삼성','HH':'한화',
                               'SK':'SSG','NC':'NC','KT':'KT','LT':'롯데','OB':'두산','WO':'키움'}
                    opp_short = eng2kor.get(opp_code, opp_code)
                    vt = '홈' if is_home else '원정'
                    if any(g2['date']==date_str and g2['opp']==f"vs {opp_short}" for g2 in games):
                        continue
                    games.append({"date":date_str,"opp":f"vs {opp_short}",
                                  "score":f"{ks}-{os_}",
                                  "result":'win' if ks>os_ else('lose' if ks<os_ else 'draw'),
                                  "venue":vt})

                # ── 예정 경기 (todayGame 또는 빈 class) ──
                else:
                    # <li>키움 : KIA [광주]</li> 형태
                    for li in soup.find_all('li'):
                        if li.get('class'): continue  # dayNum 등 스킵
                        txt = li.get_text(strip=True)
                        # "팀A : 팀B [구장]"
                        m2 = re.match(r'(.+?)\s*:\s*(.+?)\s*\[(.+?)\]', txt)
                        if not m2: continue
                        team_a, team_b = m2.group(1).strip(), m2.group(2).strip()
                        stadium = m2.group(3).strip()
                        if 'KIA' not in (team_a + team_b): continue
                        is_home = team_b == 'KIA'
                        opp_short = team_a if is_home else team_b
                        opp_full  = KOR_FULL.get(opp_short, opp_short)
                        vt = '홈' if is_home else '원정'
                        # 시작시간 기본 18:30
                        try:
                            fdt = datetime(year, month, da, 18, 30)
                            fdt_str = fdt.strftime('%Y-%m-%dT%H:%M:%S')
                        except:
                            continue
                        if any(g2['date']==date_str and g2['opp']==f"vs {opp_short}" for g2 in games):
                            continue
                        if next_game_ref[0] is None and fdt >= now:
                            next_game_ref[0] = {"date":fdt_str,"opponent":opp_full,
                                                "venue":stadium,"home":is_home}
                        games.append({"date":date_str,"opp":f"vs {opp_short}",
                                      "score":"18:30","result":"upcoming",
                                      "venue":vt,"fullDate":fdt_str})
                        break

        added = len(games) - before
        print(f"  월간스케줄({year}{month:02d}): {added}경기 추가")
        return added > 0
    except Exception as e:
        print(f"  월간스케줄 오류: {e}")
        return False

def get_kia_schedule():
    """GetScheduleList API로 KIA 경기 수집 (완료+예정, 실제 시간 포함)"""
    import json as _json
    from bs4 import BeautifulSoup as _BS
    DAY_KOR = ['월','화','수','목','금','토','일']
    KOR_FULL = {
        'KIA':'KIA 타이거즈','LG':'LG 트윈스','삼성':'삼성 라이온즈','한화':'한화 이글스',
        'SSG':'SSG 랜더스','NC':'NC 다이노스','KT':'KT 위즈','롯데':'롯데 자이언츠',
        '두산':'두산 베어스','키움':'키움 히어로즈'
    }
    now = datetime.now()
    games = []; next_game = None

    for year, month in [
        (now.year, now.month),
        (now.year if now.month < 12 else now.year+1, now.month+1 if now.month < 12 else 1)
    ]:
        try:
            res = requests.post(
                "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList",
                headers={**HEADERS,
                         'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                         'X-Requested-With':'XMLHttpRequest'},
                data={'leId':'1','srIdList':'0,9,6','seasonId':str(year),
                      'gameMonth':f'{month:02d}','teamId':'HT'},
                timeout=15
            )
            if res.status_code != 200:
                print(f"  스케줄 API 오류: {res.status_code} ({year}{month:02d})")
                continue

            data = _json.loads(res.text)
            added = 0
            for row_obj in data.get('rows', []):
                cells = row_obj.get('row', [])
                # 셀을 class로 매핑
                cell_map = {}
                none_cells = []
                for c in cells:
                    cls = c.get('Class') or ''
                    if cls:
                        cell_map[cls] = c.get('Text','')
                    else:
                        none_cells.append(c.get('Text',''))

                day_txt  = cell_map.get('day','')    # "04.15(수)"
                time_txt = cell_map.get('time','')   # "<b>18:30</b>"
                play_txt = cell_map.get('play','')   # "<span>KIA</span>..."
                # 구장은 None 셀 중 2번째 (index 1)
                stadium  = none_cells[1] if len(none_cells) > 1 else ''

                if not day_txt or not play_txt: continue

                # 날짜 파싱: "04.15(수)"
                dm = re.match(r'(\d{2})\.(\d{2})\(', day_txt)
                if not dm: continue
                mo, da = int(dm.group(1)), int(dm.group(2))

                # 시간 파싱: "<b>18:30</b>"
                tm = re.search(r'(\d{2}):(\d{2})', time_txt)
                h_, m_ = (int(tm.group(1)), int(tm.group(2))) if tm else (18, 30)

                try:
                    fdt = datetime(year, mo, da, h_, m_)
                    fdt_str = fdt.strftime('%Y-%m-%dT%H:%M:%S')
                    dow = DAY_KOR[fdt.weekday()]
                    date_str = f"{mo:02d}.{da:02d}({dow})"
                except:
                    continue

                # 팀/점수 파싱
                soup = _BS(play_txt, 'html.parser')
                spans = soup.find_all('span')
                if len(spans) < 2: continue
                team_away = spans[0].get_text(strip=True)
                team_home = spans[-1].get_text(strip=True)
                is_home = team_home == 'KIA'
                opp_short = team_away if is_home else team_home
                opp_full  = KOR_FULL.get(opp_short, opp_short)
                vt = '홈' if is_home else '원정'

                # 점수: win/lose class가 있으면 완료, 없으면 예정
                score_spans = soup.select('em span[class]')
                has_score = any(s.get('class',[''])[0] in ('win','lose') for s in score_spans)

                # 우천취소 체크 (none_cells 전체에서 검색)
                bigo_all = ' '.join(none_cells)
                if '취소' in bigo_all or '우천' in bigo_all:
                    continue  # 취소 경기 제외

                if has_score:
                    nums = [s.get_text(strip=True) for s in score_spans
                            if s.get_text(strip=True).isdigit()]
                    if len(nums) < 2: continue
                    s_away, s_home = int(nums[0]), int(nums[1])
                    ks  = s_home if is_home else s_away
                    os_ = s_away if is_home else s_home
                    games.append({"date":date_str,"opp":f"vs {opp_short}",
                                  "score":f"{ks}-{os_}",
                                  "result":'win' if ks>os_ else('lose' if ks<os_ else 'draw'),
                                  "venue":vt})
                else:
                    time_disp = f"{h_:02d}:{m_:02d}"
                    if next_game is None and fdt >= now:
                        next_game = {"date":fdt_str,"opponent":opp_full,
                                     "venue":stadium,"home":is_home}
                    games.append({"date":date_str,"opp":f"vs {opp_short}",
                                  "score":time_disp,"result":"upcoming",
                                  "venue":vt,"fullDate":fdt_str})
                added += 1

            print(f"  스케줄({year}{month:02d}): {added}경기 추가")
        except Exception as e:
            print(f"  스케줄 오류 ({year}{month:02d}): {e}")

    upcoming = [g for g in games if g.get('result')=='upcoming']
    print(f"KIA 경기: {len(games)}경기, 예정: {len(upcoming)}경기")
    return games, next_game

def get_top_batters():
    try:
        res=requests.get("https://www.koreabaseball.com/Record/Player/HitterBasic/BasicOld.aspx",headers=HEADERS,timeout=15)
        soup=BeautifulSoup(res.text,"html.parser")
        table=soup.select_one("table")
        if not table: return []
        out=[]
        for row in table.select("tr"):
            cols=row.select("td")
            if len(cols)<8: continue
            try: rank=int(cols[0].get_text(strip=True))
            except: continue
            name=cols[1].get_text(strip=True); team=cols[2].get_text(strip=True)
            try: avg=f".{int(float(cols[3].get_text(strip=True))*1000):03d}"
            except: avg='-'
            out.append({"rank":rank,"name":name,"team":team,"avg":avg,
                        "h":safe_int(cols[7].get_text(strip=True)),
                        "hr":safe_int(cols[10].get_text(strip=True)) if len(cols)>10 else 0,
                        "rbi":safe_int(cols[11].get_text(strip=True)) if len(cols)>11 else 0,
                        "kia":team=='KIA'})
            if len(out)>=10: break
        print(f"타자 순위: {len(out)}명"); return out
    except Exception as e: print(f"batters error: {e}"); return []

def get_top_pitchers():
    try:
        res=requests.get("https://www.koreabaseball.com/Record/Player/PitcherBasic/BasicOld.aspx",headers=HEADERS,timeout=15)
        soup=BeautifulSoup(res.text,"html.parser")
        table=soup.select_one("table")
        if not table: return []
        out=[]
        for row in table.select("tr"):
            cols=row.select("td")
            if len(cols)<10: continue
            try: rank=int(cols[0].get_text(strip=True))
            except: continue
            name=cols[1].get_text(strip=True); team=cols[2].get_text(strip=True)
            out.append({"rank":rank,"name":name,"team":team,
                        "era":cols[3].get_text(strip=True),
                        "ip":cols[13].get_text(strip=True) if len(cols)>13 else '-',
                        "k":safe_int(cols[18].get_text(strip=True)) if len(cols)>18 else 0,
                        "wl":f"{safe_int(cols[7].get_text(strip=True))}-{safe_int(cols[8].get_text(strip=True))}" if len(cols)>8 else '-',
                        "kia":team=='KIA'})
            if len(out)>=10: break
        print(f"투수 순위: {len(out)}명"); return out
    except Exception as e: print(f"pitchers error: {e}"); return []

def get_kia_team_stats():
    avg,avg_rank,era,era_rank='-','-','-','-'
    try:
        res=requests.get("https://www.koreabaseball.com/Record/Team/Hitter/Basic1.aspx",headers=HEADERS,timeout=15)
        soup=BeautifulSoup(res.text,"html.parser")
        table=soup.select_one("table")
        if table:
            for i,row in enumerate(table.select("tr")[1:]):
                cols=row.select("td")
                if len(cols)<3: continue
                if 'KIA' in cols[1].get_text():
                    avg=cols[2].get_text(strip=True); avg_rank=str(i+1); break
    except Exception as e: print(f"팀타율 오류: {e}")
    try:
        res2=requests.get("https://www.koreabaseball.com/Record/Team/Pitcher/Basic1.aspx",headers=HEADERS,timeout=15)
        soup2=BeautifulSoup(res2.text,"html.parser")
        table2=soup2.select_one("table")
        if table2:
            for i,row in enumerate(table2.select("tr")[1:]):
                cols=row.select("td")
                if len(cols)<3: continue
                if 'KIA' in cols[1].get_text():
                    era=cols[2].get_text(strip=True); era_rank=str(i+1); break
    except Exception as e: print(f"팀ERA 오류: {e}")
    print(f"팀타율: {avg}({avg_rank}위), 팀ERA: {era}({era_rank}위)")
    return avg,avg_rank,era,era_rank

def get_kia_stats_from_standings(standings, avg='-', avg_rank='-', era='-', era_rank='-'):
    for t in standings:
        if t.get('kia'):
            w,l=safe_int(t['w']),safe_int(t['l'])
            return {"rank":f"{t['rank']}위","record":f"{w} / 0 / {l}",
                    "winrate":t['pct'],"avg":avg,"avgRank":avg_rank,
                    "era":era,"eraRank":era_rank,"label":"2026 정규시즌 성적"}
    return None

def make_hitter(name, d):
    info = PLAYER_INFO.get(name, {'num':'-','pos':'-'})
    return {"name":name,"num":info['num'],"pos":info['pos'],
            "avg":d.get('avg','-'),"pa":d.get('pa',0),"ab":d.get('ab',0),
            "h":d.get('h',0),"r":d.get('r',0),"rbi":d.get('rbi',0),
            "hr":d.get('hr',0),"bb":d.get('bb',0),"so":d.get('so',0),
            "obp":d.get('obp','-'),"slg":d.get('slg','-'),"ops":d.get('ops','-')}

def make_pitcher(name, d):
    info = PLAYER_INFO.get(name, {'num':'-','pos':'투수'})
    return {"name":name,"num":info['num'],"pos":info['pos'],
            "era":d.get('era','-'),"w":d.get('w',0),"l":d.get('l',0),
            "sv":d.get('sv',0),"hld":d.get('hld',0),"ip":d.get('ip','0'),
            "bb":d.get('bb',0),"k":d.get('k',0),"whip":d.get('whip','-')}

def replace_in_regular(html, key, val):
    import re as _re
    m = _re.search(r'regular\s*:\s*\{', html)
    if not m: print(f"⚠️ regular: 없음"); return html
    reg_start = m.start()
    depth=0; reg_end=reg_start
    for i in range(reg_start, len(html)):
        if html[i]=='{': depth+=1
        elif html[i]=='}':
            depth-=1
            if depth==0: reg_end=i; break
    rb = html[reg_start:reg_end+1]
    ki = rb.find(f'    {key}:')
    if ki==-1: print(f"⚠️ {key} 없음"); return html
    cp = rb.find(':', ki+len(key)+4)
    sb = rb.find('[', cp); sc = rb.find('{', cp)
    if sb==-1: start=sc
    elif sc==-1: start=sb
    else: start=min(sb,sc)
    if start==-1: return html
    oc=rb[start]; cc=']' if oc=='[' else '}'
    d2=0; end=start
    for i in range(start, len(rb)):
        if rb[i]==oc: d2+=1
        elif rb[i]==cc:
            d2-=1
            if d2==0: end=i; break
    new_rb = rb[:start] + val + rb[end+1:]
    print(f"✅ {key} 교체")
    return html[:reg_start] + new_rb + html[reg_end+1:]

def build_html(standings, games, next_game, hitters, pitchers, batters, top_pitchers):
    with open("index.html","r",encoding="utf-8") as f: html=f.read()
    now=datetime.now(); today=now.strftime("%Y.%m.%d")

    if standings:
        html=replace_in_regular(html,'standings',json.dumps(standings,ensure_ascii=False))
        avg,avg_rank,era,era_rank=get_kia_team_stats()
        ks=get_kia_stats_from_standings(standings,avg,avg_rank,era,era_rank)
        if ks: html=replace_in_regular(html,'kiaStats',json.dumps(ks,ensure_ascii=False))

    if games:
        done=[g for g in games if g['result']!='upcoming'][-5:]
        upcoming=[g for g in games if g['result']=='upcoming'][:5]
        html=replace_in_regular(html,'recentGames',json.dumps(done+upcoming,ensure_ascii=False))
        # nextGame: 인수로 받은 게 없으면 upcoming 첫 번째에서 생성
        if not next_game and upcoming:
            u=upcoming[0]
            try:
                op_name=u['opp'].replace('vs ','')
                full=next((v for k,v in TEAM_ENG_KOR.items() if v.startswith(op_name)),op_name)
                next_game={"date":u.get('fullDate',''),"opponent":full,"venue":"","home":u.get('venue','')=='홈'}
            except: pass
    if next_game:
        html=replace_in_regular(html,'nextGame',json.dumps(next_game,ensure_ascii=False))

    if hitters:
        fav_names=['오선우','박재현']
        all_sorted=sorted(hitters.keys(), key=lambda n: -float(hitters[n].get('avg','-').replace('.','') or 0) if hitters[n].get('avg','-')!='-' else 0)
        main_h=[make_hitter(n,hitters[n]) for n in all_sorted if n not in fav_names][:10]
        html=replace_in_regular(html,'kiaHitters',json.dumps(main_h,ensure_ascii=False))
        # 즐겨찾기 타자: 개인 상세 페이지에서 직접 수집
        fav_h=[]
        for name in fav_names:
            kind, pid = FAV_PLAYER_IDS.get(name, (None, None))
            if not pid: continue
            d = fetch_fav_player(name, kind, pid)
            if d: fav_h.append(make_hitter(name, d))
        html=replace_in_regular(html,'kiaFavHitters',json.dumps(fav_h,ensure_ascii=False))

    if pitchers:
        fav_names=['최지민']
        def era_key(n):
            try: return float(pitchers[n].get('era','99'))
            except: return 99.0
        all_sorted=sorted(pitchers.keys(), key=era_key)
        main_p=[make_pitcher(n,pitchers[n]) for n in all_sorted if n not in fav_names][:10]
        html=replace_in_regular(html,'kiaPitchers',json.dumps(main_p,ensure_ascii=False))
        # 즐겨찾기 투수: 개인 상세 페이지에서 직접 수집
        fav_p=[]
        for name in fav_names:
            kind, pid = FAV_PLAYER_IDS.get(name, (None, None))
            if not pid: continue
            d = fetch_fav_player(name, kind, pid)
            if d: fav_p.append(make_pitcher(name, d))
        html=replace_in_regular(html,'kiaFavPitchers',json.dumps(fav_p,ensure_ascii=False))

    if batters:
        html=replace_in_regular(html,'batters',json.dumps(batters,ensure_ascii=False))
    if top_pitchers:
        html=replace_in_regular(html,'pitchers',json.dumps(top_pitchers,ensure_ascii=False))

    # JS 패치
    if "let currentPlayerTab" not in html and "currentPlayerTab = tab" in html:
        html=html.replace("let currentFavTab = ","let currentPlayerTab = 'hitters';\nlet currentFavTab = ")

    html=re.sub(r'2026 KBO 리그 · .*? 기준',f'2026 KBO 리그 · {today} 기준',html)
    with open("index.html","w",encoding="utf-8") as f: f.write(html)
    print(f"✅ index.html 완료 ({today})")

if __name__=="__main__":
    print("📡 KBO 데이터 수집 중...")
    standings      = get_standings()
    games,next_game= get_kia_schedule()

    print("KIA 타자 수집 중...")
    hitters = scrape_kia_hitters()
    print(f"KIA 타자: {len(hitters)}명 - {list(hitters.keys())}")

    print("KIA 투수 수집 중...")
    pitchers = scrape_kia_pitchers()
    print(f"KIA 투수: {len(pitchers)}명 - {list(pitchers.keys())}")

    batters     = get_top_batters()
    top_pitchers= get_top_pitchers()
    build_html(standings, games, next_game, hitters, pitchers, batters, top_pitchers)
