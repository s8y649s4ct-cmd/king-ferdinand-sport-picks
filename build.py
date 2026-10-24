#!/usr/bin/env python3
"""Fetch fresh scores/odds/injuries/weather, build picks.json, log lines + history. Idempotent."""
import json,os,datetime,urllib.request,urllib.parse
UTC=datetime.timezone.utc; now=datetime.datetime.now(UTC); NOW=now.strftime('%Y-%m-%d %H:%M UTC')
cfg=json.load(open('legs.json')); notes=json.load(open('notes.json')); DATE=cfg['date']
SPORTS={'college-football':'football','nba':'basketball','nhl':'hockey','eng.1':'soccer','mlb':'baseball'}
def get(u):
  try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'kfsp'}),timeout=20))
  except Exception as e: print('fetch fail',u,e); return None
def imp(o):
  try: o=int(str(o).replace('+','')); return 100/(o+100) if o>0 else -o/(-o+100)
  except: return None
def load(f,d): return json.load(open(f)) if os.path.exists(f) else d
games=[]
for lg,sp in SPORTS.items():
  d=get(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/scoreboard?dates={DATE.replace("-","")}&limit=300') or {}
  for e in d.get('events',[]):
    c=e['competitions'][0]; o=((c.get('odds') or [{}])[0]) or {}; ml=o.get('moneyline') or {}
    teams={t['homeAway']:t for t in c['competitors']}
    g={'id':e['id'],'sport':lg,'name':e['name'],'start':e['date'],'state':e['status']['type']['state'],
       'status':e['status']['type']['shortDetail'],'venue':c.get('venue',{}).get('fullName'),
       'indoor':c.get('venue',{}).get('indoor'),'city':(c.get('venue',{}).get('address') or {}),
       'espn_wx':e.get('weather'),'line':o.get('details'),'total':o.get('overUnder'),'book':(o.get('provider') or {}).get('name'),
       'teams':{}}
    for side,t in teams.items():
      m=(ml.get(side) or {}); g['teams'][t['team']['displayName']]={'side':side,'score':t.get('score'),'winner':t.get('winner'),
        'ml_open':(m.get('open') or {}).get('odds'),'ml':(m.get('close') or {}).get('odds')}
    games.append(g)
print('games',len(games))
def find(sport,team):
  for g in games:
    if g['sport']==sport and team in g['teams']: return g
# legs: manual + auto CFB favourites from ESPN lines
legs=[dict(l) for l in cfg['legs']]; have={(l['sport'],l['team']) for l in legs}
for g in games:
  if g['sport']!='college-football': continue
  for tn,t in g['teams'].items():
    try: v=int(t['ml'])
    except: continue
    if v<=cfg['auto_ml_max'] and ('college-football',tn) not in have:
      legs.append({'id':'cfb-'+g['id'],'sport':'college-football','team':tn,'type':'ml','market':tn+' moneyline',
        'why':f"Auto: {g['book']} line {g['line']}, total {g['total']}.",'src':'https://www.espn.com/college-football/scoreboard'})
for l in legs:
  g=find(l['sport'],l['team']); l['game']=g['name'] if g else l['team']; l['event']=g['id'] if g else None
  l['status']=g['status'] if g else 'not found on ESPN'; l['state']=g['state'] if g else 'pre'
  t=g['teams'][l['team']] if g else {}
  if l.get('fd'): l['odds']=l['fd']+' (FanDuel, verified via FanDuel Research/aggregator)'; l['verified']=True
  else: l['odds']=(l.get('alt') or (f"{t.get('ml')} ({g['book']} via ESPN)" if t.get('ml') else 'n/a'))+' - check FanDuel'; l['verified']=False
  if 'prob' not in l and l['type']=='ml' and g:
    p=[imp(x['ml']) for x in g['teams'].values()]
    if None not in p: l['prob']=round(imp(t['ml'])/sum(p)*0.98,3)  # no-vig, shaded 2%
  l.setdefault('prob',0)
  if l['state']=='post' and l['type']=='ml' and t: l['result']='win' if t.get('winner') else 'loss'
pool=sorted([l for l in legs if l['prob']>=cfg['min_prob'] and l['state']=='pre'],key=lambda l:-l['prob'])
seen=set(); uniq=[]
for l in pool:  # max one leg per game -> avoids same-game correlation
  if l['event'] in seen: continue
  seen.add(l['event']); uniq.append(l)
pars=[]; p=1
for n in range(1,min(27,len(uniq))+1):
  p*=uniq[n-1]['prob']; dec=1
  pars.append({'id':f'{DATE}-{n}-'+'.'.join(sorted(x['id'] for x in uniq[:n])),'legs_count':n,'legs':[x['id'] for x in uniq[:n]],'est_prob':round(p,5),
   'fd_verified_legs':sum(x['verified'] for x in uniq[:n])})
cap=len(pars)
# injuries (ESPN, slate teams only) + manual verified notes
slate={tn for g in games for tn in g['teams']}; inj=[]
for lg in ['nba','nhl']:
  d=get(f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/injuries') or {}
  for t in d.get('injuries',[]):
    if t['displayName'] in slate:
      for i in t['injuries']: inj.append({'team':t['displayName'],'t':f"{i['athlete']['displayName']} - {i['status']}: {i.get('shortComment','')}",'src':'ESPN injuries feed'})
inj=notes['injuries']+inj
# weather for outdoor games
wxc=load('weather.cache.json',{}); wx=[]
for g in games:
  if g['indoor']: continue
  if g['espn_wx']: wx.append({'g':g['name'],'w':f"{g['espn_wx']['displayValue']}, {g['espn_wx']['temperature']}F",'src':'ESPN/AccuWeather'}); continue
  city=g['city'].get('city'); 
  if not city: continue
  if city not in wxc:
    r=get('https://geocoding-api.open-meteo.com/v1/search?count=1&name='+urllib.parse.quote(city))
    wxc[city]=(r or {}).get('results',[{}])[0] if r and r.get('results') else None
  loc=wxc[city]
  if not loc: wx.append({'g':g['name'],'w':'unavailable','src':'-'}); continue
  f=get(f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&hourly=temperature_2m,precipitation_probability,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC&forecast_days=2")
  try:
    h=g['start'][:13]+':00'; i=f['hourly']['time'].index(h)
    wx.append({'g':g['name'],'w':f"{f['hourly']['temperature_2m'][i]}F, wind {f['hourly']['wind_speed_10m'][i]} mph, rain {f['hourly']['precipitation_probability'][i]}%",'src':'open-meteo (kickoff hour)'})
  except Exception: wx.append({'g':g['name'],'w':'unavailable','src':'open-meteo'})
json.dump(wxc,open('weather.cache.json','w'))
# line history snapshot (one per refresh)
lh=load('lines.history.json',[]); lh.append({'at':NOW,'lines':{g['id']:{'name':g['name'],'line':g['line'],'total':g['total'],'ml':{k:v['ml'] for k,v in g['teams'].items()},'ml_open':{k:v['ml_open'] for k,v in g['teams'].items()}} for g in games}})
lh=lh[-500:]; json.dump(lh,open('lines.history.json','w'))
first=lh[0]['lines']; moves=[]
for g in games:
  for tn,t in g['teams'].items():
    o=t['ml_open'] or (first.get(g['id'],{}).get('ml',{}).get(tn))
    if o and t['ml'] and o!=t['ml']: moves.append({'g':g['name'],'team':tn,'open':o,'now':t['ml']})
out={'updated':NOW,'date':DATE,'legs':legs,'parlays':pars,'games':games,'injuries':inj,'weather':wx,'moves':moves,
 'note':f"{len(uniq)} legs pass the {int(cfg['min_prob']*100)}% bar with one leg per game, so the longest parlay here is {cap} legs (target 27)."}
json.dump(out,open('picks.json','w'),indent=1)
# history log: add new parlays once, grade legs when final
hist=load('picks.history.json',[]); ids={x['id'] for x in hist}; res={l['id']:l.get('result') for l in legs}
for x in pars:
  if x['id'] not in ids: hist.append(dict(x,logged=NOW,result=None))
for x in hist:
  if x['id'].startswith(DATE) and x.get('result') is None:
    r=[res.get(i) for i in x['legs']]
    if 'loss' in r: x['result']='loss'
    elif r and all(v=='win' for v in r): x['result']='win'
json.dump(hist,open('picks.history.json','w'),indent=1)
print('legs',len(legs),'pool',len(uniq),'parlays',cap,'moves',len(moves),'wx',len(wx),'inj',len(inj))
