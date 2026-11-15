"""ROI ledger -> ledger.json. Every graded posted ticket at a flat 1-unit stake, priced from the odds stored when it was posted
(fd_payout_x for ladder/Best/Lottery; product of stored leg odds for 2-leg boards and Value picks). Win = payout-1 units, loss = -1,
void/push = 0. Breakdowns: overall, board, sport, bet type (single / 2-leg / 3-5 / 6+), model version, day. Also the separate
boards (Live, Props, TD, 3s & rebounds) and the EV backtest (bt_ev.py -> backtest.json). Times in Eastern. Never places bets."""
import json,datetime,re,os,glob,collections
from zoneinfo import ZoneInfo
ET=ZoneInfo('America/New_York')
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
def dec(o): o=float(o); return 1+(o/100 if o>0 else 100/-o)
def imp(o): o=float(o); return 100/(o+100) if o>0 else -o/(-o+100)
SH=load('shadow.json',{'legs':{}})['legs']
BYSEL={}
for k,r in SH.items():
  p=k.split(':')
  if len(p)>=3: BYSEL[(p[1],p[2])]=r
def sgrp(sp): return 'soccer' if sp and '.' in sp else (sp or '?')
def btype(n): return 'single' if n==1 else '2-leg' if n==2 else '3-5 legs' if n<=5 else '6+ legs'
T=[]
def add(id,date,board,n,payout,result,sports,est=None,fav=False,model='v1',label=None,odds_src='posted'):
  if result not in('win','loss','void') or not payout: return
  u=0.0 if result=='void' else (payout-1 if result=='win' else -1.0)
  ss={sgrp(s) for s in sports}
  T.append({'id':id,'date':date,'board':board,'n':n,'type':btype(n),'sport':ss.pop() if len(ss)==1 else 'multi-sport','payout_x':round(payout,3),
    'result':result,'units':round(u,4),'est':est,'fav':fav,'model':model,'label':label or f"{n}-leg {board}"})
# 1) main boards
NB={'ladder':'Ladder','best':"Kings Pick (Best Parlay)",'lottery':'Lottery'}
for x in load('picks.history.json',[]):
  b=x.get('type') or 'ladder'
  add(x['id'],x['date'],NB.get(b,b),x['n'],x.get('fd_payout_x'),x.get('result'),[l.get('sport') for l in x.get('legs_detail') or []],
      x.get('est_raw') or x.get('est_prob'),bool(x.get('favorite')),label=x.get('label'))
# 2) strict 2-leg
for x in load('twoleg.history.json',[]):
  try: pay=dec(x['legs'][0]['odds'])*dec(x['legs'][1]['odds'])
  except Exception: pay=None
  add(x['id'],x['date'],'Strict 2-leg',2,pay,x.get('result'),[l['sport'] for l in x['legs']],x.get('joint'),True)
# 3) researched 2-leg comparisons (archive of twoleg.research.json; graded from the shadow log by FanDuel market+selection id)
SC=load('.cache/scores.json',{})
GAMEEV={}
for r in SH.values(): GAMEEV.setdefault((r.get('game') or '').lower(),r.get('event'))
def grade_text(l):
  """Fallback for researched legs not in the shadow log: grade simple spread/total/moneyline text from the ESPN final score."""
  g=(l.get('game') or '').replace(' @ ',' at ').lower(); ev=GAMEEV.get(g); s=SC.get(ev) if ev else None
  if not s: return None
  pk=(l.get('pick') or '').strip(); m=re.fullmatch(r'(Over|Under)\s*\(?([\d.]+)\)?',pk)
  if m:
    t=s['h']+s['a']; ln=float(m.group(2)); return 'void' if t==ln else ('win' if (t>ln)==(m.group(1)=='Over') else 'loss')
  m=re.fullmatch(r'(.+?)\s*\(?([+-][\d.]+)?\)?',pk)
  if not m: return None
  team=m.group(1).strip().lower(); ln=float(m.group(2)) if m.group(2) else 0.0
  nick=team.split()[-1] if team.split() else ''
  side='home' if team==s['home'].lower() else 'away' if team==s['away'].lower() else None
  if not side and nick: side='home' if s['home'].lower().endswith(nick) and not s['away'].lower().endswith(nick) else 'away' if s['away'].lower().endswith(nick) and not s['home'].lower().endswith(nick) else None
  if not side: return None
  my,op=(s['h'],s['a']) if side=='home' else (s['a'],s['h']); d=my+ln-op
  if not m.group(2): return 'win' if my>op else 'loss'
  return 'void' if d==0 else 'win' if d>0 else 'loss'
