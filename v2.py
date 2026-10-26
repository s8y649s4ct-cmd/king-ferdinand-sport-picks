"""KFSP v2 probability engine (runs in SHADOW next to v1; replaces v1 only when the switch rule is met).
Components: Pinnacle sharp anchor (power de-vig, alt lines via nearest Pinnacle line + normal/Poisson model),
SRS power ratings from ESPN results (shrunk toward league average), player-impact injuries (NBA box impact, NFL QB),
closing-line value tracking, league-correlated Monte Carlo parlay probability. Free sources only; failures fall back."""
import json,math,os,re,datetime
from math import erf,sqrt
UTC=datetime.timezone.utc
PIN='https://guest.api.arcadia.pinnacle.com/0.1/'; PKEY='CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R'  # public key used by pinnacle.com's own web app
LEAGUES={'nfl':889,'college-football':880,'nba':487,'nhl':1456,'mlb':246,'eng.1':1980,'esp.1':2196,'ita.1':2436,'ger.1':1842,'fra.1':2036,'usa.1':2663}
SD={'nba':(12.0,17.0),'college-football':(15.0,14.0),'nfl':(13.5,13.0),'nhl':(2.6,2.4),'mlb':(4.2,4.3)}
SOCCER={'eng.1','esp.1','ita.1','ger.1','fra.1','usa.1'}
HFA={'nba':2.5,'nfl':1.8,'college-football':2.8,'nhl':0.15,'mlb':0.15}; SHRINK={'nba':10,'nfl':4,'college-football':4,'nhl':15,'mlb':20}
def ncdf(x): return 0.5*(1+erf(x/sqrt(2)))
def ninv(p):
  p=min(max(p,1e-6),1-1e-6); lo,hi=-10,10
  for _ in range(60):
    m=(lo+hi)/2
    if ncdf(m)<p: lo=m
    else: hi=m
  return (lo+hi)/2
def imp(o):
  o=float(o); return 100/(o+100) if o>0 else -o/(-o+100)
def devig(prices):
  """power method: find k with sum(p_i^k)=1"""
  q=[imp(x) for x in prices]
  if any(x<=0 or x>=1 for x in q): return None
  lo,hi=0.5,3.0
  for _ in range(60):
    k=(lo+hi)/2
    if sum(x**k for x in q)>1: lo=k
    else: hi=k
  return [x**k for x in q]
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
# ---------------- sharp anchor ----------------
def pinnacle(games,get,toks):
  import urllib.request
  def pget(path):
    cf='.cache/pin_'+re.sub(r'\W','_',path)
    if os.path.exists(cf) and datetime.datetime.now().timestamp()-os.path.getmtime(cf)<240: return load(cf,None)
    try:
      d=json.load(urllib.request.urlopen(urllib.request.Request(PIN+path,headers={'X-API-Key':PKEY,'User-Agent':'Mozilla/5.0','Referer':'https://www.pinnacle.com/'}),timeout=20)); json.dump(d,open(cf,'w')); return d
    except Exception as e: print('pinnacle fail',path,e); return load(cf,None)
  out={}; st={'leagues_ok':0,'leagues':0}
  for lg in {g['sport'] for g in games if g['state']=='pre'}:
    lid=LEAGUES.get(lg)
    if not lid: continue
    st['leagues']+=1; M=pget(f'leagues/{lid}/matchups'); S=pget(f'leagues/{lid}/markets/straight')
    if not M or not S: continue
    st['leagues_ok']+=1
    mk={}
    for s in S:
      if s.get('period')==0: mk.setdefault(s['matchupId'],[]).append(s)
    for g in games:
      if g['sport']!=lg or g['state']!='pre': continue
      best=None
      for m in M:
        if m.get('type')!='matchup' or m.get('parentId') or m.get('isLive'): continue
        if (m.get('units') or 'Regular')!='Regular': continue
        try:
          if abs((ts(m['startTime'])-ts(g['start'])).total_seconds())>5400: continue
        except Exception: continue
        P={p['alignment']:p['name'] for p in m['participants']}
        if 'home' not in P or 'away' not in P: continue
        sc=len(toks(P['home'])&toks(g['teams']['home']['name']+' '+g['teams']['home']['short']))+len(toks(P['away'])&toks(g['teams']['away']['name']+' '+g['teams']['away']['short']))
        if sc>=2 and (not best or sc>best[0]): best=(sc,m)
      if not best: continue
      ent={'id':best[1]['id'],'spreads':[],'totals':[],'ml':None}
      for s in mk.get(best[1]['id'],[]):
        pr={p.get('designation'):p for p in s['prices']}
        if s['type']=='moneyline':
          if 'draw' in pr: v=devig([pr['home']['price'],pr['away']['price'],pr['draw']['price']]); ent['ml']=v and {'home':v[0],'away':v[1],'draw':v[2]}
          elif 'home' in pr and 'away' in pr: v=devig([pr['home']['price'],pr['away']['price']]); ent['ml']=v and {'home':v[0],'away':v[1],'draw':0}
        elif s['type']=='spread' and 'home' in pr and 'away' in pr:
          v=devig([pr['home']['price'],pr['away']['price']])
          if v: ent['spreads'].append((pr['home']['points'],v[0],not s.get('isAlternate')))
        elif s['type']=='total' and 'over' in pr and 'under' in pr:
          v=devig([pr['over']['price'],pr['under']['price']])
          if v: ent['totals'].append((pr['over']['points'],v[0],not s.get('isAlternate')))
      out[g['id']]=ent
  st['games_matched']=len(out); st['games_pre']=sum(1 for g in games if g['state']=='pre'); return out,st
