"""Extra free research per game (ESPN schedules/injuries/odds, open-meteo, lines history) -> modest prob adjustments.
Every source is optional: failures just mean that factor is skipped (and said so)."""
import datetime,math,re,urllib.parse
from concurrent.futures import ThreadPoolExecutor
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def hav(a,b):
  la1,lo1,la2,lo2=map(math.radians,(a['latitude'],a['longitude'],b['latitude'],b['longitude']))
  h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2; return 3959*2*math.asin(math.sqrt(h))
KEYPOS={'nfl':{'QB'},'college-football':{'QB'},'nhl':{'G'},'nba':set()}
LOWSCORE={'nhl','mlb','eng.1','esp.1','ita.1','ger.1','fra.1','usa.1'}
SOCCER={'eng.1','esp.1','ita.1','ger.1','fra.1','usa.1'}
OUTDOOR_WX={'nfl','college-football','mlb'}|SOCCER
def sc(c):
  s=c.get('score'); s=s.get('value') if isinstance(s,dict) else s
  try: return float(s)
  except Exception: return None
def build_ctx(games,get,SPORTS,geo,wxs):
  """returns {game_id:{side:{...}}, plus game-level keys}"""
  def geoc(city):
    if not city: return None
    if city not in geo:
      r=get('https://geocoding-api.open-meteo.com/v1/search?count=1&name='+urllib.parse.quote(city)); geo[city]=(r.get('results') or [None])[0] if r else None
    return geo[city]
  def sched(a):
    lg,tid=a
    return get(f"https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/teams/{tid}/schedule",ttl=10800) or {}
  keys={(g['sport'],t.get('tid')) for g in games if g['state']=='pre' for t in g['teams'].values() if t.get('tid')}
  with ThreadPoolExecutor(12) as ex: S=dict(zip(keys,ex.map(sched,keys)))
  inj={}
  for lg in {g['sport'] for g in games} & set(KEYPOS):
    d=get(f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/injuries',ttl=600) or {}
    for t in d.get('injuries',[]):
      for i in t.get('injuries',[]):
        pos=((i.get('athlete') or {}).get('position') or {}).get('abbreviation')
        if pos in KEYPOS[lg] and i.get('status') not in ('Active',):
          inj.setdefault((lg,t['displayName']),[]).append(f"{pos} {i['athlete']['displayName']} {i['status']}")
  ctx={}
  for g in games:
    if g['state']!='pre': continue
    st=ts(g['start']); c={'sides':{}}
    here=geoc((g['city'] or {}).get('city'))
    for side,t in g['teams'].items():
      x={'record':t.get('record'),'split':t.get('home_rec' if side=='home' else 'road_rec')}
      evs=[e for e in (S.get((g['sport'],t.get('tid'))) or {}).get('events',[]) if e['competitions'][0]['status']['type'].get('completed') and ts(e['date'])<st]
      evs.sort(key=lambda e:e['date'])
      if evs:
        last=evs[-1]; x['rest_days']=round((st-ts(last['date'])).total_seconds()/86400,1)
        x['b2b']=x['rest_days']<1.6 and g['sport'] in('nba','nhl')
        lc=(last['competitions'][0].get('venue') or {}).get('address',{}).get('city'); pl=geoc(lc)
        if pl and here and hav(pl,here)<3500: x['travel_mi']=round(hav(pl,here))  # bigger = likely geocode mix-up, skip
        res=[]
        for e in evs[-10:]:
          cs=e['competitions'][0]['competitors']; me=next((k for k in cs if k['team']['id']==t.get('tid')),None); op=next((k for k in cs if k is not me),None)
          if me and op and sc(me) is not None and sc(op) is not None: res.append(sc(me)-sc(op))
        if res:
          x['form']=f"{sum(r>0 for r in res)}-{sum(r<0 for r in res)}"+(f"-{sum(r==0 for r in res)}" if any(r==0 for r in res) else '')+f" last {len(res)}, avg margin {sum(res)/len(res):+.1f}"
          x['margin']=sum(res)/len(res); x['n']=len(res)
      x['key_inj']=inj.get((g['sport'],t['name']),[])
      c['sides'][side]=x
    w=wxs.get(g['name']); c['wx']=w
    c['postpone']=bool(re.search(r'postpon|delay|suspend|cancel',g.get('status') or '',re.I))
    ctx[g['id']]=c
  return ctx
def adjust(L,g,c,main,firstodds,imp):
  """returns (delta_prob, [reasons]). Deltas are modest and capped to [-6,+2] pts; market already prices most of this."""
  if not c: return 0,['research: game started or no data']
  d=0; R=[]; sp=g['sport']; k=L['kind']; side=L.get('side') if L.get('side') in('home','away') else None
  S=c['sides']; opp={'home':'away','away':'home'}.get(side)
  if side:
    me,op=S.get(side,{}),S.get(opp,{})
    if me.get('rest_days') is not None and op.get('rest_days') is not None:
      R.append(f"rest {me['rest_days']}d vs {op['rest_days']}d")
      if me.get('b2b') and not op.get('b2b'): d-=1.5; R.append('we are on a back-to-back (-1.5)')
      elif op.get('b2b') and not me.get('b2b'): d+=1.0; R.append('opponent on back-to-back (+1.0)')
      elif sp in('nfl','college-football') and me['rest_days']-op['rest_days']>=3: d+=0.5; R.append('rest edge (+0.5)')
    if me.get('travel_mi') is not None: R.append(f"travel {me['travel_mi']} mi since last game")
    if me.get('travel_mi',0)>1500 and me.get('rest_days',9)<2.5: d-=0.5; R.append('long trip, short rest (-0.5)')
    if me.get('form') or op.get('form'): R.append(f"form {me.get('form','?')} vs {op.get('form','?')}")
    if me.get('n',0)>=5 and op.get('n',0)>=5:
      f=max(-1,min(1,(me['margin']-op['margin'])*(0.08 if sp in('nba','nfl','college-football') else 0.5)))
      if abs(f)>=0.3: d+=f; R.append(f"form edge ({f:+.1f})")
    if me.get('split'): R.append(f"{side} record {me['split']}")
    if me.get('key_inj'):
      q=any(re.search('Question|Doubt|Day',s) for s in me['key_inj']); d-=2.5 if q else 1.0; R.append(f"our key player: {'; '.join(me['key_inj'][:2])} ({'-2.5' if q else '-1.0'})")
    if op.get('key_inj'): R.append(f"opponent key player: {'; '.join(op['key_inj'][:2])}")
  if k=='total':
    ki=[s for x in S.values() for s in x.get('key_inj',[])]
    if ki and L['ou']=='over': d-=1.0; R.append('key QB/G injury hurts Over (-1.0)')
    w=c.get('wx')
    if w and sp in OUTDOOR_WX and not g.get('indoor'):
      wind,rain=w.get('wind') or 0,w.get('rain') or 0
      if wind>=15 or rain>=60:
        e=1.5 if L['ou']=='under' else -2.0; d+=e; R.append(f"weather wind {wind} mph / rain {rain}% ({e:+.1f})")
      else: R.append(f"weather fine (wind {wind} mph, rain {rain}%)")
  # consensus vs ESPN/DraftKings line
  if k=='spread' and side and main.get('hs') is not None and g.get('espn_hs') is not None:
    diff=(main['hs']-g['espn_hs'])*(1 if side=='home' else -1)  # >0: DK rates our side better than FD
    if abs(diff)>=0.5: e=0.5 if diff>0 else -0.5; d+=e; R.append(f"DraftKings line {g['espn_hs']:+g} vs FanDuel {main['hs']:+g} ({e:+.1f})")
  if k=='total' and main.get('tot') and g.get('total'):
    diff=(float(g['total'])-main['tot'])*(1 if L['ou']=='over' else -1)
    if abs(diff)>=0.5: e=0.5 if diff>0 else -0.5; d+=e; R.append(f"DraftKings total {g['total']} vs FanDuel {main['tot']} ({e:+.1f})")
  # line movement on this exact FanDuel selection
  f0=firstodds.get(L['id'])
  if f0 is not None and f0!=L['odds']:
    mv=imp(L['odds'])-imp(f0)
    if mv<=-0.02: d-=1.0; R.append(f"FanDuel price moved against us {f0:+d} -> {L['odds']:+d} (-1.0)")
    elif mv>=0.02: d+=0.5; R.append(f"FanDuel price moved our way {f0:+d} -> {L['odds']:+d} (+0.5)")
  # volatility of low-scoring sports on lines (one goal/run decides it)
  if sp in LOWSCORE and k in('spread','total','dnb','dc'):
    d-=1.5; R.append('low-scoring sport, one goal decides line (-1.5 volatility)')
  if c.get('postpone'): d-=3; R.append('postponement/delay risk (-3)')
  d=max(-6,min(2,d)); return d/100,R
