#!/usr/bin/env python3
"""KFSP extra board: LIVE in-game legs/parlays and pregame PLAYER PROPS legs/parlays -> extra.json.
Separate from build.py on purpose: main pregame tabs/Best Parlay never see live markets. Never invents data:
every leg is a FanDuel PA OPEN/ACTIVE selection; estimates use ESPN scores/clock/win-prob, ESPN game logs, rosters."""
import json,os,re,time,math,datetime,unicodedata,urllib.request
from concurrent.futures import ThreadPoolExecutor
from math import erf,sqrt,exp
UTC=datetime.timezone.utc; now=datetime.datetime.now(UTC); NOW=now.strftime('%Y-%m-%d %H:%M UTC')
K='FhMFpcPWXMeyZxOx'; FD='https://sbapi.pa.sportsbook.fanduel.com/api/'; MAXLEGS=25
os.makedirs('.cache',exist_ok=True)
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
def get(u,ttl=0):
  cf='.cache/'+re.sub(r'\W','_',u)[-150:]
  if ttl and os.path.exists(cf) and time.time()-os.path.getmtime(cf)<ttl: return load(cf,None)
  try:
    d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=20))
    if ttl: json.dump(d,open(cf,'w'))
    return d
  except Exception as e:
    print('fetch fail',u[:90],e); return load(cf,None) if ttl else None
def imp(o): o=float(o); return 100/(o+100) if o>0 else -o/(-o+100)
def dec(o): return 1+(o/100 if o>0 else 100/-o)
def norm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
STOP={'fc','cf','city','united','utd','state','the','de','afc','sc','st','university','club','real'}
def toks(s): return {w for w in re.findall(r'[a-z]+',norm(s)) if len(w)>2 and w not in STOP}
def pname(s): return ' '.join(re.findall(r'[a-z]+',norm(s).replace(' jr.','').replace(' jr','').replace(' iii','').replace(' ii','')))
def ncdf(x): return 0.5*(1+erf(x/sqrt(2)))
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def od(r): return r['winRunnerOdds']['americanDisplayOdds']['americanOddsInt']
def fdlink(legs):
  legs=legs[:MAXLEGS]
  if not legs: return None
  return 'https://sportsbook.fanduel.com/addToBetslip?'+'&'.join(f"marketId%5B{i}%5D={L['fd_market_id']}&selectionId%5B{i}%5D={L['fd_selection_id']}" for i,L in enumerate(legs))