def pois_over(lam,line):
  k=math.floor(line); c=sum(math.exp(-lam)*lam**i/math.factorial(i) for i in range(k+1)); return 1-c
def sharp_prob(L,g,P):
  """returns (prob, how) or (None,reason). Never invents a price: needs a Pinnacle market on the same game."""
  e=P.get(L['event'])
  if not e: return None,'no Pinnacle match'
  k=L['kind']; sp=L['sport']; side=L.get('side')
  ml=e.get('ml')
  if k in('ml','ml3','dnb','dc'):
    if not ml: return None,'no Pinnacle moneyline'
    if k=='dnb': return ml[side]/(ml['home']+ml['away']),'Pinnacle 3-way de-vig'
    if k=='dc':
      if side=='nodraw': return ml['home']+ml['away'],'Pinnacle 3-way de-vig'
      return ml[side]+ml['draw'],'Pinnacle 3-way de-vig'
    if side in ml: return ml[side],'Pinnacle moneyline de-vig'
    return None,'side?'
  if k=='spread' and side in('home','away') and L.get('line') is not None and e['spreads']:
    hl=L['line'] if side=='home' else -L['line']
    hp,ph,_=min(e['spreads'],key=lambda t:(abs(t[0]-hl),not t[2]))
    if abs(hp-hl)<1e-6: p=ph
    else:
      sd=SD.get(sp)
      if not sd: return None,'alt line outside Pinnacle range (no model for sport)'
      mu=sd[0]*ninv(ph)-hp; p=ncdf((mu+hl)/sd[0])
    return (p if side=='home' else 1-p),('Pinnacle exact line' if abs(hp-hl)<1e-6 else f'Pinnacle {hp:+g} line extrapolated {abs(hp-hl):g} pts')
  if k=='total' and L.get('line') is not None and e['totals'] and L.get('ou') in('over','under'):
    tp,po,_=min(e['totals'],key=lambda t:(abs(t[0]-L['line']),not t[2]))
    if abs(tp-L['line'])<1e-6: p=po
    elif sp in SOCCER:
      lo,hi=0.05,10
      for _ in range(50):
        m=(lo+hi)/2
        if pois_over(m,tp)<po: lo=m
        else: hi=m
      p=pois_over((lo+hi)/2,L['line'])
    else:
      sd=SD.get(sp)
      if not sd: return None,'no model'
      mu=tp+sd[1]*ninv(po); p=ncdf((mu-L['line'])/sd[1])
    return (p if L['ou']=='over' else 1-p),('Pinnacle exact total' if abs(tp-L['line'])<1e-6 else f'Pinnacle total {tp:g} extrapolated')
  return None,'market not on Pinnacle (props etc.)'
