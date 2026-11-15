import json,collections,oddsrule,math
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
def imp(o): o=float(o); return 100/(o+100) if o>0 else -o/(-o+100)
def dec(o): o=float(o); return 1+(o/100 if o>0 else 100/-o)
SH=load('shadow.json',{'legs':{}})['legs']
G=[r for r in SH.values() if r.get('result') in('win','loss') and r.get('odds_last') and r.get('v1') is not None and oddsrule.leg_ok(r.get('odds_first')) and oddsrule.leg_ok(r.get('odds_last'))]  # 2026-11-15 hard odds rule: backtest only what may be published
dates=sorted({r['date'] for r in G}); cut=dates[len(dates)//2]
def grp(r): return ('soccer' if '.' in r['sport'] else r['sport'], r.get('kind') or '?')
def pav(xs):  # isotonic regression (pool adjacent violators) on (p,y) -> list of (p_hi, value)
  xs=sorted(xs); bl=[]
  for p,y in xs:
    bl.append([p,p,y,1])
    while len(bl)>1 and bl[-2][2]/bl[-2][3]>=bl[-1][2]/bl[-1][3]:
      b=bl.pop(); bl[-1][1]=b[1]; bl[-1][2]+=b[2]; bl[-1][3]+=b[3]
  return [(b[0],b[1],b[2]/b[3],b[3]) for b in bl]
def fit(train,M=30):
  C={}
  for key in {grp(r) for r in train}|{'ALL'}:
    xs=[(r['v1'],r['result']=='win') for r in train if key=='ALL' or grp(r)==key]
    if len(xs)>=80: C[key]=(pav(xs),len(xs))
  return C
def app(C,r,M=200):
  def f(key):
    if key not in C: return None
    bl,n=C[key]; p=r['v1']
    for lo,hi,v,c in bl:
      if p<=hi: return v
    return bl[-1][2]
  g=f(grp(r)); a=f('ALL'); n=C.get(grp(r),(None,0))[1]
  base=a if a is not None else r['v1']
  return base if g is None else (n*g+M*base)/(n+M)
def platt(train):
  # 1-d logistic on logit(v1) per sport group via a few Newton steps
  P={}
  for key in {grp(r)[0] for r in train}:
    xs=[(math.log(r['v1']/(1-r['v1'])),r['result']=='win') for r in train if grp(r)[0]==key and 0<r['v1']<1]
    if len(xs)<80: continue
    a,b=1.0,0.0
    for _ in range(25):
      ga=gb=haa=hab=hbb=0
      for x,y in xs:
        p=1/(1+math.exp(-(a*x+b))); e=p-y; w=p*(1-p); ga+=e*x; gb+=e; haa+=w*x*x; hab+=w*x; hbb+=w
      det=haa*hbb-hab*hab
      if det<=0: break
      a-=(hbb*ga-hab*gb)/det; b-=(haa*gb-hab*ga)/det
    P[key]=(a,b)
  return P
def papp(P,r):
  k=grp(r)[0]
  if k not in P or not 0<r['v1']<1: return r['v1']
  a,b=P[k]; x=math.log(r['v1']/(1-r['v1'])); return 1/(1+math.exp(-(a*x+b)))
def metrics(xs,pf):
  n=len(xs); br=sum((pf(r)-(r['result']=='win'))**2 for r in xs)/n
  ll=-sum(math.log(max(1e-6,pf(r) if r['result']=='win' else 1-pf(r))) for r in xs)/n
  return round(br,4),round(ll,4)
def top_per_game(xs,pf,filt=lambda r:True):
  by=collections.defaultdict(list)
  for r in xs:
    if filt(r): by[(r['date'],r['event'])].append(r)
  sel=[max(v,key=lambda r:(pf(r),-abs(r['odds_last']))) for v in by.values()]
  n=len(sel); w=sum(r['result']=='win' for r in sel); u=sum((dec(r['odds_last'])-1) if r['result']=='win' else -1 for r in sel)
  return {'n':n,'win_pct':round(w/n,4),'units':round(u,2),'roi_pct':round(100*u/n,2)}
def run(tr,te):
  C=fit(tr); P=platt(tr)
  base=lambda r:r['v1']; iso=lambda r:app(C,r); pl=lambda r:papp(P,r)
  mv=lambda r: imp(r['odds_last'])-imp(r['odds_first'])
  o={'test_legs':len(te)}
  for nm,f in (('v1 raw (live)',base),('isotonic by sport x market',iso),('Platt by sport',pl)):
    b,l=metrics(te,f); o[nm]={'brier':b,'logloss':l,'top_leg_per_game':top_per_game(te,f)}
  o['v1 + skip legs whose FanDuel price moved against by 2+ pts']={'top_leg_per_game':top_per_game(te,base,lambda r:mv(r)>-0.02)}
  o['v1 ranked by prob + 0.5 x edge']={'top_leg_per_game':top_per_game(te,lambda r:r['v1']+0.5*(r['v1']-imp(r['odds_last'])))}
  return o
def report():
  c1=dates[len(dates)//2]; c2=dates[int(len(dates)*0.7)]
  return {'note':'Fit on older dates, scored on newer dates. Top leg per game = 1-unit single at the last pregame FanDuel price.',
    'split_50_50':{'train_before':c1,**run([r for r in G if r['date']<c1],[r for r in G if r['date']>=c1])},
    'split_70_30':{'train_before':c2,**run([r for r in G if r['date']<c2],[r for r in G if r['date']>=c2])}}
if __name__=='__main__': print(json.dumps(report(),indent=1))
# ---- live use (adopted 2026-11-15): isotonic by sport x market, refit on ALL graded legs each refresh, used ONLY to rank
# which leg is each game's top leg. Displayed chances stay the v1 estimate (isotonic had slightly worse log loss out of sample).
def fit_all(): return fit(G)
def rank_prob(C,L):
  try: return app(C,{'v1':L['prob'],'sport':L['sport'],'kind':L.get('kind')})
  except Exception: return L['prob']