SPORTS={'nfl':'football','college-football':'football','nba':'basketball','nhl':'hockey','eng.1':'soccer','esp.1':'soccer','ita.1':'soccer','ger.1':'soccer','fra.1':'soccer','usa.1':'soccer','uefa.champions':'soccer'}
ET=now.astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
DAYS=[(ET-datetime.timedelta(hours=1)).strftime('%Y%m%d'),(ET-datetime.timedelta(hours=25)).strftime('%Y%m%d'),(ET+datetime.timedelta(hours=23)).strftime('%Y%m%d')]
# ---------- ESPN games (scores, clock, pregame lines) ----------
def espn(lg,day,ttl): return (get(f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/scoreboard?dates={day}&limit=300',ttl=ttl) or {}).get('events',[])
games={}
jobs=[(lg,d,0 if i==0 else 900) for lg in SPORTS for i,d in enumerate(DAYS)]
with ThreadPoolExecutor(12) as ex: res=list(ex.map(lambda j:(j[0],espn(*j)),jobs))
for lg,evs in res:
  for e in evs:
    c=e['competitions'][0]; st=e['status']; o=(c.get('odds') or [{}])[0] or {}
    g={'id':e['id'],'sport':lg,'name':e['name'],'start':e['date'],'state':st['type']['state'],'detail':st['type'].get('shortDetail'),
       'period':st.get('period') or 0,'clock':st.get('clock') or 0,'dclock':st.get('displayClock'),'details':o.get('details'),'ou':o.get('overUnder'),'teams':{}}
    for t in c['competitors']:
      g['teams'][t['homeAway']]={'name':t['team']['displayName'],'short':t['team'].get('shortDisplayName',''),'abbr':t['team'].get('abbreviation'),'tid':t['team'].get('id'),'score':float(t.get('score') or 0)}
    if g['id'] not in games or g['state']!='pre': games[g['id']]=g
def match(fdname,cands,start=None):
  n=fdname
  if ' @ ' in n: a,h=n.split(' @ ',1)
  elif ' v ' in n: h,a=n.split(' v ',1)
  else: return None
  a=re.sub(r'\s*\(.*?\)','',a); h=re.sub(r'\s*\(.*?\)','',h); best=None
  for g in cands:
    if start and abs((ts(start)-ts(g['start'])).total_seconds())>5400: continue
    T=g['teams']; sc=len(toks(h)&toks(T['home']['name']+' '+T['home']['short']))+len(toks(a)&toks(T['away']['name']+' '+T['away']['short']))
    if sc>=1 and (not best or sc>best[0]): best=(sc,g)
  return best[1] if best else None
# ======================= LIVE =======================
SD={'nba':(12.0,17.0),'college-football':(15.0,14.0),'nfl':(13.5,13.0)}
PER={'nfl':(4,900),'college-football':(4,900),'nba':(4,720),'nhl':(3,1200)}
def frac_left(g):
  if g['sport'] in PER:
    n,L=PER[g['sport']]; p=g['period']
    if p>n: return max(g['clock'],1)/(n*L)*0.5
    return max(0.0,((n-p)*L+g['clock'])/(n*L))
  m=re.match(r"(\d+)",g.get('dclock') or ''); mins=int(m.group(1)) if m else 0
  if (g.get('detail') or '').upper().startswith('HT'): mins=45
  return max(0.02,(94-mins)/94)
def pois(l,k): return exp(-l)*l**k/math.factorial(k)
def goal_grid(g,f):
  T=g['teams']; tot=float(g['ou']) if g.get('ou') else (6.1 if g['sport']=='nhl' else 2.7)
  lh,la=tot*0.53*f,tot*0.47*f; H=T['home']['score']; A=T['away']['score']
  return {(H+i,A+j):pois(lh,i)*pois(la,j) for i in range(12) for j in range(12)}
def espn_wp(g):
  if SPORTS[g['sport']] not in('football','basketball'): return None
  d=get(f"https://site.api.espn.com/apis/site/v2/sports/{SPORTS[g['sport']]}/{g['sport']}/summary?event={g['id']}") or {}
  w=d.get('winprobability') or []
  return w[-1].get('homeWinPercentage') if w else None
def live_model(g,L,wp):
  f=frac_left(g); T=g['teams']; H,A=T['home']['score'],T['away']['score']; k=L['kind']
  if g['sport'] in SD:
    sdm,sdt=SD[g['sport']]; hs=None
    try:
      ab,v=g['details'].rsplit(' ',1); v=float(v); hs=v if ab==T['home']['abbr'] else -v if ab==T['away']['abbr'] else None
    except Exception: pass
    mu=(-hs if hs is not None else 2.0)*f; s=max(sdm*sqrt(max(f,0.003)),0.5); cur=H-A
    if k=='ml':
      p=ncdf((cur+mu)/s); p=p if L['side']=='home' else 1-p
      if wp is not None: p=0.5*p+0.5*(wp if L['side']=='home' else 1-wp)
      return p
    if k=='spread' and L.get('line') is not None:
      m=(cur+mu) if L['side']=='home' else -(cur+mu); return ncdf((m+L['line'])/s)
    if k=='total' and L.get('line') is not None:
      tot=float(g['ou']) if g.get('ou') else None
      if tot is None: return None
      rem=tot*f; z=(H+A+rem-L['line'])/max(sdt*sqrt(max(f,0.003)),0.5); return ncdf(z) if L['ou']=='over' else ncdf(-z)
    return None
  G=goal_grid(g,f); P=lambda fn:sum(v for (h,a),v in G.items() if fn(h,a))
  sd=L.get('side')
  if k=='ml':  # NHL 2-way incl OT: ties split 50/50
    w=P(lambda h,a:h>a) if sd=='home' else P(lambda h,a:a>h); return w+0.5*P(lambda h,a:h==a) if g['sport']=='nhl' else None
  if k=='ml3': return P(lambda h,a:h>a) if sd=='home' else P(lambda h,a:a>h)
  if k=='dnb': w=P(lambda h,a:h>a) if sd=='home' else P(lambda h,a:a>h); return w/max(1-P(lambda h,a:h==a),1e-6)
  if k=='dc': return P(lambda h,a:h>=a) if sd=='home' else P(lambda h,a:a>=h) if sd=='away' else P(lambda h,a:h!=a)
  if k=='spread' and L.get('line') is not None: return P(lambda h,a:((h-a) if sd=='home' else (a-h))+L['line']>0)
  if k=='total' and L.get('line') is not None: return P(lambda h,a:(h+a>L['line']) if L['ou']=='over' else (h+a<L['line']))
def side_of(g,txt):
  t=toks(txt)
  if t & toks(g['teams']['home']['name']+' '+g['teams']['home']['short']): return 'home'
  if t & toks(g['teams']['away']['name']+' '+g['teams']['away']['short']): return 'away'
def num(s):
  m=re.search(r'([+-]?\d+(?:\.\d+)?)\)?\s*(?:goals?)?\s*$',s,re.I); return float(m.group(1)) if m else None
def parse_game_markets(g,mk,live):
  out=[]
  for m in mk.values():
    mt=m['marketType']
    if m.get('marketStatus')!='OPEN' or bool(m.get('inPlay'))!=live: continue
    rs=[r for r in m['runners'] if r.get('runnerStatus')=='ACTIVE' and r.get('winRunnerOdds',{}).get('americanDisplayOdds')]
    if not rs: continue
    S=sum(imp(od(r)) for r in rs)
    for r in rs:
      o=od(r); nm=r['runnerName']; L=None; p=None
      if mt in('MONEY_LINE','DRAW_NO_BET') and len(rs)==2: L={'kind':'ml' if mt=='MONEY_LINE' else 'dnb','side':side_of(g,nm)}; p=imp(o)/S
      elif mt=='WIN-DRAW-WIN' and len(rs)==3 and nm!='Draw': L={'kind':'ml3','side':side_of(g,nm)}; p=imp(o)/S
      elif mt=='DOUBLE_CHANCE' and len(rs)==3:
        sd=side_of(g,nm.split(' And ')[0]) if 'Draw' in nm else 'nodraw'; L={'kind':'dc','side':sd}; p=min(.999,imp(o)*2/S)
      elif mt=='MATCH_HANDICAP_(2-WAY)' and len(rs)==2: L={'kind':'spread','side':side_of(g,nm),'line':r.get('handicap')}; p=imp(o)/S
      elif mt in('ALTERNATE_HANDICAP','ALTERNATE_HANDICAPS','ALTERNATE_PUCK_LINE','ALTERNATE_SPREAD'): L={'kind':'spread','side':side_of(g,nm),'line':num(nm)}; p=imp(o)/(1.045 if o>-500 else 1.06)
      elif mt=='TOTAL_POINTS_(OVER/UNDER)' and len(rs)==2: L={'kind':'total','ou':nm.split()[0].lower(),'line':r.get('handicap')}; p=imp(o)/S
      elif re.fullmatch(r'OVER_UNDER_\d+',mt) and len(rs)==2: L={'kind':'total','ou':nm.split()[0].lower(),'line':num(nm.replace(' Goals',''))}; p=imp(o)/S
      elif mt in('ALTERNATE_TOTAL','ALTERNATE_TOTAL_POINTS','ALTERNATE_TOTAL_GOALS'): L={'kind':'total','ou':nm.split()[0].lower(),'line':num(nm)}; p=imp(o)/(1.045 if o>-500 else 1.06)
      if not L or (L['kind'] in('ml','ml3','dnb','dc','spread') and not L.get('side')): continue
      if L['kind']=='total' and (L.get('line') is None or L['ou'] not in('over','under')): continue
      pick=nm+(f" {r['handicap']:+g}" if mt=='MATCH_HANDICAP_(2-WAY)' and r.get('handicap') else '')+(f" {r['handicap']:g}" if mt=='TOTAL_POINTS_(OVER/UNDER)' and r.get('handicap') else '')
      L.update({'id':f"{g['id']}:{r['selectionId']}:{m['marketId']}",'event':g['id'],'sport':g['sport'],'game':g['name'],'start':g['start'],'market':m['marketName'],
        'pick':pick,'odds':o,'fd_prob':round(min(p,.999),4),'fd_market_id':m['marketId'],'fd_selection_id':r['selectionId'],'fd_event':m['eventId']})
      out.append(L)
  return out
LIVE_FLOOR,LIVE_CEIL,MOVE=-1000,200,0.08
snap=load('live.snap.json',{}); newsnap={}
inplay=[]
for et in (1,6423,7522,7524):
  d=get(f"{FD}in-play?_ak={K}&eventTypeId={et}") or {}
  inplay+=list(((d.get('attachments') or {}).get('events') or {}).values())
livegames=[g for g in games.values() if g['state']=='in']
pairs=[]
for e in inplay:
  g=match(e['name'],livegames)
  if g: pairs.append((g,e))
def fetch_ev(e): return get(f"{FD}event-page?_ak={K}&eventId={e['eventId']}&tab=popular")
with ThreadPoolExecutor(10) as ex: pages=list(ex.map(lambda p:fetch_ev(p[1]),pairs))
with ThreadPoolExecutor(10) as ex: wps=list(ex.map(lambda p:espn_wp(p[0]),pairs))
live_legs=[]; dropped_move=0; live_cov={'espn_live':len(livegames),'fd_inplay_matched':len(pairs),'espn_winprob':sum(1 for w in wps if w is not None)}
for (g,e),pg,wp in zip(pairs,pages,wps):
  mk=((pg or {}).get('attachments') or {}).get('markets') or {}
  f=frac_left(g); T=g['teams']
  for L in parse_game_markets(g,mk,True):
    newsnap[L['id']]=L['fd_prob']
    if L['odds']<LIVE_FLOOR or L['odds']>LIVE_CEIL: continue
    if L['id'] in snap and abs(snap[L['id']]-L['fd_prob'])>MOVE: dropped_move+=1; continue
    mp=live_model(g,L,wp)
    if mp is None: continue
    if abs(mp-L['fd_prob'])>0.12: continue   # model and market disagree a lot -> something we can't see (red card, injury, stale clock)
    L['model_prob']=round(mp,4); L['prob']=round(min(.995,0.5*L['fd_prob']+0.5*mp),4)
    L['score']=f"{T['away']['abbr'] or T['away']['short']} {T['away']['score']:g} - {T['home']['abbr'] or T['home']['short']} {T['home']['score']:g}"
    L['clock']=g['detail']; L['asof']=NOW; L['espn_wp']=wp
    L['why']=f"{L['score']}, {g['detail']} ({f*100:.0f}% of game left). Score+clock model {mp*100:.1f}%"+(f" (incl. ESPN live win prob {(wp if L.get('side')=='home' else 1-wp)*100:.0f}%)" if wp is not None and L['kind']=='ml' else '')+f", FanDuel no-vig {L['fd_prob']*100:.1f}%."
    live_legs.append(L)
json.dump(newsnap,open('live.snap.json','w'))
lbest={}
for L in live_legs:
  k=L['event']
  if k not in lbest or (L['prob'],L['odds'])>(lbest[k]['prob'],lbest[k]['odds']): lbest[k]=L
lpool=sorted(lbest.values(),key=lambda L:-L['prob'])
def ticket(legs,typ):
  p=1; x=1
  for L in legs: p*=L['prob']; x*=dec(L['odds'])
  return {'n':len(legs),'legs':[L['id'] for L in legs],'est_prob':round(p,4),'fd_payout_x':round(x,2),'ev':round(p*x-1,4),'fd_link':fdlink(legs),'type':typ}
live_tix=[ticket(lpool[:n],'live') for n in range(1,min(10,len(lpool))+1)]
# ======================= PROPS =======================
PROP_SP={'nba':('basketball',['player-points','player-rebounds','player-assists','player-threes']),'nfl':('football',['passing-props','receiving-props','rushing-props']),'nhl':('hockey',['shots','points-assists'])}
fdev=[]
for lg in PROP_SP:
  d=get(f"{FD}content-managed-page?page=CUSTOM&customPageId={lg}&_ak={K}&timezone=America/New_York",ttl=240) or {}
  for e in ((d.get('attachments') or {}).get('events') or {}).values():
    if ' @ ' in e['name']: fdev.append((lg,e))
pre=[g for g in games.values() if g['state']=='pre' and g['sport'] in PROP_SP and 0<(ts(g['start'])-now).total_seconds()<30*3600]
ppairs=[]
for g in pre:
  e=next((e for lg,e in fdev if lg==g['sport'] and match(e['name'],[g],e['openDate'])),None)
  if e and not e.get('inPlay'): ppairs.append((g,e))
def ppages(pe):
  g,e=pe; mk={}
  for t in PROP_SP[g['sport']][1]:
    d=get(f"{FD}event-page?_ak={K}&eventId={e['eventId']}&tab={t}",ttl=240) or {}
    mk.update(((d.get('attachments') or {}).get('markets') or {}))
  return mk
with ThreadPoolExecutor(10) as ex: pmk=list(ex.map(ppages,ppairs))
# stat spec: key -> (gamelog field, label)
NBA={'POINTS':('points','points'),'REBOUNDS':('totalRebounds','rebounds'),'ASSISTS':('assists','assists'),'THREES':('threePointFieldGoalsMade-threePointFieldGoalsAttempted','made threes')}
def parse_props(g,mk):
  out=[]
  for m in mk.values():
    mt=m['marketType']; mn=m['marketName']
    if m.get('marketStatus')!='OPEN' or m.get('inPlay'): continue
    if re.search(r'QUARTER|PERIOD|HALF|DRIVE|FIRST|EACH|MINUTE|MOST_|SPECIAL',mt): continue
    rs=[r for r in m['runners'] if r.get('runnerStatus')=='ACTIVE' and r.get('winRunnerOdds',{}).get('americanDisplayOdds')]
    if not rs: continue
    S=sum(imp(od(r)) for r in rs); spec=None; th=[]
    if g['sport']=='nba':
      mm=re.fullmatch(r'TO_(?:SCORE|RECORD)_(\d+)\+_(POINTS|REBOUNDS|ASSISTS)',mt) or re.fullmatch(r'(\d+)\+_MADE_(THREES)',mt)
      if mm: spec=NBA[mm.group(2)]; th=[(r,r['runnerName'],int(mm.group(1)),'over',imp(od(r))/1.07) for r in rs]
      mm=re.fullmatch(r'PLAYER_[A-Z]_TOTAL_(POINTS|REBOUNDS|ASSISTS)',mt)
      if mm and len(rs)==2: spec=NBA[mm.group(1)]; th=[(r,r['runnerName'].rsplit(' ',1)[0],r['handicap'],r['runnerName'].rsplit(' ',1)[1].lower(),imp(od(r))/S) for r in rs]
    elif g['sport']=='nfl':
      mm=re.fullmatch(r'PLAYER_X_ALT_(RUSHING_YARDS|RECEIVING_YARDS|PASSING_YARDS|RECEPTIONS)_\w+',mt)
      if mm:
        spec={'RUSHING_YARDS':('rushingYards','rushing yards'),'RECEIVING_YARDS':('receivingYards','receiving yards'),'PASSING_YARDS':('passingYards','passing yards'),'RECEPTIONS':('receptions','receptions')}[mm.group(1)]
        for r in rs:
          x=re.match(r'(.+?) (\d+)\+ ',r['runnerName']+' ')
          if x: th.append((r,x.group(1),int(x.group(2)),'over',imp(od(r))/(1.07 if od(r)>-500 else 1.08)))
      mm=re.fullmatch(r'PLAYER_X_(RUSHING_YARDS|RECEIVING_YARDS|PASSING_YARDS|TOTAL_RECEPTIONS)_?\w*',mt)
      if mm and not th and len(rs)==2 and all(r.get('handicap') for r in rs):
        spec={'RUSHING_YARDS':('rushingYards','rushing yards'),'RECEIVING_YARDS':('receivingYards','receiving yards'),'PASSING_YARDS':('passingYards','passing yards'),'TOTAL_RECEPTIONS':('receptions','receptions')}[mm.group(1)]
        th=[(r,r['runnerName'].rsplit(' ',1)[0],r['handicap'],r['runnerName'].rsplit(' ',1)[1].lower(),imp(od(r))/S) for r in rs]
    elif g['sport']=='nhl':
      mm=re.fullmatch(r'PLAYER_TO_RECORD_(\d+)\+_(SHOTS_ON_GOAL|POINTS|ASSISTS)',mt)
      if mm: spec={'SHOTS_ON_GOAL':('shotsTotal','shots on goal'),'POINTS':('points','points'),'ASSISTS':('assists','assists')}[mm.group(2)]; th=[(r,r['runnerName'],int(mm.group(1)),'over',imp(od(r))/1.07) for r in rs]
      if mt=='PLAYER_TOTAL_SHOTS' and len(rs)==2: spec=('shotsTotal','shots on goal'); th=[(r,r['runnerName'].split(' - ')[0],r['handicap'],r['runnerName'].split()[-1].lower(),imp(od(r))/S) for r in rs]
    for r,pl,t,ou,p in th:
      if ou not in('over','under') or t is None: continue
      line=t-0.5 if isinstance(t,int) else float(t)
      out.append({'id':f"{g['id']}:{r['selectionId']}:{m['marketId']}",'event':g['id'],'sport':g['sport'],'game':g['name'],'start':g['start'],'market':mn,'player':pl.strip(),
        'stat':spec[0],'stat_label':spec[1],'line':line,'ou':ou,'pick':f"{pl.strip()} {'Over' if ou=='over' else 'Under'} {line:g} {spec[1]}" if not isinstance(t,int) else f"{pl.strip()} {t}+ {spec[1]}",
        'odds':od(r),'fd_prob':round(min(p,.995),4),'fd_market_id':m['marketId'],'fd_selection_id':r['selectionId']})
  return out
def roster(sp,lg,tid): return get(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/teams/{tid}/roster',ttl=3*3600) or {}
def teaminfo(sp,lg,tid): return get(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/teams/{tid}',ttl=6*3600) or {}
def gamelog(sp,lg,aid,season=None,ttl=3*3600):
  return get(f'https://site.web.api.espn.com/apis/common/v3/sports/{sp}/{lg}/athletes/{aid}/gamelog'+(f'?season={season}' if season else ''),ttl=ttl) or {}
def glrows(gl,field):
  names=gl.get('names') or []; rows=[]
  if field.startswith('threePoint'): idx=names.index(field) if field in names else None
  else: idx=names.index(field) if field in names else None
  if idx is None: return rows
  evs=gl.get('events') or {}
  for s in gl.get('seasonTypes') or []:
    if 'Regular' not in s.get('displayName',''): continue
    for c in s.get('categories') or []:
      for e in c.get('events') or []:
        v=e['stats'][idx]; 
        try: v=float(str(v).split('-')[0])
        except Exception: continue
        mi=None
        if 'minutes' in names:
          try: mi=float(e['stats'][names.index('minutes')])
          except Exception: pass
        rows.append({'eid':e['eventId'],'date':(evs.get(e['eventId']) or {}).get('gameDate',''),'v':v,'min':mi})
  rows.sort(key=lambda r:r['date'],reverse=True); return rows
SEASON={'nba':(None,'2026'),'nhl':(None,'2026'),'nfl':(None,'2025')}
# rosters & injuries
teams={}
for g,_ in ppairs:
  sp=PROP_SP[g['sport']][0]
  for side in('home','away'):
    t=g['teams'][side]; r=roster(sp,g['sport'],t['tid']); al=[]
    for grp in r.get('athletes') or []: al+=grp['items'] if 'items' in grp else [grp]
    teams[(g['sport'],t['tid'])]={pname(a.get('fullName','')):a for a in al}
    ti=teaminfo(sp,g['sport'],t['tid']); rec=((ti.get('team') or {}).get('record') or {}).get('items') or []
    st={s['name']:s['value'] for s in (rec[0].get('stats') if rec else [])}
    teams[(g['sport'],t['tid'],'pa')]=st.get('avgPointsAgainst')
def lgavg(lg):
  v=[x for k,x in teams.items() if len(k)==3 and k[0]==lg and x]; return sum(v)/len(v) if v else None
BAD={'out','doubtful','questionable','day-to-day','injured reserve','suspension'}
props=[]; excl_inj=set(); nomatch=set(); pcov={'games':len(ppairs),'fd_markets':0,'players_matched':0}
raw=[]
for (g,e),mk in zip(ppairs,pmk):
  ls=parse_props(g,mk); pcov['fd_markets']+=len(ls); raw+=[(g,L) for L in ls]
need={}
for g,L in raw:
  for side in('home','away'):
    a=teams.get((g['sport'],g['teams'][side]['tid']),{}).get(pname(L['player']))
    if a: L['_a']=a; L['_side']=side; break
  if '_a' in L: need[(g['sport'],L['_a']['id'])]=1
def fetchgl(k):
  lg,aid=k; sp=PROP_SP[lg][0]; return k,(gamelog(sp,lg,aid),gamelog(sp,lg,aid,SEASON[lg][1],ttl=30*86400))
with ThreadPoolExecutor(12) as ex: GL=dict(ex.map(fetchgl,need))
outs={}
for (lg,tid),ros in [(k,v) for k,v in teams.items() if len(k)==2]:
  outs[(lg,tid)]=[a.get('fullName') for a in ros.values() if a.get('injuries') and (a['injuries'][0].get('status','').lower() =='out')]
for g,L in raw:
  a=L.pop('_a',None); side=L.pop('_side',None)
  if not a: nomatch.add(L['player']); continue
  inj=(a.get('injuries') or [{}])[0].get('status','') if a.get('injuries') else ''
  if inj.lower() in BAD: excl_inj.add(f"{L['player']} ({inj})"); continue
  cur,prev=GL.get((g['sport'],a['id']),({},{}))
  rc=glrows(cur,L['stat']); rp=glrows(prev,L['stat'])[:20]
  if not rc: continue   # no current-season game: role unknown, skip
  hit=lambda v:(v>L['line']) if L['ou']=='over' else (v<L['line'])
  wc,wp=1.0,0.4; hw=sum(wc*hit(r['v']) for r in rc)+sum(wp*hit(r['v']) for r in rp); n=wc*len(rc)+wp*len(rp)
  k=6.0; pemp=(hw+k*L['fd_prob'])/(n+k)
  p=0.5*L['fd_prob']+0.5*pemp; R=[]
  l5=rc[:5]; l10=(rc+rp)[:10]
  R.append(f"This season {sum(hit(r['v']) for r in rc)}/{len(rc)} games hit (avg {sum(r['v'] for r in rc)/len(rc):.1f})")
  R.append(f"last 10 {sum(hit(r['v']) for r in l10)}/{len(l10)}")
  if rp: R.append(f"last season's final 20: {sum(hit(r['v']) for r in rp)}/{len(rp)}")
  if g['sport']=='nba':
    mins=[r['min'] for r in rc if r['min'] is not None]; pm=[r['min'] for r in rp if r['min'] is not None]
    if len(mins)>=2 and pm:
      ratio=(sum(mins[:3])/len(mins[:3]))/(sum(pm)/len(pm))
      if ratio<0.8 and L['ou']=='over': p-=0.04; R.append(f"minutes down ({sum(mins[:3])/len(mins[:3]):.0f} vs {sum(pm)/len(pm):.0f} last season) -4 pts")
      elif ratio>1.15 and L['ou']=='over': p+=0.01; R.append(f"minutes up ({sum(mins[:3])/len(mins[:3]):.0f} vs {sum(pm)/len(pm):.0f}) +1 pt")
  opp='away' if side=='home' else 'home'; pa=teams.get((g['sport'],g['teams'][opp]['tid'],'pa')); la=lgavg(g['sport'])
  if pa and la:
    adj=max(-0.03,min(0.03,(pa/la-1)*0.4)); adj=adj if L['ou']=='over' else -adj; p+=adj
    R.append(f"{g['teams'][opp]['short']} allow {pa:.1f} {'goals' if g['sport']=='nhl' else 'pts'}/g vs {la:.1f} avg of today's teams ({adj*100:+.1f} pts)")
  mo=[x for x in outs.get((g['sport'],g['teams'][side]['tid']),[]) if x and pname(x)!=pname(L['player'])]
  if mo and L['ou']=='over' and g['sport']=='nba': p+=0.01; R.append('teammates out: '+', '.join(mo[:3])+' (+1 pt, more usage)')
  elif mo: R.append('teammates out: '+', '.join(mo[:3]))
  # 2026-10-28 review: graded props through 10-27 - rebounds over hit 66.7% vs 79.3% model (63 legs), under 46.7% vs 64.5% (15);
  # made threes 75.0% vs 79.5% (108). Points/assists/shots are calibrated. Haircut (about 2/3 of the gap) so they rank honestly.
  hc=(0.08 if L['ou']=='over' else 0.10) if L['stat']=='totalRebounds' else 0.03 if L['stat'].startswith('threePoint') else 0.0
  if hc: p-=hc; L['haircut']=hc; R.append(f"{L['stat'][:5]=='total' and 'rebounds' or 'threes'} calibration haircut -{hc*100:.0f} pts (these props hit below estimate so far)")
  L.update({'prob':round(max(.01,min(.97,p)),4),'emp_prob':round(pemp,4),'n_games':len(rc),'injury':inj or 'none listed','why':'; '.join(R),'asof':NOW,'team':g['teams'][side]['name']})
  props.append(L)
pcov['players_matched']=len({L['player'] for L in props}); pcov['props_scored']=len(props); pcov['excluded_injury']=sorted(excl_inj); pcov['unmatched_players']=len(nomatch)
P_FLOOR,P_CEIL=-1000,150
# 2026-10-29 review: rebound UNDERS hit 9/20 (45%) here and 22/42 in the NBA tab vs ~63% est even after the haircut - excluded.
pp=[L for L in props if P_FLOOR<=L['odds']<=P_CEIL and L['prob']>=0.6 and L['prob']+L.get('haircut',0)-L['fd_prob']>=-0.02 and not(L['stat']=='totalRebounds' and L['ou']=='under')]  # FD-gap check before the haircut
byp={}
for L in pp:
  k=(L['event'],L['player'])
  if k not in byp or (L['prob'],L['odds'])>(byp[k]['prob'],byp[k]['odds']): byp[k]=L
ppool=sorted(byp.values(),key=lambda L:-L['prob'])
uses={}; prop_tix=[]
for n in range(1,min(15,len(ppool))+1):
  sel=[]; pg={}
  for L in sorted(ppool,key=lambda L:-(L['prob']-0.006*uses.get(L['id'],0))):
    if pg.get(L['event'],0)>=2 or uses.get(L['id'],0)>=5: continue
    sel.append(L); pg[L['event']]=pg.get(L['event'],0)+1
    if len(sel)==n: break
  if len(sel)<n: break
  for L in sel: uses[L['id']]=uses.get(L['id'],0)+1
  prop_tix.append(ticket(sorted(sel,key=lambda L:-L['prob']),'props'))
for t in prop_tix+live_tix: t['favorite']=False
for t in sorted([t for t in prop_tix if t['est_prob']>=0.5 and t['n']>=2],key=lambda t:-t['ev'])[:3]: t['favorite']=True
for t in sorted([t for t in live_tix if t['est_prob']>=0.5 and t['n']>=2],key=lambda t:-t['ev'])[:2]: t['favorite']=True
# ======================= history + grading =======================
H=load('extra.history.json',{'legs':{},'tickets':{}})
DATE=(ET-datetime.timedelta(hours=1)).strftime('%Y-%m-%d')
keep=lambda L:{k:L.get(k) for k in('id','event','sport','game','start','market','pick','kind','side','line','ou','player','stat','odds','prob','fd_prob')}
for L in live_legs:
  if L['id'] not in H['legs']: H['legs'][L['id']]={**keep(L),'type':'live','date':DATE,'logged':NOW,'clock':L['clock'],'score':L['score']}
for t in live_tix:
  k='live:'+','.join(sorted(t['legs']))
  if k not in H['tickets']: H['tickets'][k]={'type':'live','date':DATE,'n':t['n'],'legs':t['legs'],'est_prob':t['est_prob'],'logged':NOW}
allp={L['id']:L for L in props}
for L in ppool:  # props legs re-logged until the game starts, then locked
  if ts(L['start'])>now: H['legs'][L['id']]={**keep(L),'type':'props','date':DATE,'logged':NOW}
for t in prop_tix:
  k=f"props:{DATE}:{t['n']}"; old=H['tickets'].get(k)
  locked=old and any(ts(H['legs'][i]['start'])<=now for i in old['legs'] if i in H['legs'])
  if not locked: H['tickets'][k]={'type':'props','date':DATE,'n':t['n'],'legs':t['legs'],'est_prob':t['est_prob'],'logged':NOW}
def final(eid,sport):
  g=games.get(eid)
  if g and g['state']=='post': return g
  d=get(f"https://site.api.espn.com/apis/site/v2/sports/{SPORTS[sport]}/{sport}/summary?event={eid}",ttl=1800) or {}
  try:
    c=d['header']['competitions'][0]
    if c['status']['type']['state']!='post': return None
    return {'teams':{t['homeAway']:{'score':float(t['score'])} for t in c['competitors']},'state':'post'}
  except Exception: return None
def grade(x):
  if ts(x['start'])>now: return None
  g=final(x['event'],x['sport'])
  if not g: return None
  if x['type']=='live' or x.get('kind'):
    h,a=g['teams']['home']['score'],g['teams']['away']['score']; sd=x.get('side'); k=x.get('kind')
    mine,their=((h,a) if sd=='home' else (a,h))
    if k in('ml','ml3'): return 'won' if mine>their else 'lost'
    if k=='dnb': return 'push' if h==a else 'won' if mine>their else 'lost'
    if k=='dc': return ('won' if h!=a else 'lost') if sd=='nodraw' else ('won' if mine>=their else 'lost')
    if k=='spread': m=mine-their+x['line']; return 'push' if m==0 else 'won' if m>0 else 'lost'
    if k=='total': t=h+a; return 'push' if t==x['line'] else 'won' if (t>x['line'])==(x['ou']=='over') else 'lost'
    return None
  sp=PROP_SP[x['sport']][0]; aid=None
  for (lg,tid),ros in [(k,v) for k,v in teams.items() if len(k)==2]:
    if lg==x['sport'] and pname(x['player']) in ros: aid=ros[pname(x['player'])]['id']
  if not aid: aid=x.get('aid')
  if not aid: return None
  rows=glrows(gamelog(sp,x['sport'],aid,ttl=1800),x['stat'])
  r=next((r for r in rows if r['eid']==x['event']),None)
  if not r: return 'void' if (now-ts(x['start'])).total_seconds()>36*3600 else None
  return 'won' if ((r['v']>x['line']) if x['ou']=='over' else (r['v']<x['line'])) else 'lost'
for L in props:  # remember athlete id for grading after rosters change
  if L['id'] in H['legs'] and ts(L['start'])>now:
    for side in('home','away'):
      a=teams.get((L['sport'],next(g for g in [games.get(L['event'])] if g)['teams'][side]['tid']),{}).get(pname(L['player']))
      if a: H['legs'][L['id']]['aid']=a['id']
for x in H['legs'].values():
  if not x.get('result'):
    try: x['result']=grade(x)
    except Exception as e: print('grade fail',x['id'],e)
for t in H['tickets'].values():
  if t.get('result'): continue
  rs=[H['legs'].get(i,{}).get('result') for i in t['legs']]
  if 'lost' in rs: t['result']='lost'
  elif rs and all(r in('won','push','void') for r in rs): t['result']='won'
json.dump(H,open('extra.history.json','w'))
def st(typ):
  G=[x for x in H['legs'].values() if x['type']==typ and x.get('result') in('won','lost')]
  T=[t for t in H['tickets'].values() if t['type']==typ and t.get('result')]
  b={}
  for x in G:
    k=f"{int(x['prob']*10)*10}-{int(x['prob']*10)*10+10}%"; s=b.setdefault(k,{'n':0,'w':0,'p':0}); s['n']+=1; s['w']+=x['result']=='won'; s['p']+=x['prob']
  return {'graded_legs':len(G),'won':sum(x['result']=='won' for x in G),'hit':round(sum(x['result']=='won' for x in G)/len(G),4) if G else None,
    'expected':round(sum(x['prob'] for x in G)/len(G),4) if G else None,'tickets_graded':len(T),'tickets_won':sum(t['result']=='won' for t in T),
    'buckets':{k:{'n':v['n'],'hit':round(v['w']/v['n'],4),'pred':round(v['p']/v['n'],4)} for k,v in sorted(b.items())}}
for L in lpool+ppool: L['fd_link']=fdlink([L])
out={'updated':NOW,'live':{'legs':{L['id']:L for L in lpool},'all_legs':len(live_legs),'parlays':live_tix,'coverage':{**live_cov,'legs_dropped_price_move':dropped_move,'games_with_leg':len(lpool)},
  'games':[{'name':g['name'],'sport':g['sport'],'detail':g['detail'],'score':f"{g['teams']['away']['short']} {g['teams']['away']['score']:g} - {g['teams']['home']['short']} {g['teams']['home']['score']:g}"} for g in livegames],
  'rule':f"One leg per live game: the highest-chance FanDuel PA in-play selection priced {LIVE_FLOOR} to +{LIVE_CEIL}. Chance = 50% FanDuel live no-vig price + 50% our score/clock model (pregame spread/total from ESPN, ESPN live win probability for NFL/NBA/college, Poisson goals for NHL/soccer). Legs are dropped if the price moved more than {MOVE*100:.0f} pts since the last refresh or if our model and FanDuel disagree by more than 12 pts (usually news we can't see: red card, injury, stale clock).",
  'stats':st('live')},
 'props':{'legs':{L['id']:L for L in ppool},'parlays':prop_tix,'coverage':pcov,
  'rule':f"Pregame only. One leg per player (his highest-chance line priced {P_FLOOR} to +{P_CEIL}), at most 2 legs per game in a parlay, each leg in at most 5 tickets. Chance = 50% FanDuel no-vig price + 50% ESPN game-log hit rate (this season, plus last season's final 20 games at 40% weight, shrunk toward FanDuel when few games), then small adjustments: opponent points allowed (±3 pts max), NBA minutes trend, teammates out; rebounds overs -8 pts and made threes -3 pts, because those props have hit below estimate so far; rebound unders are excluded (they hit about 45% so far). Players listed Out/Doubtful/Questionable/Day-To-Day by ESPN are excluded. Only legs with est. chance ≥60% and not worse than FanDuel's own price by >2 pts.",
  'stats':st('props')}}
json.dump(out,open('extra.json','w'),indent=1)
print('live games',len(livegames),'matched',len(pairs),'live legs',len(live_legs),'pool',len(lpool),'| props scored',len(props),'pool',len(ppool),'tix',len(prop_tix),'excl inj',len(excl_inj))
