"""Hard odds rule (user, 2026-11-15 10:13 AM ET): nothing published may be priced from -1000 to -40000.
Every leg must be priced -950 .. +1,000,000 (American) and every ticket's combined parlay odds must be -950 .. +1,000,000.
Used by build.py, extra.py, extra2.py, twoleg.py at selection time, and by update.sh (python3 oddsrule.py --enforce)
as a last check over every published board file before publish.sh. History/record files are past graded tickets and are
left as they were posted (they are the record, not current picks)."""
import json,sys
LEG_MIN=-950; LEG_MAX=1000000; TICKET_MIN=-950; TICKET_MAX=1000000
def dec(o): o=float(o); return 1+(o/100 if o>0 else 100/-o)
def american(d):
  d=float(d)
  if d<=1: return None
  return round((d-1)*100) if d>=2 else round(-100/(d-1))
def leg_ok(o):
  try: o=float(o)
  except Exception: return False
  return LEG_MIN<=o<=LEG_MAX
def ticket_ok_dec(d):
  a=american(d) if d else None
  return a is not None and TICKET_MIN<=a<=TICKET_MAX
def ticket_ok(odds):
  odds=list(odds)
  if not odds or not all(leg_ok(o) for o in odds): return False
  d=1.0
  for o in odds: d*=dec(o)
  return ticket_ok_dec(d)
def _odds(L): return L.get('odds') if L.get('odds') is not None else L.get('odds_pa')
def scrub_section(sec,label='board'):
  """sec = {'legs':{id:leg}, 'parlays':[{'legs':[ids or leg dicts], 'fd_payout_x':..}]}. Returns (legs_removed, tickets_removed)."""
  if not isinstance(sec,dict): return 0,0
  legs=sec.get('legs')
  bad=set(); nl=0
  if isinstance(legs,dict):
    for k,L in list(legs.items()):
      if not leg_ok(_odds(L)): bad.add(k); legs.pop(k); nl+=1
  nt=0
  for key in ('parlays','lottery','board'):
    ts=sec.get(key)
    if not isinstance(ts,list): continue
    keep=[]
    for t in ts:
      ids=t.get('legs') or []
      lo=[]
      ok=True
      for x in ids:
        if isinstance(x,dict): lo.append(_odds(x))
        elif x in bad: ok=False
        elif isinstance(legs,dict) and x in legs: lo.append(_odds(legs[x]))
      if ok and lo and not ticket_ok(lo): ok=False
      if ok and t.get('fd_payout_x') and not ticket_ok_dec(t['fd_payout_x']): ok=False
      if ok: keep.append(t)
      else: nt+=1
    sec[key]=keep
  return nl,nt
def scrub_picks(out):
  """picks.json: legs dict, ladder parlays, lottery, Kings Pick (best + feature)."""
  nl,nt=scrub_section(out)
  for k in ('best','feature'):
    t=out.get(k)
    if not t: continue
    lo=[_odds(x) if isinstance(x,dict) else _odds(out['legs'].get(x,{})) for x in t.get('legs',[])]
    if any(not isinstance(x,dict) and x not in out['legs'] for x in t.get('legs',[])) or not ticket_ok(lo) or (t.get('fd_payout_x') and not ticket_ok_dec(t['fd_payout_x'])):
      out[k]=None; nt+=1
  if isinstance(out.get('value'),list):
    n0=len(out['value']); out['value']=[v for v in out['value'] if leg_ok(v.get('odds'))]; nt+=n0-len(out['value'])
  out['odds_rule']=f"Every published leg is priced {LEG_MIN} to +{LEG_MAX:,} and every ticket's combined odds are {TICKET_MIN} to +{TICKET_MAX:,} (no -1000 or shorter)."
  return nl,nt
def scrub_research(doc):
  if not isinstance(doc,dict) or not isinstance(doc.get('options'),list): return 0,0
  n0=len(doc['options']); keep=[]
  for o in doc['options']:
    lo=[l.get('odds_pa') if l.get('odds_pa') is not None else l.get('odds') for l in o.get('legs',[])]
    md=[l.get('odds_md') for l in o.get('legs',[]) if l.get('odds_md') is not None]
    if ticket_ok(lo) and all(leg_ok(x) for x in md): keep.append(o)
  doc['options']=keep; return 0,n0-len(keep)
FILES={'picks.json':'picks','extra.json':'extra','extra2.json':'extra2','twoleg.json':'twoleg','twoleg.research.json':'research'}
def enforce(write=True):
  tot={}
  for f,kind in FILES.items():
    try: d=json.load(open(f))
    except Exception: continue
    if kind=='picks': r=scrub_picks(d)
    elif kind in('extra','extra2'):
      r=(0,0)
      for k,v in d.items():
        if isinstance(v,dict) and 'legs' in v: a=scrub_section(v,k); r=(r[0]+a[0],r[1]+a[1])
    elif kind=='twoleg': r=scrub_section(d)
    else: r=scrub_research(d)
    tot[f]=r
    if write and (r[0] or r[1]): json.dump(d,open(f,'w'),indent=1)
  return tot
SKIP={'favorites_record','stats','backtest','model_check'}  # past graded records / aggregates, not current picks
def violations():
  """independent scan: every 'odds'/'odds_pa'/'odds_md' number and every ticket payout in the published board files."""
  bad=[]
  def walk(x,path,f):
    if isinstance(x,dict):
      for k,v in x.items():
        if k in SKIP: continue
        if k in('odds','odds_pa','odds_md','odds_last','odds_first') and isinstance(v,(int,float)) and not leg_ok(v): bad.append((f,path+'.'+k,v))
        elif k in('fd_payout_x',) and isinstance(v,(int,float)) and not ticket_ok_dec(v): bad.append((f,path+'.'+k,v))
        else: walk(v,path+'.'+str(k),f)
    elif isinstance(x,list):
      for i,v in enumerate(x): walk(v,path+f'[{i}]',f)
  for f in FILES:
    try: walk(json.load(open(f)),'',f)
    except FileNotFoundError: pass
  return bad
if __name__=='__main__':
  if '--enforce' in sys.argv:
    t=enforce(); b=violations()
    print('odds rule: removed (legs, tickets)',t,'| remaining violations',len(b))
    if b: print(b[:10]); sys.exit(2)
  else: print(violations()[:50])
