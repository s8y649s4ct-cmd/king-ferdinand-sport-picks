"""EV layer (added 2026-11-15, user request t60u): positive expected value first, honest numbers on every pick and ticket.
annotate(out,...) is called by build.py just before picks.json is written; any failure leaves the board as it was.
  Per leg: break-even chance (FanDuel price incl. vig), FanDuel no-vig fair chance (both sides of the market when FanDuel
  lists them), model estimate, Pinnacle no-vig fair chance where Pinnacle prices the game, edge in points, EV per 1 unit,
  confidence, and a short research 'checks' line (injuries, weather, rest/back-to-back, travel, form, line movement).
  Per ticket: estimated hit chance vs break-even, edge, EV, confidence and the graded ROI of that ticket size so far.
  Value board (out['value']): singles where Pinnacle's no-vig fair chance beats FanDuel's break-even by >= the threshold
  chosen out-of-sample in backtest.json (bt_ev.py). One leg per game. Logged to value.history.json, locked at kickoff, graded
  from shadow.json. Nothing here places a bet."""
import json,math,datetime,re
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
def imp(o): o=float(o); return 100/(o+100) if o>0 else -o/(-o+100)
def dec(o): o=float(o); return 1+(o/100 if o>0 else 100/-o)
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
DEFAULT_TH=0.06
def _inj(get,SPORTS):
  """team -> (out, questionable) counts from ESPN injury feeds (display only: FanDuel/Pinnacle prices already include known news)."""
  T={}
  for lg in ('nba','nhl','nfl','college-football'):
    try:
      for t in (get(f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/injuries',ttl=1800) or {}).get('injuries',[]):
        o=q=0; nm=[]
        for i in t.get('injuries',[]):
          s=(i.get('status') or '').lower()
          if s in('out','injured reserve','suspension'): o+=1
          elif s in('questionable','doubtful','day-to-day'): q+=1; nm.append((i.get('athlete') or {}).get('displayName',''))
        T[t.get('displayName')]=(o,q,nm[:2])
    except Exception: pass
  return T
def checks(L,g,c,first,INJ):
  """short research line + priced-in flag"""
  out=[]; pin=False
  if g:
    ab=[]
    for sd in ('away','home'):
      t=g['teams'].get(sd,{}); x=INJ.get(t.get('name'))
      if x: ab.append(f"{t.get('abbr') or t.get('name')} {x[0]} out/{x[1]} Q"+(f" ({', '.join(x[2])})" if x[2] else ''))
    out.append('Inj: '+('; '.join(ab) if ab else 'none listed (ESPN)'))
    if g.get('indoor'): out.append('Wx: indoor')
    elif c and c.get('wx'): w=c['wx']; out.append(f"Wx: wind {w.get('wind')} mph, rain {w.get('rain')}%"+(' ⚠️' if (w.get('wind') or 0)>=15 or (w.get('rain') or 0)>=60 else ''))
    elif g['sport'] in('nfl','college-football') or '.' in g['sport']: out.append('Wx: no forecast found')
  if c:
    S=c.get('sides',{}); rr=[]
    for sd in ('away','home'):
      x=S.get(sd,{})
      if x.get('rest_days') is not None: rr.append(f"{sd} {x['rest_days']:g}d"+(' B2B' if x.get('b2b') else '')+(f", {x['travel_mi']} mi" if x.get('travel_mi') else ''))
    if rr: out.append('Rest/travel: '+'; '.join(rr))
    fm=[f"{sd} {S[sd]['form'].split(',')[0]}" for sd in ('away','home') if S.get(sd,{}).get('form')]
    if fm: out.append('Form: '+'; '.join(fm))
    if c.get('postpone'): out.append('⚠️ postponement/delay risk')
  f0=first.get(L['id'])
  if f0 is not None and f0!=L['odds']:
    mv=imp(L['odds'])-imp(f0)
    out.append(f"Line: {f0:+d} → {L['odds']:+d}"+(' (moved toward this pick: news likely already priced in)' if mv>=0.02 else ' (moved against this pick)' if mv<=-0.02 else ''))
    pin=abs(mv)>=0.02
  else: out.append('Line: no FanDuel move today')
  return ' · '.join(out),pin
def conf_leg(pe,how):
  """Backtest edge bands (bt_ev.py edge_bands): bigger Pinnacle edge = better graded ROI. Extrapolated alt lines drop one level."""
  if pe is None: return 'Low'
  lv=2 if pe>=0.10 else 1 if pe>=0.08 else 0
  if how and 'extrapolated' in how: lv=max(0,lv-1)
  return ('Low','Med','High')[lv]
def annotate(out,cands,G,CTX,FIRST,DATE,NOW,get,SPORTS,fdlink,cfg):
  bt=load('backtest.json',{}); TH=bt.get('value_threshold') or DEFAULT_TH
  led=load('ledger.json',{}); BT=(led.get('by_type') or {})
  INJ=_inj(get,SPORTS); now=datetime.datetime.now(datetime.timezone.utc)
  def legfields(L):
    be=imp(L['odds']); nv=L.get('fd_nv',L.get('fd_prob')); sp=L.get('sharp_prob'); how=(L.get('v2_src') or '').replace('Pinnacle: ','')
    L['be']=round(be,4); L['fd_nv']=round(nv,4) if nv else None
    L['edge_be']=round(L['prob']-be,4); L['edge_nv']=round(L['prob']-nv,4) if nv else None; L['ev']=round(L['prob']*dec(L['odds'])-1,4)
    L['pin_edge']=round(sp-be,4) if sp is not None else None; L['pin_how']=how if sp is not None else None
    L['conf']=conf_leg(L['pin_edge'],how) if (sp is not None and sp-be>=TH) else 'Low'
    g=G.get(L['event']); L['checks'],L['priced_in']=checks(L,g,CTX.get(L['event']),FIRST,INJ)
  for L in list(out['legs'].values()):
    try: legfields(L)
    except Exception as e: print('ev leg fail',L.get('id'),e)
  def bt_note(n):
    k='single' if n==1 else '2-leg' if n==2 else '3-5 legs' if n<=5 else '6+ legs'; a=BT.get(k) or {}
    return f"Posted {k} tickets so far: {a.get('won',0)}-{a.get('lost',0)}, {a.get('units',0):+.1f} units ({a.get('roi_pct') or 0:+.1f}% ROI)" if a else None
  def tick(p,legs):
    if not p or not legs: return
    est=p.get('est_raw') or p['est_prob']; pay=p['fd_payout_x']; be=1/pay if pay else None
    nv=math.prod(l.get('fd_nv') or l.get('fd_prob') or imp(l['odds']) for l in legs)
    pins=[l.get('sharp_prob') for l in legs]
    p['be']=round(be,5) if be else None; p['mkt_nv']=round(nv,5); p['edge_be']=round(est-be,5) if be else None
    p['ev_unit']=round(est*pay-1,3) if pay else None
    p['pin_joint']=round(math.prod(pins),5) if all(x is not None for x in pins) else None
    p['pin_ev']=round(p['pin_joint']*pay-1,3) if p['pin_joint'] is not None and pay else None
    allv=all((l.get('pin_edge') or -1)>=TH for l in legs)
    p['conf']='Med' if allv and p['n']<=2 else 'Low'
    p['tier']='short' if p['n']<=3 else 'long'
    p['bt_note']=bt_note(p['n'])
  for p in out.get('parlays') or []: tick(p,[out['legs'].get(i) for i in p['legs'] if out['legs'].get(i)])
  for p in out.get('lottery') or []: tick(p,[out['legs'].get(i) for i in p['legs'] if out['legs'].get(i)])
  if out.get('best'): tick(out['best'],[out['legs'].get(i) for i in out['best']['legs'] if out['legs'].get(i)])
  f=out.get('feature')
  if f and f.get('fd_payout_x'):
    fl=[out['legs'].get(x['id']) for x in f.get('legs',[])]
    if all(fl): tick(f,fl)
  # Value singles
  pre=[L for L in cands if G[L['event']]['state']=='pre' and L.get('sharp_prob') is not None and L.get('kind')!='prop' and ts(L['start'])>now]
  best={}
  for L in pre:
    pe=L['sharp_prob']-imp(L['odds'])
    if pe<TH: continue
    if L['event'] not in best or pe>best[L['event']][0]: best[L['event']]=(pe,L)
  V=[]
  for pe,L in sorted(best.values(),key=lambda t:-t[0]):
    L=dict(L)
    try: legfields(L)
    except Exception as e: print('ev value leg fail',e); continue
    L['fd_link']=fdlink([L]); L['est']=L['sharp_prob']
    L['ev_pin']=round(L['sharp_prob']*dec(L['odds'])-1,4)
    V.append({k:L.get(k) for k in ('id','event','sport','game','start','pick','market','kind','odds','be','fd_nv','prob','sharp_prob','pin_how','pin_edge','edge_nv','ev_pin','conf','checks','priced_in','fd_link')})
  out['value']=V
  q=bt.get('pinnacle',{}).get('grid',[]); row=next((r for r in q if abs(r['min_edge']-TH)<1e-9),{})
  out['value_rule']={'threshold':TH,'train':row.get('train'),'test':row.get('test'),'split':bt.get('split_date'),
    'text':f"A single is listed only when Pinnacle's no-vig fair chance beats FanDuel's break-even chance (the price including vig) by at least {TH*100:.0f} points. The threshold was picked on the older half of graded legs and checked on the newer half (backtest.json). Props are excluded (no Pinnacle price). Zero picks is a normal day."}
  # history: add/refresh while pregame and still qualifying; drop unlocked ones that stop qualifying; lock at kickoff; grade from shadow
  H={x['id']:x for x in load('value.history.json',[])}
  cur={f"{DATE}-V-{v['id']}":v for v in V}
  for k in [k for k,x in H.items() if x['date']==DATE and not x.get('locked') and k not in cur]: H.pop(k)
  for k,v in cur.items():
    if k in H and H[k].get('locked'): continue
    H[k]={'id':k,'date':DATE,'n':1,'label':v['pick'],'leg_id':v['id'],'game':v['game'],'sports':[v['sport']],'start':v['start'],'odds':v['odds'],'payout_x':round(dec(v['odds']),4),
          'est':v['sharp_prob'],'be':v['be'],'pin_edge':v['pin_edge'],'conf':v['conf'],'model':f"pinnacle-edge>={TH*100:.0f}",'logged':NOW,'locked':False,'result':None}
  SH=load('shadow.json',{'legs':{}})['legs']
  for x in H.values():
    if ts(x['start'])<=now: x['locked']=True
    if x.get('result') is None and x.get('locked'): x['result']=(SH.get(x['leg_id']) or {}).get('result')
  hist=sorted(H.values(),key=lambda x:(x['date'],x['id']),reverse=True)
  json.dump(hist,open('value.history.json','w'),indent=1)
  g=[x for x in hist if x['result'] in('win','loss')]; w=sum(x['result']=='win' for x in g); u=sum((x['payout_x']-1) if x['result']=='win' else -1 for x in g)
  out['value_record']={'won':w,'lost':len(g)-w,'pending':sum(1 for x in hist if not x['result']),'units':round(u,2),'roi_pct':round(100*u/len(g),1) if g else None}
  print('value picks',len(V),'threshold',TH,'record',out['value_record'])
