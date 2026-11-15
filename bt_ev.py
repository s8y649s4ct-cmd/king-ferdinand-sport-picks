"""Out-of-sample backtests on graded history -> backtest.json (read by ledger.py and the site). Re-run every refresh (fast).
1) EV threshold for the Value board: graded candidate legs in shadow.json (every FanDuel leg the model saw, graded), edge =
   Pinnacle no-vig fair chance minus FanDuel's break-even chance (price incl. vig) at the first price seen that day.
   Time split: threshold chosen on the earlier half of dates (largest ROI with >= MIN_N legs), then scored on the later half.
2) v1 edge (our blended model vs FanDuel break-even) on the same split, for comparison.
3) Long tickets: ROI of posted ladder / Lottery / Kings Pick tickets by size, in both halves.
4) Value 2-leg: pairs of qualifying legs (different games, same day), 1 unit each, in both halves."""
import json,collections,oddsrule,itertools
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
def imp(o): o=float(o); return 100/(o+100) if o>0 else -o/(-o+100)
def dec(o): o=float(o); return 1+(o/100 if o>0 else 100/-o)
MIN_N=10; GRID=[0.0,0.01,0.02,0.03,0.04,0.05,0.06,0.07]
SH=load('shadow.json',{'legs':{}})['legs']
G=[r for r in SH.values() if r.get('result') in('win','loss') and r.get('odds_first') and r.get('v1') is not None and oddsrule.leg_ok(r.get('odds_first')) and oddsrule.leg_ok(r.get('odds_last'))]  # 2026-11-15 hard odds rule: backtest only what may be published
dates=sorted({r['date'] for r in G}); cut=dates[len(dates)//2] if dates else None
def roi(xs,ok='_o'):
  n=len(xs); w=sum(r['result']=='win' for r in xs); u=sum((dec(r[ok])-1) if r['result']=='win' else -1 for r in xs)
  return {'n':n,'won':w,'win_pct':round(w/n,4) if n else None,'units':round(u,2),'roi_pct':round(100*u/n,2) if n else None}
for r in G: r['_o']=r['odds_first']
def edge_pin(r): return None if r.get('sharp_first') is None else r['sharp_first']-imp(r['odds_first'])
def edge_v1(r): return r['v1']-imp(r['odds_first'])
out={'split_date':cut,'dates':[dates[0],dates[-1]] if dates else None,'legs_graded':len(G),'min_n':MIN_N}
for nm,ef in (('pinnacle',edge_pin),('v1',edge_v1)):
  rows=[]
  for t in GRID:
    tr=[r for r in G if r['date']<cut and ef(r) is not None and ef(r)>=t]; te=[r for r in G if r['date']>=cut and ef(r) is not None and ef(r)>=t]
    rows.append({'min_edge':t,'train':roi(tr),'test':roi(te),'all':roi(tr+te)})
  ok=[x for x in rows if x['train']['n']>=MIN_N]
  pick=max(ok,key=lambda x:x['train']['roi_pct']) if ok else None
  out[nm]={'grid':rows,'chosen_on_train':pick['min_edge'] if pick else None,'test_at_chosen':pick['test'] if pick else None}
P=out['pinnacle']; out['value_threshold']=P['chosen_on_train'] if P['chosen_on_train'] is not None else 0.06
th=out['value_threshold']
q=[r for r in G if edge_pin(r) is not None and edge_pin(r)>=th]
# by sport and edge band among qualifying legs
bs=collections.defaultdict(list)
for r in q: bs['soccer' if '.' in r['sport'] else r['sport']].append(r)
out['qualifying_by_sport']={k:roi(v) for k,v in bs.items()}
out['edge_bands']={f"{a*100:.0f}-{b*100:.0f} pts":roi([r for r in q if a<=edge_pin(r)<b]) for a,b in ((th,th+0.02),(th+0.02,th+0.04),(th+0.04,1))}
# 2-leg pairs of qualifying legs (all different-game pairs per day; shows whether combining value legs keeps ROI)
def pairs(xs):
  n=w=0;u=0.0
  byd=collections.defaultdict(list)
  for r in xs: byd[r['date']].append(r)
  for d,v in byd.items():
    for a,b in itertools.combinations(v,2):
      if a['event']==b['event']: continue
      n+=1; win=a['result']=='win' and b['result']=='win'; w+=win; u+=(dec(a['_o'])*dec(b['_o'])-1) if win else -1
  return {'n':n,'won':w,'win_pct':round(w/n,4) if n else None,'units':round(u,2),'roi_pct':round(100*u/n,2) if n else None}
out['value_2leg']={'train':pairs([r for r in q if r['date']<cut]),'test':pairs([r for r in q if r['date']>=cut])}
# long tickets from posted history
H=[x for x in load('picks.history.json',[]) if x.get('result') in('win','loss') and x.get('fd_payout_x')]
def tr(xs):
  n=len(xs); w=sum(x['result']=='win' for x in xs); u=sum((x['fd_payout_x']-1) if x['result']=='win' else -1 for x in xs)
  return {'n':n,'won':w,'win_pct':round(w/n,4) if n else None,'units':round(u,2),'roi_pct':round(100*u/n,2) if n else None}
def bt(n): return 'single' if n==1 else '2-leg' if n==2 else '3-5 legs' if n<=5 else '6-10 legs' if n<=10 else '11+ legs'
LT={}
for b in ('ladder','lottery','best'):
  for s in ('single','2-leg','3-5 legs','6-10 legs','11+ legs'):
    xs=[x for x in H if (x.get('type') or 'ladder')==b and bt(x['n'])==s]
    if xs: LT[f"{b} {s}"]={'train':tr([x for x in xs if x['date']<cut]),'test':tr([x for x in xs if x['date']>=cut]),'all':tr(xs)}
out['long_tickets']=LT
try:
  import bt_cal; out['calibration']=bt_cal.report()
except Exception as e: out['calibration']={'error':str(e)}
json.dump(out,open('backtest.json','w'),indent=1)
print('backtest: value threshold',th,'test',P['test_at_chosen'],'| v1 chosen',out['v1']['chosen_on_train'],out['v1']['test_at_chosen'])