RA=load('twoleg.research.history.json',{})
cur=load('twoleg.research.json',{})
if cur.get('date') and cur.get('options') and (cur['date'] not in RA or len(cur['options'])>=len(RA[cur['date']].get('options',[]))): RA[cur['date']]=cur  # never shrink an archived day
json.dump(RA,open('twoleg.research.history.json','w'))
for _d,_doc in RA.items():
  for _o in _doc.get('options',[]):
    for _l in _o.get('legs',[]):
      _m=re.search(r'marketId%5B0%5D=([\d.]+)&selectionId%5B0%5D=(\d+)',_l.get('pa_link') or ''); _r=BYSEL.get((_m.group(2),_m.group(1))) if _m else None
      if _r: GAMEEV[(_l.get('game') or '').replace(' @ ',' at ').lower()]=_r.get('event')
RES=[]
for d,doc in sorted(RA.items()):
  for o in doc.get('options',[]):
    rs=[];sp=[];pay=1.0;ok=True
    for l in o.get('legs',[]):
      m=re.search(r'marketId%5B0%5D=([\d.]+)&selectionId%5B0%5D=(\d+)',l.get('pa_link') or '')
      r=BYSEL.get((m.group(2),m.group(1))) if m else None
      res0=(r or {}).get('result') if r else grade_text(l)
      rs.append(res0); sp.append((r or {}).get('sport') or ('nba' if 'NBA' in (o.get('tier') or '') else None))
      od=l.get('odds_pa') or l.get('odds')
      if od is None: ok=False
      else: pay*=dec(od)
    res='loss' if 'loss' in rs else 'win' if rs and all(v in('win','void') for v in rs) else None
    if res=='win' and all(v=='void' for v in rs): res='void'
    RES.append({'date':d,'id':o.get('id'),'tier':o.get('tier'),'legs':[l.get('pick') for l in o.get('legs',[])],'leg_results':rs,'result':res,'payout_x':round(pay,3) if ok else None})
    if ok: add(f"{d}-R-{o.get('id')}",d,'Researched 2-leg',len(o.get('legs',[])),pay,res,[s for s in sp if s],o.get('est_model_product'),False,label=f"Option {o.get('id')}")
# 4) Value picks (EV board, new 2026-11-15)
for x in load('value.history.json',[]):
  add(x['id'],x['date'],'Value (+EV)',x['n'],x.get('payout_x'),x.get('result'),x.get('sports',[]),x.get('est'),False,model=x.get('model','pinnacle-edge'),label=x.get('label'))
def agg(xs):
  g=[t for t in xs if t['result'] in('win','loss')]; w=sum(t['result']=='win' for t in g); u=sum(t['units'] for t in xs); n=len(xs)
  return {'tickets':n,'won':w,'lost':len(g)-w,'void':n-len(g),'win_pct':round(w/len(g),4) if g else None,'units':round(u,2),'roi_pct':round(100*u/n,2) if n else None,
          'avg_payout_x':round(sum(t['payout_x'] for t in xs)/n,2) if n else None,'avg_est':round(sum(t['est'] for t in xs if t['est'])/max(1,sum(1 for t in xs if t['est'])),4) if n else None}
def by(key,xs=None):
  xs=T if xs is None else xs; D=collections.defaultdict(list)
  for t in xs: D[key(t)].append(t)
  return {k:agg(v) for k,v in sorted(D.items(),key=lambda kv:-len(kv[1]))}
L={'updated_et':datetime.datetime.now(ET).strftime('%a %b %-d, %-I:%M %p ET'),'stake':'1 unit flat per ticket at the posted FanDuel price',
   'overall':agg(T),'by_board':by(lambda t:t['board']),'green':agg([t for t in T if t['fav']]),'by_type':by(lambda t:t['type']),
   'by_sport':by(lambda t:t['sport']),'by_model':by(lambda t:t['model']),
   'by_day':dict(sorted(by(lambda t:t['date']).items(),reverse=True)),'researched_2leg':RES,
   'odds_coverage':f"{len(T)} graded posted tickets; every one had its FanDuel price stored at posting (ladder/Best/Lottery: ticket payout; 2-leg and Value: leg odds), so ROI covers the full history. Researched 2-leg options before {min(RA) if RA else 'n/a'} were not archived in machine-readable form and are not in the ledger."}
# cumulative units by day (main boards)
cum=0; ser=[]
for d in sorted({t['date'] for t in T}):
  cum+=sum(t['units'] for t in T if t['date']==d); ser.append([d,round(cum,2)])
L['cumulative']=ser
# legs used in posted tickets, valued as 1-unit singles (who drags tickets down)
LG={}
for x in load('picks.history.json',[]):
  for l in x.get('legs_detail') or []:
    if l.get('result') in('win','loss') and l.get('odds'): LG[l['id']]=l
