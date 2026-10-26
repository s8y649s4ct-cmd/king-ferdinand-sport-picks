#!/usr/bin/env python3
"""Maryland link map. FanDuel MD uses its own market IDs (724.x) for the same events/selections
as PA (742.x). Builds md.json {pa_market_id: md_market_id} for every market in a Bet link, matching
by FD eventId + marketType + marketName + same selectionId and handicap. Picks are untouched."""
import json,os,re,glob,time,urllib.request
from concurrent.futures import ThreadPoolExecutor
K='FhMFpcPWXMeyZxOx'; MD='https://sbapi.md.sportsbook.fanduel.com/api/'
need=set()
def walk(o):
  if isinstance(o,dict):
    for k,v in o.items():
      if isinstance(v,str) and 'addToBetslip' in v: need.update(re.findall(r'marketId%5B\d+%5D=([\d.]+)',v))
      else: walk(v)
  elif isinstance(o,list):
    for v in o: walk(v)
for f in ['picks.json','extra.json','extra2.json']:
  try: walk(json.load(open(f)))
  except Exception as e: print('md: skip',f,e)
# PA/NJ market info from the scripts' fresh caches
info={}; evtabs={}
for cf in glob.glob('.cache/*sportsbook_fanduel*'):
  if time.time()-os.path.getmtime(cf)>7200: continue
  try: d=json.load(open(cf))
  except Exception: continue
  tab=re.search(r'_tab_(\w+)$',cf)
  for m in ((d.get('attachments') or {}).get('markets') or {}).values():
    if m.get('marketId') in need:
      info[m['marketId']]=m; evtabs.setdefault(m['eventId'],set()).add(tab.group(1) if tab else 'popular')
def get(u):
  try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=15))
  except Exception as e: print('md fetch fail',u[-60:],e); return {}
# live markets aren't cached: look them up in the PA/MD in-play feeds by eventId later
missing=[m for m in need if m not in info]
if missing:
  for et in (1,2,4,7522,6423,7511,7524):
    for m in ((get(f'https://sbapi.pa.sportsbook.fanduel.com/api/in-play?_ak={K}&eventTypeId={et}').get('attachments') or {}).get('markets') or {}).values():
      if m.get('marketId') in need and m['marketId'] not in info:
        info[m['marketId']]=m; evtabs.setdefault(m['eventId'],set()).add('popular')
jobs=[(e,t) for e,ts in evtabs.items() for t in ts]
with ThreadPoolExecutor(12) as ex:
  res=list(ex.map(lambda j:get(f'{MD}event-page?_ak={K}&eventId={j[0]}&tab={j[1]}'),jobs))
mdm={}
for d in res:
  for m in ((d.get('attachments') or {}).get('markets') or {}).values():
    mdm.setdefault((m['eventId'],m.get('marketType'),m.get('marketName')),[]).append(m)
sig=lambda m:{(r['selectionId'],r.get('handicap',0)) for r in m.get('runners',[])}
out={}
for pid,m in info.items():
  for c in mdm.get((m['eventId'],m.get('marketType'),m.get('marketName')),[]):
    if sig(m)&sig(c) and c.get('marketStatus','OPEN')=='OPEN': out[pid]=c['marketId']; break
json.dump({'updated':time.strftime('%Y-%m-%d %H:%M UTC',time.gmtime()),'map':out,'needed':len(need),'matched':len(out)},open('md.json','w'))
print(f'md.py: {len(out)}/{len(need)} markets mapped to FanDuel MD ({len(jobs)} MD fetches)')