# ---------------- power ratings + player impact ----------------
def power(games,get,SPORTS):
  R={}; info={}
  for lg in {g['sport'] for g in games if g['state']=='pre'} & set(HFA):
    teams={t['tid'] for g in games if g['sport']==lg and g['state']=='pre' for t in g['teams'].values() if t.get('tid')}
    res=[]
    for tid in teams:
      d=get(f"https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/teams/{tid}/schedule",ttl=10800) or {}
      for e in d.get('events',[]):
        c=e['competitions'][0]
        if not c['status']['type'].get('completed'): continue
        if (e.get('seasonType') or {}).get('type') not in (None,2,'2'): continue  # regular season only
        cs=c['competitors']; me=next((k for k in cs if k['team']['id']==tid),None); op=next((k for k in cs if k is not me),None)
        try:
          s1=float((me['score'] or {}).get('value') if isinstance(me['score'],dict) else me['score']); s2=float((op['score'] or {}).get('value') if isinstance(op['score'],dict) else op['score'])
        except Exception: continue
        res.append((tid,op['team']['id'],s1-s2,1 if me.get('homeAway')=='home' else -1))
    r={}
    for _ in range(30):
      nr={}
      for tid in teams:
        g=[(m-HFA[lg]*h+r.get(o,0)) for t,o,m,h in res if t==tid]
        nr[tid]=sum(g)/len(g) if g else 0
      r=nr
    n={tid:sum(1 for x in res if x[0]==tid) for tid in teams}
    R[lg]={tid:r[tid]*n[tid]/(n[tid]+SHRINK[lg]) for tid in teams}; info[lg]={'teams':len(teams),'games':len(res)}
  return R,info
