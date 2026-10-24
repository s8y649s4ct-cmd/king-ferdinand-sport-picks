#!/usr/bin/env python3
"""KFSP build: fetch ESPN + FanDuel public JSON, build per-game best legs, parlays 1-27,
lines/history/stats. Idempotent; slow fetches cached (FanDuel 4 min, geocode/boxscores forever)."""
import json,os,re,time,datetime,unicodedata,urllib.request,urllib.parse
from concurrent.futures import ThreadPoolExecutor
UTC=datetime.timezone.utc; now=datetime.datetime.now(UTC); NOW=now.strftime('%Y-%m-%d %H:%M UTC')
cfg=json.load(open('legs.json')); notes=json.load(open('notes.json')); DATE=cfg['date']
FLOOR,CEIL=cfg['odds_floor'],cfg['odds_ceiling']; K='FhMFpcPWXMeyZxOx'; FD='https://sbapi.nj.sportsbook.fanduel.com/api/'
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
    print('fetch fail',u[:90],e); return load(cf,None)
def imp(o):
  o=float(o); return 100/(o+100) if o>0 else -o/(-o+100)
def norm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
STOP={'fc','cf','city','united','utd','state','the','de','afc','sc','st','university','club','real'}
def toks(s): return {w for w in re.findall(r'[a-z]+',norm(s)) if len(w)>2 and w not in STOP}
SPORTS={'college-football':'football','nba':'basketball','nhl':'hockey','mlb':'baseball','eng.1':'soccer','esp.1':'soccer','ita.1':'soccer','ger.1':'soccer','fra.1':'soccer','usa.1':'soccer'}
# ---------- ESPN games ----------
games=[]
for lg,sp in SPORTS.items():
  d=get(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/scoreboard?dates={DATE.replace("-","")}&limit=300') or {}
  for e in d.get('events',[]):
    c=e['competitions'][0]; o=(c.get('odds') or [{}])[0] or {}; ml=o.get('moneyline') or {}
    g={'id':e['id'],'sport':lg,'name':e['name'],'start':e['date'],'state':e['status']['type']['state'],'status':e['status']['type']['shortDetail'],
       'venue':c.get('venue',{}).get('fullName'),'indoor':c.get('venue',{}).get('indoor'),'city':c.get('venue',{}).get('address') or {},
       'espn_wx':e.get('weather'),'line':o.get('details'),'total':o.get('overUnder'),'book':(o.get('provider') or {}).get('name'),'teams':{}}
    for t in c['competitors']:
      m=ml.get(t['homeAway']) or {}
      g['teams'][t['homeAway']]={'name':t['team']['displayName'],'short':t['team'].get('shortDisplayName',''),'score':t.get('score'),'winner':t.get('winner'),
        'record':(t.get('records') or [{}])[0].get('summary'),'ml_open':(m.get('open') or {}).get('odds'),'ml':(m.get('close') or {}).get('odds')}
    games.append(g)
G={g['id']:g for g in games}
# ---------- FanDuel events ----------
pages=[('CUSTOM','nba'),('CUSTOM','nhl'),('CUSTOM','ncaaf'),('CUSTOM','mlb'),('SPORT','1')]
fdev=[]
for typ,pid in pages:
  q=f"page={typ}&"+(f"customPageId={pid}" if typ=='CUSTOM' else f"eventTypeId={pid}")
  d=get(f"{FD}content-managed-page?{q}&_ak={K}&timezone=America/New_York",ttl=240) or {}
  for e in (d.get('attachments') or {}).get('events',{}).values():
    n=e['name']
    if ' @ ' in n: a,h=n.split(' @ ',1)
    elif ' v ' in n: h,a=n.split(' v ',1)
    else: continue
    a=re.sub(r'\s*\(.*?\)','',a); h=re.sub(r'\s*\(.*?\)','',h)
    fdev.append({'id':e['eventId'],'name':n,'home':h,'away':a,'start':e['openDate']})
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
for g in games:
  best=None
  for f in fdev:
    if abs((ts(f['start'])-ts(g['start'])).total_seconds())>5400: continue
    sc=len(toks(f['home'])&toks(g['teams']['home']['name']+' '+g['teams']['home']['short']))+len(toks(f['away'])&toks(g['teams']['away']['name']+' '+g['teams']['away']['short']))
    if sc>=1 and (not best or sc>best[0]): best=(sc,f)
  g['fd']=best[1] if best else None
def fdpage(g): return get(f"{FD}event-page?_ak={K}&eventId={g['fd']['id']}&tab=popular",ttl=240) if g['fd'] else None
with ThreadPoolExecutor(12) as ex: pagesd=dict(zip([g['id'] for g in games],ex.map(fdpage,games)))
print('games',len(games),'fd matched',sum(1 for g in games if g['fd']))
# ---------- candidate legs ----------
PROP_VIG=1.07; ALT_VIG=1.045
def side_of(g,txt):
  t=toks(txt)
  if t & toks(g['fd']['home']): return 'home'
  if t & toks(g['fd']['away']): return 'away'
def num(s):
  m=re.search(r'([+-]?\d+(?:\.\d+)?)\)?\s*(?:goals?)?\s*$',s,re.I); return float(m.group(1)) if m else None
models=cfg['models']
SD={'nba':(12.0,17.0),'college-football':(15.0,14.0)}
from math import erf,sqrt
def ncdf(x): return 0.5*(1+erf(x/sqrt(2)))
MAIN={}
for g in games:
  d=pagesd.get(g['id']) or {}
  for m in (d.get('attachments') or {}).get('markets',{}).values():
    if m['marketType']=='MATCH_HANDICAP_(2-WAY)':
      for r in m['runners']:
        if side_of(g,r['runnerName'])=='home' and r.get('handicap') is not None: MAIN.setdefault(g['id'],{})['hs']=r['handicap']
    if m['marketType']=='TOTAL_POINTS_(OVER/UNDER)' and m['runners'] and m['runners'][0].get('handicap'): MAIN.setdefault(g['id'],{})['tot']=m['runners'][0]['handicap']
def dist_prob(g,L):
  sd=SD.get(g['sport']); mn=MAIN.get(g['id'],{})
  if not sd: return None
  if L['kind']=='spread' and 'hs' in mn and L.get('line') is not None:
    mu=-mn['hs'] if L['side']=='home' else mn['hs']   # expected margin for picked side
    return ncdf((mu+L['line'])/sd[0])
  if L['kind']=='total' and 'tot' in mn and L.get('line') is not None:
    z=(mn['tot']-L['line'])/sd[1]; return ncdf(z) if L['ou']=='over' else ncdf(-z)
cands=[]
for g in games:
  d=pagesd.get(g['id'])
  if not d: continue
  for m in (d.get('attachments') or {}).get('markets',{}).values():
    mt=m['marketType']; rs=[r for r in m['runners'] if r.get('runnerStatus')=='ACTIVE' and r.get('winRunnerOdds')]
    if not rs or m.get('marketStatus')!='OPEN': continue
    od=lambda r:r['winRunnerOdds']['americanDisplayOdds']['americanOddsInt']
    S=sum(imp(od(r)) for r in rs)
    for r in rs:
      o=od(r); nm=r['runnerName']; p=None; L=None
      if mt in('MONEY_LINE','DRAW_NO_BET') and len(rs)==2:
        sd=side_of(g,nm); p=imp(o)/S; L={'kind':'ml' if mt=='MONEY_LINE' else 'dnb','side':sd}
      elif mt=='WIN-DRAW-WIN' and len(rs)==3 and nm!='Draw':
        p=imp(o)/S; L={'kind':'ml3','side':side_of(g,nm)}
      elif mt=='DOUBLE_CHANCE' and len(rs)==3:
        p=imp(o)*2/S; sd='home' if 'Draw' in nm and side_of(g,nm)=='home' else 'away' if 'Draw' in nm else 'nodraw'
        L={'kind':'dc','side':sd}
      elif mt=='MATCH_HANDICAP_(2-WAY)' and len(rs)==2:
        p=imp(o)/S; L={'kind':'spread','side':side_of(g,nm),'line':r.get('handicap')}
      elif mt in('ALTERNATE_HANDICAP','ALTERNATE_HANDICAPS','ALTERNATE_RUN_LINES','ALTERNATE_PUCK_LINE','ALTERNATE_PUCK_LINES','ALTERNATE_SPREAD'):
        p=imp(o)/ALT_VIG; L={'kind':'spread','side':side_of(g,nm),'line':num(nm)}
      elif mt=='TOTAL_POINTS_(OVER/UNDER)' and len(rs)==2:
        p=imp(o)/S; L={'kind':'total','ou':nm.split()[0].lower(),'line':r.get('handicap')}
      elif re.fullmatch(r'OVER_UNDER_\d+',mt) and len(rs)==2:
        p=imp(o)/S; L={'kind':'total','ou':nm.split()[0].lower(),'line':num(nm.replace(' Goals',''))}
      elif mt in('ALTERNATE_TOTAL','ALTERNATE_TOTAL_POINTS','ALTERNATE_TOTAL_RUNS','ALTERNATE_TOTAL_GOALS'):
        p=imp(o)/ALT_VIG; L={'kind':'total','ou':nm.split()[0].lower(),'line':num(nm)}
      elif g['sport']=='nba':
        mm=re.fullmatch(r'TO_(?:SCORE|RECORD)_(\d+)\+_(POINTS|REBOUNDS|ASSISTS)',mt) or re.fullmatch(r'(\d+)\+_MADE_(THREES)',mt)
        if mm: p=imp(o)/PROP_VIG; L={'kind':'prop','player':nm,'stat':mm.group(2)[:3].replace('THR','3PM'),'ou':'over','line':int(mm.group(1))-0.5}
        elif re.fullmatch(r'PLAYER_[A-Z]_TOTAL_POINTS',mt) and len(rs)==2:
          p=imp(o)/S; L={'kind':'prop','player':nm.rsplit(' ',1)[0],'stat':'POI','ou':nm.rsplit(' ',1)[1].lower(),'line':r.get('handicap')}
      if not L or p is None or o<FLOOR or o>CEIL: continue
      if L.get('kind') in('ml','ml3','dnb','dc','spread') and not L.get('side'): continue
      if L.get('kind')=='total' and (L['line'] is None or L['ou'] not in('over','under')): continue
      L.update({'id':f"{g['id']}:{r['selectionId']}:{m['marketId']}",'event':g['id'],'sport':g['sport'],'game':g['name'],'start':g['start'],
        'market':m['marketName'],'pick':nm+(f" {r['handicap']:+g}" if r.get('handicap') and L['kind'] in('spread',) and mt=='MATCH_HANDICAP_(2-WAY)' else '')+(f" {r['handicap']:g}" if L['kind'] in('total','prop') and r.get('handicap') and mt in('TOTAL_POINTS_(OVER/UNDER)',) or (L['kind']=='prop' and r.get('handicap')) else ''),
        'odds':o,'fd_prob':round(p,4),'verified':True,'odds_src':f"FanDuel Sportsbook public API (NJ), event {g['fd']['id']}, fetched {NOW}"})
      # blend: model prob (moneyline only) + ESPN/DraftKings no-vig consensus
      tn=g['teams'].get(L.get('side'),{}).get('name') if L.get('side') in('home','away') else None
      parts=[p]
      dp=dist_prob(g,L)
      if dp is not None: parts.append(dp); L['dist_prob']=round(dp,4)
      if L['kind']=='ml' and tn:
        t=g['teams']
        try: parts.append(imp(t[L['side']]['ml'])/(imp(t['home']['ml'])+imp(t['away']['ml'])))
        except Exception: pass
      q=sum(parts)/len(parts)
      if L['kind']=='ml' and tn in models: w=cfg['model_weight']; q=(1-w)*q+w*models[tn]['prob']; L['model']=models[tn]['prob']; L['why_model']=models[tn]['why']
      L['market_prob']=round(sum(parts)/len(parts),4); L['prob']=round(q,4)
      cands.append(L)
# ---------- calibration ----------
hist=load('picks.history.json',[]); hist=hist if isinstance(hist,list) and (not hist or 'legs_detail' in hist[0]) else []
stats=load('stats.json',{})
def bucket(p): return f"{int(p*20)*5}-{int(p*20)*5+5}%"
cal=stats.get('calibration',{})
for L in cands:
  b=cal.get(bucket(L['prob']))
  if b and b['n']>=30: L['prob']=round(min(.99,L['prob']*max(.85,min(1.1,b['hit']/b['pred']))),4); L['calibrated']=True
# ---------- per-game best leg; parlays ----------
best={}
for L in cands:
  k=L['event']
  if k not in best or (L['prob'],-abs(L['odds']))>(best[k]['prob'],-abs(best[k]['odds'])): best[k]=L
pool=sorted([L for L in best.values() if G[L['event']]['state']=='pre'],key=lambda L:-L['prob'])
started=[L for L in best.values() if G[L['event']]['state']!='pre']
def dec(o): return 1+(o/100 if o>0 else 100/-o)
pars=[];P=1;D=1
for n in range(1,min(27,len(pool))+1):
  P*=pool[n-1]['prob']; D*=dec(pool[n-1]['odds'])
  pars.append({'n':n,'legs':[x['id'] for x in pool[:n]],'est_prob':round(P,5),'fd_payout_x':round(D,2),'ev':round(P*D-1,3)})
# Best parlay: per game, highest-prob leg priced -300 or longer (real payout); pick n in 3..6 maximizing prob*ln(payout), payout >= 3.5x
import math
BF=cfg.get('best_floor',-300); bb={}
for L in cands:
  if L['odds']<BF or G[L['event']]['state']!='pre': continue
  k=L['event']
  if k not in bb or L['prob']>bb[k]['prob']: bb[k]=L
bpool=sorted(bb.values(),key=lambda L:-L['prob']); bestp=None
for n in range(3,7):
  if len(bpool)<n: break
  P=math.prod(x['prob'] for x in bpool[:n]); D=math.prod(dec(x['odds']) for x in bpool[:n])
  if D>=3.5 and (not bestp or P*math.log(D)>bestp['score']): bestp={'n':n,'legs':[x['id'] for x in bpool[:n]],'est_prob':round(P,4),'fd_payout_x':round(D,2),'score':P*math.log(D)}
# ---------- lottery tickets: max sum log(p) s.t. sum log(dec) >= log(target), <=27 legs, one per game ----------
def lottery(cands,G,target,maxn=27):
  byg={}
  for L in cands:
    if G[L['event']]['state']!='pre' or not L.get('verified',True): continue
    byg.setdefault(L['event'],[]).append(L)
  LT=math.log(target); bestt=None
  for i in range(0,401):
    lam=i*0.025  # Lagrangian sweep: value = log p + lam*log d
    pick=[]
    for ls in byg.values():
      v,L=max(((math.log(L['prob'])+lam*math.log(dec(L['odds'])),L) for L in ls),key=lambda t:t[0])
      pick.append((v,L))
    pick.sort(key=lambda t:-t[0]); sel=[]; S=0
    for v,L in pick:
      if S>=LT or len(sel)>=maxn: break
      sel.append(L); S+=math.log(dec(L['odds']))
    if S<LT: continue
    # local improvement: drop legs whose removal keeps target
    for L in sorted(sel,key=lambda L:L['prob']):
      if S-math.log(dec(L['odds']))>=LT: sel.remove(L); S-=math.log(dec(L['odds']))
    P=math.prod(L['prob'] for L in sel)
    if not bestt or P>bestt[0]: bestt=(P,sel)
  return bestt
def edge(L): return L['prob']-L['fd_prob'] if L.get('fd_prob') else 0
def tix(sel,label,target=None):
  P=math.prod(L['prob'] for L in sel); D=math.prod(dec(L['odds']) for L in sel)
  return {'label':label,'target_x':target,'n':len(sel),'legs':[L['id'] for L in sel],'est_prob':P,'fd_payout_x':round(D,2),
    'one_in':round(1/P) if P>0 else None,'fd_odds':'+'+str(round((D-1)*100)),'ev':round(P*D-1,3)}
lot=[]; lotlegs={}
for T in cfg.get('lottery_tiers',[25,100,500,1000,10000,100000,1000000]):
  r=lottery(cands,G,T)
  if r: lot.append(tix(r[1],f'~{T:,}x',T)); lotlegs.update({L['id']:L for L in r[1]})
# 27-leg (or max) lottery: best-edge leg per game, top 27 by edge then prob
eg={}
for L in cands:
  if G[L['event']]['state']!='pre' or not L.get('verified',True): continue
  k=L['event']
  if k not in eg or (edge(L),L['prob'])>(edge(eg[k]),eg[k]['prob']): eg[k]=L
e27=sorted(eg.values(),key=lambda L:(-edge(L),-L['prob']))[:27]
if e27: lot.append(tix(e27,f'{len(e27)}-leg best-edge lottery')); lotlegs.update({L['id']:L for L in e27})
for L in lotlegs.values():
  L.setdefault('why',f"FanDuel no-vig {L.get('fd_prob',0)*100:.1f}%"+(f", line model {L['dist_prob']*100:.1f}%" if L.get('dist_prob') is not None else '')+(f", team model {L['model']*100:.1f}%" if L.get('model') is not None else '')+f" -> est. {L['prob']*100:.1f}% (edge {edge(L)*100:+.1f} pts)")
# ---------- injuries, weather, lines (unchanged logic) ----------
slate={t['name'] for g in games for t in g['teams'].values()}; inj=list(notes['injuries'])
for lg in ['nba','nhl']:
  d=get(f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/injuries',ttl=600) or {}
  for t in d.get('injuries',[]):
    if t['displayName'] in slate:
      for i in t['injuries']: inj.append({'team':t['displayName'],'t':f"{i['athlete']['displayName']} - {i['status']}: {i.get('shortComment','')}",'src':'ESPN injuries feed'})
wxc=load('.cache/geo.json',{}); wx=[]
for g in games:
  if g['indoor']: continue
  if g['espn_wx']: wx.append({'g':g['name'],'w':f"{g['espn_wx']['displayValue']}, {g['espn_wx']['temperature']}F",'src':'ESPN/AccuWeather'}); continue
  city=g['city'].get('city')
  if not city: continue
  if city not in wxc:
    r=get('https://geocoding-api.open-meteo.com/v1/search?count=1&name='+urllib.parse.quote(city)); wxc[city]=(r.get('results') or [None])[0] if r else None
  loc=wxc[city]
  if not loc: continue
  f=get(f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&hourly=temperature_2m,precipitation_probability,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC&forecast_days=2",ttl=1800)
  try: i=f['hourly']['time'].index(g['start'][:13]+':00'); wx.append({'g':g['name'],'w':f"{f['hourly']['temperature_2m'][i]}F, wind {f['hourly']['wind_speed_10m'][i]} mph, rain {f['hourly']['precipitation_probability'][i]}%",'src':'open-meteo'})
  except Exception: pass
json.dump(wxc,open('.cache/geo.json','w'))
lh=load('lines.history.json',[]); snap={'at':NOW,'fd':{L['id']:L['odds'] for L in best.values()},'espn':{g['id']:{t['name']:t['ml'] for t in g['teams'].values()} for g in games}}
if not lh or lh[-1].get('fd')!=snap['fd'] or lh[-1].get('espn')!=snap['espn']: lh.append(snap)
lh=lh[-400:]; json.dump(lh,open('lines.history.json','w'))
firstfd={}
for s in lh:
  for k,v in (s.get('fd') or {}).items(): firstfd.setdefault(k,v)
moves=[]
for g in games:
  for t in g['teams'].values():
    if t['ml_open'] and t['ml'] and t['ml_open']!=t['ml']: moves.append({'g':g['name'],'team':t['name'],'open':t['ml_open'],'now':t['ml'],'src':'ESPN/DraftKings'})
for L in best.values():
  if firstfd.get(L['id']) not in(None,L['odds']): moves.append({'g':L['game'],'team':L['pick'],'open':firstfd[L['id']],'now':L['odds'],'src':'FanDuel (since first snapshot)'})
# ---------- grading ----------
box=load('.cache/box.json',{})
def boxstats(g):
  if g['id'] in box: return box[g['id']]
  d=get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={g['id']}") or {}; out={}
  for tm in (d.get('boxscore') or {}).get('players',[]):
    for st in tm['statistics']:
      lab=st['labels']
      for a in st['athletes']:
        s=dict(zip(lab,a.get('stats',[])))
        try: out[norm(a['athlete']['displayName'])]={'POI':int(s['PTS']),'REB':int(s['REB']),'AST':int(s['AST']),'3PM':int(s['3PT'].split('-')[0])}
        except Exception: pass
  box[g['id']]=out; return out
def grade(L):
  g=G.get(L['event'])
  if not g or g['state']!='post': return None
  h=float(g['teams']['home']['score'] or 0); a=float(g['teams']['away']['score'] or 0); k=L['kind']
  my,op=(h,a) if L.get('side')=='home' else (a,h)
  if k in('ml','ml3'): return 'win' if my>op else 'loss'
  if k=='dnb': return 'win' if my>op else 'void' if my==op else 'loss'
  if k=='dc': return ('win' if h!=a else 'loss') if L['side']=='nodraw' else ('win' if my>=op else 'loss')
  if k=='spread':
    v=my+L['line']-op; return 'win' if v>0 else 'void' if v==0 else 'loss'
  if k=='total':
    v=(h+a-L['line'])*(1 if L['ou']=='over' else -1); return 'win' if v>0 else 'void' if v==0 else 'loss'
  if k=='prop':
    s=boxstats(g).get(norm(L['player']))
    if not s: return 'void'
    v=(s[L['stat']]-L['line'])*(1 if L['ou']=='over' else -1); return 'win' if v>0 else 'loss'
json.dump(box,open('.cache/box.json','w'))
# history: one entry per date+n, overwritten until any leg's game starts (then locked)
H={x['id']:x for x in hist}; LD={L['id']:L for L in cands}
for p in pars:
  pid=f"{DATE}-{p['n']}"; old=H.get(pid)
  if old and old.get('locked'): continue
  H[pid]={'id':pid,'date':DATE,'n':p['n'],'est_prob':p['est_prob'],'fd_payout_x':p['fd_payout_x'],'legs_detail':[{k:LD[i][k] for k in('id','event','sport','kind','side','line','ou','player','stat','pick','market','odds','prob','game') if k in LD[i]} for i in p['legs']],'logged':NOW,'locked':False,'result':None}
for x in H.values():
  if not x.get('locked') and any(G.get(l['event'],{}).get('state')!='pre' for l in x['legs_detail']): x['locked']=True
  if x['result'] is None and x['date']==DATE:
    for l in x['legs_detail']:
      if l.get('result') is None:
        l['result']=grade(l)
    r=[l.get('result') for l in x['legs_detail']]
    if 'loss' in r: x['result']='loss'
    elif r and all(v in('win','void') for v in r): x['result']='win'
hist=sorted(H.values(),key=lambda x:(x['date'],x['n'])); json.dump(hist,open('picks.history.json','w'),indent=1)
# stats (unique graded legs)
seen={}
for x in hist:
  for l in x['legs_detail']:
    if l.get('result') in('win','loss'): seen[l['id']]=l
def agg(key):
  o={}
  for l in seen.values():
    k=key(l); b=o.setdefault(k,{'n':0,'wins':0,'pred':0})
    b['n']+=1; b['wins']+=l['result']=='win'; b['pred']+=l['prob']
  for b in o.values(): b['hit']=round(b['wins']/b['n'],3); b['pred']=round(b['pred']/b['n'],3)
  return o
par=[x for x in hist if x['result']]
stats={'updated':NOW,'graded_legs':len(seen),'calibration':agg(lambda l:bucket(l['prob'])),'by_sport':agg(lambda l:l['sport']),'by_market':agg(lambda l:l['kind']),
 'parlays':{'graded':len(par),'won':sum(x['result']=='win' for x in par)},'note':'Calibration factor applied to a probability bucket once it has 30+ graded legs.'}
json.dump(stats,open('stats.json','w'),indent=1)
# ---------- output ----------
kinds=sorted({L['kind'] for L in cands})
out={'updated':NOW,'date':DATE,'legs':{**{L['id']:L for L in best.values()},**({i:next(x for x in bpool if x['id']==i) for i in bestp['legs']} if bestp else {}),**lotlegs},'parlays':pars,'lottery':lot,'best':bestp,'started':[L['id'] for L in started],
 'games':games,'injuries':inj,'weather':wx,'moves':moves,'stats':stats,'feature':None,
 'note':f"{len(cands)} FanDuel-priced candidates ({', '.join(kinds)}) across {len(best)} games; best single market per game kept (odds {FLOOR} to +{CEIL}); {len(pool)} not-yet-started games -> parlays up to {len(pars)} legs."}
import feature
try: out['feature']=feature.build(bestp,out['legs'],games,cands,moves,wx,inj,get,SPORTS)
except Exception as e: print('feature fail',e)
for g in out['games']: g.pop('fd',None)
json.dump(out,open('picks.json','w'),indent=1)
print('cands',len(cands),'games w/ leg',len(best),'pool',len(pool),'parlays',len(pars),'best',bestp and bestp['n'],'kinds',kinds)