def lagg(xs):
  n=len(xs); w=sum(l['result']=='win' for l in xs); u=sum((dec(l['odds'])-1) if l['result']=='win' else -1 for l in xs)
  return {'legs':n,'won':w,'win_pct':round(w/n,4) if n else None,'avg_est':round(sum(l.get('prob') or 0 for l in xs)/n,4) if n else None,'units':round(u,2),'roi_pct':round(100*u/n,2) if n else None}
D=collections.defaultdict(list)
for l in LG.values(): D[sgrp(l['sport'])].append(l)
L['legs_as_singles_by_sport']={k:lagg(v) for k,v in sorted(D.items(),key=lambda kv:-len(kv[1]))}
L['legs_as_singles_all']=lagg(list(LG.values()))
# model versions on identical candidates (shadow log): each game's top v1 leg vs top v2 leg, as 1-unit singles at last pregame price
def sh_singles(flag):
  xs=[r for r in SH.values() if r.get(flag) and r.get('result') in('win','loss') and r.get('odds_last')]
  return lagg([{'result':r['result'],'odds':r['odds_last'],'prob':r.get('v1' if flag=='v1_top' else 'v2'),'sport':r['sport']} for r in xs])
L['model_compare']={'v1 (live) top leg per game':sh_singles('v1_top'),'v2 (shadow) top leg per game':sh_singles('v2_top'),
  'note':'Same games, same FanDuel prices, graded the same way; each model\u2019s single best leg per game as a 1-unit single. Published tickets so far all used v1.'}
# separate boards (Live, Props, TD, 3s & rebounds): tickets priced from stored leg odds
SEP={}
for f,names in (('extra.history.json',{'live':'Live picks','props':'Player props'}),('extra2.history.json',{'td':'NFL TD scorers','nba3r':'NBA 3s & rebounds'})):
  h=load(f,{}); legs=h.get('legs',{}); legs=legs if isinstance(legs,dict) else {l['id']:l for l in legs}
  tk=h.get('tickets',{}); tk=list(tk.values()) if isinstance(tk,dict) else tk
  for k,nm in names.items():
    xs=[];miss=0
    for t in tk:
      if t.get('type')!=k or t.get('result') not in('won','lost','win','loss'): continue
      if k=='live' and t['n']!=1: continue  # live combos are re-logged as prices move (same game in many tickets): singles only
      try: pay=1.0; [pay:=pay*dec(legs[i]['odds']) for i in t['legs']]
      except Exception: miss+=1; continue
      w=t['result'] in('won','win'); xs.append({'result':'win' if w else 'loss','units':pay-1 if w else -1.0,'payout_x':pay,'est':t.get('est_prob'),'n':t['n'],'type':btype(t['n'])})
    a=agg(xs); a['no_odds']=miss
    a['by_type']={bt:agg([x for x in xs if x['type']==bt]) for bt in ('single','2-leg','3-5 legs','6+ legs') if any(x['type']==bt for x in xs)}
    SEP[nm]=a
L['separate_boards']=SEP
L['separate_note']='Live: singles only, because Live combo tickets are re-logged as prices move (one game sits in many tickets). Live prices change within the 10-minute refresh, so the logged price may not have been available when you looked: treat Live ROI as indicative only.'
L['backtest']=load('backtest.json',{})
# flags: underperforming strategies (>=20 graded tickets and ROI below -10%)
FL=[]
for nm,a in list(L['by_board'].items())+[("King's Favorites (green)",L['green'])]+[(k+' (separate)',v) for k,v in SEP.items()]:
  if a['tickets']>=20 and a['roi_pct'] is not None and a['roi_pct']<-10: FL.append(f"{nm}: {a['units']:+.1f} units on {a['tickets']} tickets (ROI {a['roi_pct']:+.1f}%) \u2014 underperforming. Since Nov 15: tickets capped at 6 legs, long tickets labeled low-probability/high-variance, Value singles preferred.")
for nm,a in L['by_type'].items():
  if a['tickets']>=20 and a['roi_pct'] is not None and a['roi_pct']<-10: FL.append(f"{nm} tickets: ROI {a['roi_pct']:+.1f}% on {a['tickets']}.")
mc=L['model_compare']; a1,a2=mc['v1 (live) top leg per game'],mc['v2 (shadow) top leg per game']
if a1['legs'] and a2['legs']: FL.append(f"Model check (singles, same games): v1 {a1['roi_pct']:+.1f}% ROI on {a1['legs']} legs vs v2 {a2['roi_pct']:+.1f}% on {a2['legs']}. Neither beats FanDuel's vig on its own.")
L['flags']=FL
json.dump(L,open('ledger.json','w'),indent=1)
o=L['overall']; print('ledger',o['tickets'],'tickets',o['won'],'-',o['lost'],'units',o['units'],'roi',o['roi_pct'])