def injuries(games,get,SPORTS,NOW):
  adj={}; notes={}
  now=datetime.datetime.now(UTC)
  slate={(g['sport'],t['name']):t['tid'] for g in games if g['state']=='pre' for t in g['teams'].values()}
  W={'Out':1,'Doubtful':0.75,'Questionable':0.4,'Day-To-Day':0.3}
  for lg in ('nba','nfl'):
    d=get(f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[lg]}/{lg}/injuries',ttl=600) or {}
    for t in d.get('injuries',[]):
      tid=slate.get((lg,t['displayName']))
      if not tid: continue
      for i in t.get('injuries',[]):
        w=W.get(i.get('status'))
        try: recent=(now-ts(i['date'])).days<=10
        except Exception: recent=False
        if not w or not recent: continue  # long-term absences are already in the team's results
        a=i.get('athlete') or {}; pos=(a.get('position') or {}).get('abbreviation')
        if lg=='nfl':
          if pos!='QB': continue
          imp_=2.0*w; why=f"QB {a.get('displayName')} {i['status']}"
        else:
          m=re.search(r'/id/(\d+)/',json.dumps(a.get('links',[])))
          if not m: continue
          s=get(f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{m.group(1)}/overview",ttl=86400) or {}
          st=s.get('statistics') or {}; lab=st.get('labels') or []; sp=[x for x in st.get('splits',[]) if x.get('displayName') in('Regular Season','Career')]
          if not sp or 'PTS' not in lab: continue
          v=dict(zip(lab,sp[-1]['stats']))
          try: pts,reb,ast,mn=(float(v[k]) for k in('PTS','REB','AST','MIN'))
          except Exception: continue
          imp_=min(6.0,0.28*(pts+0.4*reb+0.7*ast)*min(1,mn/32))*w; why=f"{a.get('displayName')} {i['status']} ({pts:.0f}p/{reb:.0f}r/{ast:.0f}a, {mn:.0f} min)"
        if imp_<0.3: continue
        adj[(lg,tid)]=adj.get((lg,tid),0)+imp_; notes.setdefault((lg,tid),[]).append(f"{why}: -{imp_:.1f} pts")
  return adj,notes
def power_prob(L,g,R,IA):
  lg=L['sport']
  if lg not in R or L['kind'] not in('ml','spread'): return None,None
  th,ta=g['teams']['home'].get('tid'),g['teams']['away'].get('tid')
  if th not in R[lg] or ta not in R[lg]: return None,None
  mu=R[lg][th]-IA.get((lg,th),0)-(R[lg][ta]-IA.get((lg,ta),0))+HFA[lg]
  sd=SD[lg][0]; side=L.get('side')
  if side not in('home','away'): return None,None
  m=mu if side=='home' else -mu
  if L['kind']=='ml': return ncdf(m/sd),mu
  if L.get('line') is None: return None,None
  return ncdf((m+L['line'])/sd),mu
# ---------------- main shadow pass ----------------
def score(cands,games,G,get,SPORTS,toks,cfg):
  C=cfg.get('v2',{}); w=C.get('power_weight',0.15)
  P,pst=pinnacle(games,get,toks)
  try: R,rinfo=power(games,get,SPORTS)
  except Exception as e: print('power fail',e); R,rinfo={},{}
  try: IA,IN=injuries(games,get,SPORTS,None)
  except Exception as e: print('inj fail',e); IA,IN={},{}
  cov=0; pre=0
  for L in cands:
    g=G[L['event']]; L['v1_prob']=L['prob']
    if g['state']!='pre': continue
    pre+=1
    sp,how=sharp_prob(L,g,P)
    pp,mu=power_prob(L,g,R,IA)
    base=sp if sp is not None else L.get('market_prob',L['fd_prob'])
    v=base if pp is None else (1-w)*base+w*pp
    L['v2_prob']=round(max(0.01,min(0.99,v)),4); L['v2_src']=('Pinnacle: '+how) if sp is not None else 'no sharp price -> FanDuel no-vig/line model'
    if sp is not None:
      cov+=1; L['sharp_prob']=round(sp,4); L['sharp_edge']=round(sp-imp(L['odds']),4)  # >0: FanDuel pays more than sharp fair
    if pp is not None:
      L['power_prob']=round(pp,4); L['power_margin_home']=round(mu,1)
      inj=[n for s in('home','away') for n in IN.get((L['sport'],g['teams'][s].get('tid')),[])]
      if inj: L['v2_injuries']=inj
  info={'pinnacle':pst,'candidates_pre':pre,'sharp_covered':cov,'sharp_coverage_pct':round(100*cov/max(pre,1),1),'power':rinfo,
        'injury_adjusted_teams':len(IA)}
  return info
def sharp_filter(cands,cfg):
  thr=cfg.get('v2',{}).get('filter_edge',-0.03)
  drop=[L for L in cands if L.get('sharp_edge') is not None and L['sharp_edge']<thr]
  if not cfg.get('v2',{}).get('sharp_filter',False): return cands,drop  # report only
  ids={L['id'] for L in drop}; return [L for L in cands if L['id'] not in ids],drop
# ---------------- shadow log, grading, CLV, switch ----------------
def ll(p,y): p=min(max(p,0.01),0.99); return -math.log(p if y else 1-p)
def shadow(cands,G,grade,DATE,NOW,cfg,v1best,live='v1'):
  S=load('shadow.json',{'legs':{}}); LG=S['legs']
  byg={}
  for L in cands:
    if G[L['event']]['state']=='pre' and L.get('v2_prob') is not None: byg.setdefault(L['event'],[]).append(L)
  for e,ls in byg.items():
    v1=sorted(ls,key=lambda L:-L['v1_prob'])[:5]; v2=sorted(ls,key=lambda L:-L['v2_prob'])[:5]
    top1=v1[0]['id']; top2=v2[0]['id']
    for L in {x['id']:x for x in v1+v2+([v1best[e]] if e in v1best else [])}.values():
      r=LG.get(L['id'])
      if not r:
        r=LG[L['id']]={k:L[k] for k in('id','event','sport','kind','side','line','ou','player','stat','pick','market','game','start') if k in L}
        r.update({'date':DATE,'odds_first':L['odds'],'sharp_first':L.get('sharp_prob'),'result':None})
      r.update({'odds_last':L['odds'],'sharp_last':L.get('sharp_prob'),'v1':L['v1_prob'],'v2':L['v2_prob'],'seen':NOW})
    for r in LG.values():
      if r['event']==e: r['v1_top']=r['id']==top1; r['v2_top']=r['id']==top2
    if e in v1best and v1best[e]['id'] in LG: LG[v1best[e]['id']][live+'_best']=True  # King's Favorite/Best Parlay pool leg of the live model
  for r in LG.values():
    if r['result'] is None:
      g=G.get(r['event'])
      if g and g['state']=='post': r['result']=grade(r)
      elif not g and (datetime.date.fromisoformat(DATE)-datetime.date.fromisoformat(r['date'])).days>3: r['result']='void'
  json.dump(S,open('shadow.json','w'))
  return evaluate(LG,cfg)
def clv(r):
  c={'fd':imp(r['odds_last'])-imp(r['odds_first'])}
  if r.get('sharp_first') is not None and r.get('sharp_last') is not None: c['sharp']=r['sharp_last']-r['sharp_first']
  return c
def evaluate(LG,cfg):
  C=cfg.get('v2',{}); need=C.get('switch_min_graded',100)
  gr=[r for r in LG.values() if r.get('result') in('win','loss')]
  def m(key,top):
    ps=[(r[key],r['result']=='win') for r in gr]
    out={'n':len(ps),'brier':round(sum((p-y)**2 for p,y in ps)/len(ps),4) if ps else None,'logloss':round(sum(ll(p,y) for p,y in ps)/len(ps),4) if ps else None}
    tp=[r for r in LG.values() if r.get(top) or r.get(key+'_best')]
    cl=[clv(r) for r in tp]
    out['picks']=len(tp); out['avg_clv_fd_pts']=round(100*sum(c['fd'] for c in cl)/len(cl),2) if cl else None
    cs=[c['sharp'] for c in cl if 'sharp' in c]; out['avg_clv_sharp_pts']=round(100*sum(cs)/len(cs),2) if cs else None
    tg=[r for r in tp if r.get('result') in('win','loss')]; out['top_picks_graded']=len(tg); out['top_picks_won']=sum(r['result']=='win' for r in tg)
    out['top_picks_expected']=round(sum(r[key] for r in tg),2)
    return out
  v1=m('v1','v1_top'); v2=m('v2','v2_top')
  ntop=C.get('switch_min_top',30)
  wr=lambda x:(x['top_picks_won']/x['top_picks_graded']) if x['top_picks_graded'] else None
  v1['top_win_rate']=wr(v1); v2['top_win_rate']=wr(v2)
  lt=lambda a,b:a is not None and b is not None and a<b
  conds=[
    {'name':f'At least {need} graded legs','v1':len(gr),'v2':len(gr),'pass':len(gr)>=need},
    {'name':'v2 lower log loss','v1':v1['logloss'],'v2':v2['logloss'],'pass':lt(v2['logloss'],v1['logloss'])},
    {'name':'v2 higher avg CLV vs FanDuel','v1':v1['avg_clv_fd_pts'],'v2':v2['avg_clv_fd_pts'],'pass':lt(v1['avg_clv_fd_pts'],v2['avg_clv_fd_pts'])},
    {'name':'v2 higher avg CLV vs Pinnacle','v1':v1['avg_clv_sharp_pts'],'v2':v2['avg_clv_sharp_pts'],'pass':lt(v1['avg_clv_sharp_pts'],v2['avg_clv_sharp_pts'])},
    {'name':f'At least {ntop} top picks graded (each model)','v1':v1['top_picks_graded'],'v2':v2['top_picks_graded'],'pass':min(v1['top_picks_graded'],v2['top_picks_graded'])>=ntop},
    {'name':'v2 top-pick win rate >= v1','v1':f"{v1['top_picks_won']}/{v1['top_picks_graded']}",'v2':f"{v2['top_picks_won']}/{v2['top_picks_graded']}",'pass':wr(v1) is not None and wr(v2) is not None and wr(v2)>=wr(v1)}]
  ready=all(c['pass'] for c in conds)
  return {'v1':v1,'v2':v2,'graded':len(gr),'need':need,'need_top':ntop,'conditions':conds,'switch_ready':ready,
          'switch':ready and C.get('allow_switch',False),
          'rule':f"v1 is live. v2 is only PROPOSED (switch_ready) when ALL hold on the same graded legs: {need}+ graded legs, lower log loss, higher avg CLV vs FanDuel AND vs Pinnacle, {ntop}+ top picks graded and a top-pick win rate (King's Favorite/Best Parlay legs + top leg per game) at least v1's. Even then the user is asked first; it never switches on its own."}
def hist_clv(hist,allc,G):
  """record last pre-game FanDuel price on every logged pick (v1 history) while its game hasn't started"""
  for x in hist:
    for l in x['legs_detail']:
      g=G.get(l['event'])
      if g and g['state']=='pre' and l['id'] in allc: l['close_odds']=allc[l['id']]['odds']
  seen={}
  for x in hist:
    for l in x['legs_detail']:
      if l.get('close_odds') is not None: seen[l['id']]=l
  cl=[imp(l['close_odds'])-imp(l['odds']) for l in seen.values()]
  return {'legs_tracked':len(cl),'avg_clv_pts':round(100*sum(cl)/len(cl),2) if cl else None,'beat_close':sum(c>0 for c in cl),'worse_than_close':sum(c<0 for c in cl)}
# ---------------- correlation-aware parlay probability ----------------
def corr_prob(legs,rho=0.04,n=40000,seed=7):
  try: import numpy as np
  except Exception: return None
  if not legs: return None
  rng=np.random.default_rng(seed); lgs=sorted({L['sport'] for L in legs})
  F={s:rng.standard_normal(n) for s in lgs}; ok=np.ones(n,bool)
  for L in legs:
    sg=(1 if L.get('ou')=='over' else -1) if L['kind']=='total' else 0  # shared league scoring environment moves totals only
    z=sg*sqrt(rho)*F[L['sport']]+sqrt(1-rho*abs(sg))*rng.standard_normal(n)
    ok&=z<ninv(L['prob'])
  return float(ok.mean())
