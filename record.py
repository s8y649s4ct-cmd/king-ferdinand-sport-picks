"""Enhanced Track record -> record.json. Every graded ticket (ladder, Best Parlay/green, lottery, 2-leg) with W/L, each leg's result
and final-score margin, a plain-English reason, and a 'What we learned / changed' note tied to improvements.md reviews. Times in Eastern."""
import json,re,datetime,urllib.request,os
from zoneinfo import ZoneInfo
ET=ZoneInfo('America/New_York')
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
SPORTS={'nfl':'football','college-football':'football','nba':'basketball','nhl':'hockey','mlb':'baseball','eng.1':'soccer','esp.1':'soccer','ita.1':'soccer','ger.1':'soccer','fra.1':'soccer','usa.1':'soccer','wnba':'basketball'}
os.makedirs('.cache',exist_ok=True); SC=load('.cache/scores.json',{}); DONE=set(SC.get('_days',[]))
def fetch_day(lg,day):
  k=f'{lg}|{day}'
  if k in DONE: return
  try: d=json.load(urllib.request.urlopen(urllib.request.Request(f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/scoreboard?dates={day.replace("-","")}&limit=300',headers={'User-Agent':'Mozilla/5.0'}),timeout=15))
  except Exception as e: print('score fetch fail',k,e); return
  allpost=True
  for e in d.get('events',[]):
    c=e['competitions'][0]; st=e['status']['type']['state']
    if st!='post': allpost=False; continue
    t={x['homeAway']:x for x in c['competitors']}
    SC[e['id']]={'h':float(t['home'].get('score') or 0),'a':float(t['away'].get('score') or 0),'home':t['home']['team']['displayName'],'away':t['away']['team']['displayName'],'status':e['status']['type']['shortDetail']}
  if allpost: DONE.add(k)
def et(s):
  if not s: return None
  s=s.replace(' UTC','+00:00').replace('Z','+00:00')
  try: d=datetime.datetime.fromisoformat(s if 'T' in s or '+' in s else s)
  except Exception: return s
  if d.tzinfo is None: d=d.replace(tzinfo=datetime.timezone.utc)
  return d.astimezone(ET).strftime('%a %b %-d, %-I:%M %p ET')
hist=load('picks.history.json',[]); two=load('twoleg.history.json',[]); SH=load('shadow.json',{'legs':{}})['legs']
need={(l['sport'],x['date']) for x in hist+two if x.get('result') for l in (x.get('legs_detail') or x.get('legs')) if l.get('result') in('win','loss') and l['event'] not in SC and l['sport'] in SPORTS}
for sp,d in sorted(need):
  fetch_day(sp,d); fetch_day(sp,(datetime.date.fromisoformat(d)+datetime.timedelta(days=1)).isoformat())
SC['_days']=sorted(DONE); json.dump(SC,open('.cache/scores.json','w'))
BLOW={'nba':20,'college-football':21,'nfl':17,'nhl':3,'mlb':5}
def margin(l):
  s=SC.get(l.get('event')); k=l.get('kind') or (SH.get(l['id']) or {}).get('kind')
  if not s or not k: return None,None
  h,a=s['h'],s['a']; side=l.get('side') or (SH.get(l['id']) or {}).get('side'); line=l.get('line') if l.get('line') is not None else (SH.get(l['id']) or {}).get('line')
  my,op=(h,a) if side=='home' else (a,h); fin=f"{s['away']} {a:g} @ {s['home']} {h:g}"
  try:
    if k=='spread': return my+line-op,fin
    if k=='total': return (h+a-line)*(1 if (l.get('ou') or (SH.get(l['id']) or {}).get('ou'))=='over' else -1),fin
    if k in('ml','ml3','dnb','dc'): return my-op,fin
  except Exception: pass
  return None,fin
def tag(l,m):
  s=SC.get(l.get('event')) or {}; k=l.get('kind'); sp=l['sport']; t=[]
  if s and abs(s['h']-s['a'])>=BLOW.get(sp,99): t.append('blowout')
  if k=='total' and m is not None and m<0 and l.get('ou')=='under': t.append('shootout')
  if l.get('close_odds') and l.get('odds') and l['close_odds']!=l['odds']:
    imp=lambda o:100/(o+100) if o>0 else -o/(-o+100)
    if imp(l['close_odds'])<imp(l['odds'])-0.02: t.append('line moved against us')
  return t
LESSON={'nhl':'NHL legs rated 85%+ now capped at 80% (Oct 26-27 reviews) so hockey ranks below proven legs.',
 'blowout':'Blowouts on alt spreads: ladder now uses only each game\'s top leg or alts within 2 pts of it, never the opposite side (Oct 26 review); NBA/CFB haircuts were backtested 3 times and rejected because they cut wins out of sample.',
 'shootout':'Shootout broke an Under: CFB/NBA alt totals were found ~4-6 pts overrated (Oct 31 review); the 2-leg bar now requires a 92%+ calibrated leg, which today excludes these.',
 'same':'Same-game stacking sank several legs at once: 2-Leg board allows one leg per game; ladder same-game penalty is being retested once 10+ graded days exist.',
 'line moved against us':'Late line move against the pick: closing-line value is tracked per leg and feeds the v2 shadow check.',
 'props':'Rebound props get a haircut and rebound unders are excluded; NBA 3s/rebounds capped at FanDuel no-vig + 3 pts (Oct 30).',
 'lottery':'25-leg lottery now ranks legs by chance + 0.25 x edge instead of pure edge (Oct 30 review: 61% -> 84% per-leg in backtest).',
 'win':'Win confirms the rule set used that day; kept unchanged (only changes that raise backtested win rate are adopted).'}
# reviews from improvements.md
REV=[]
for m in re.finditer(r'^## (\d{4}-\d{2}-\d{2})([^\n]*)\n(.*?)(?=^## |\Z)',open('improvements.md').read(),re.S|re.M):
  body=m.group(3); ln=body.split('\n'); i=next((j for j,x in enumerate(ln) if 'Changes' in x),None)
  if i is None: txt=' '.join(x for x in ln if x.strip())
  else:
    txt=ln[i].split(':',1)[1] if ':' in ln[i] else ''
    for x in ln[i+1:]:
      if x.startswith('- '): txt+=' '+x[2:]
      elif x.strip(): break
  txt=txt.strip().replace('**','').strip(': ')
  REV.append({'date':m.group(1),'title':m.group(1)+m.group(2),'changes':re.sub(r'\s+',' ',txt)[:420]})
def review_after(d): return next((r for r in REV if r['date']>d and 'daily review' in r['title']),None)
def build(x,typ):
  legs=x.get('legs_detail') or x.get('legs'); out=[]; miss=[]
  for l in legs:
    m,fin=margin(l) if l.get('result') in('win','loss') else (None,None); tg=tag(l,m) if l.get('result')=='loss' else []
    est=l.get('calibrated') or l.get('prob') or l.get('model')
    out.append({'pick':l.get('pick'),'game':l.get('game'),'sport':l['sport'],'odds':l.get('odds'),'est':round(est,3) if est else None,'result':l.get('result'),'final':fin,'margin':m,'tags':tg})
    if l.get('result')=='loss': miss.append(out[-1])
  res=x['result']
  if res=='win':
    cl=min([o for o in out if o['margin'] is not None],key=lambda o:o['margin'],default=None)
    reason=f"All {len(out)} legs hit."+(f" Closest call: {cl['pick']} covered by {cl['margin']:g}." if cl else '')
  else:
    ev=[l.get('event') for l in legs if l.get('result')=='loss']; same=len(ev)!=len(set(ev))
    parts=[f"{o['pick']} ({o['game']}, rated {o['est']*100:.0f}%)"+(f" missed by {abs(o['margin']):g}" if o['margin'] is not None else '')+(f" [{', '.join(o['tags'])}]" if o['tags'] else '')+(f"; final {o['final']}" if o['final'] else '') for o in miss]
    reason=f"{len(miss)} of {len(out)} legs missed: "+'; '.join(parts[:6])+(f"; +{len(parts)-6} more" if len(parts)>6 else '')+('. Several misses came from the same game (stacked risk).' if same else '.')
  les=[]
  if res=='loss':
    tags={t for o in miss for t in o['tags']}
    if any(o['sport']=='nhl' for o in miss): les.append(LESSON['nhl'])
    for t in ('blowout','shootout','line moved against us'):
      if t in tags: les.append(LESSON[t])
    if len([l.get('event') for l in legs if l.get('result')=='loss'])!=len({l.get('event') for l in legs if l.get('result')=='loss'}): les.append(LESSON['same'])
    if typ=='lottery': les.append(LESSON['lottery'])
    if not les: les.append(f"Upset of a {miss[0]['est']*100:.0f}% leg; no pattern on its own, it feeds the per-sport calibration the 2-Leg bar uses." if miss and miss[0]['est'] else 'Feeds calibration.')
  else: les.append(LESSON['win'])
  rv=review_after(x['date'])
  return {'id':x['id'],'date':x['date'],'type':typ,'label':x.get('label') or (f"{x['n']}-leg ladder" if typ=='ladder' else typ),'n':x['n'],'favorite':bool(x.get('favorite')),
    'est':round(x.get('est_raw') or x.get('est_prob') or x.get('joint') or 0,4),'payout_x':x.get('fd_payout_x'),'result':res,'logged_et':et(x.get('logged')),
    'reason':reason,'learned':les,'review':({'date':rv['date'],'title':rv['title'],'changes':rv['changes']} if rv else {'date':None,'title':'Next daily review (3 AM ET)','changes':'Pending.'}),'legs':out}
T=[build(x,'best' if x.get('type')=='best' else x.get('type') or 'ladder') for x in hist if x.get('result')]+[build(x,'twoleg') for x in two if x.get('result')]
T.sort(key=lambda t:(t['date'],t['type'],t['n']),reverse=True)
def rec(xs):
  w=sum(t['result']=='win' for t in xs); return {'won':w,'lost':len(xs)-w,'win_pct':round(w/len(xs),3) if xs else None}
by={k:rec([t for t in T if t['type']==k]) for k in ('ladder','best','lottery','twoleg')}
by['green']=rec([t for t in T if t['favorite']])
byday={}
for t in T: byday.setdefault(t['date'],[]).append(t)
json.dump({'updated_et':datetime.datetime.now(ET).strftime('%a %b %-d, %-I:%M %p ET'),'overall':rec(T),'by_type':by,
  'by_day':{d:rec(v) for d,v in byday.items()},'reviews':REV[::-1],'tickets':T,'pending':sum(1 for x in hist+two if not x.get('result'))},open('record.json','w'))
print('record tickets',len(T),by)
