#!/usr/bin/env python3
"""KFSP extra board 2: NFL anytime-TD tab + NBA 3-pointers & rebounds tab -> extra2.json (graded in extra2.history.json).
Pregame only. Every leg is a FanDuel PA OPEN/ACTIVE selection (742.* market). Estimates use ESPN game logs, rosters/injuries,
ESPN box scores of each opponent's recent games, ESPN spread/total, and Pinnacle player props (no-vig) when Pinnacle lists the player."""
src=open(__file__.replace('extra2.py','extra.py')).read()
exec(src[:src.index('# ======================= LIVE')])   # shared helpers + ESPN games (no live/props side effects)
PIN='https://guest.api.arcadia.pinnacle.com/0.1/'; PKEY='CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R'
def pget(path):
  cf='.cache/pin2_'+re.sub(r'\W','_',path)
  if os.path.exists(cf) and time.time()-os.path.getmtime(cf)<240: return load(cf,None)
  try:
    d=json.load(urllib.request.urlopen(urllib.request.Request(PIN+path,headers={'X-API-Key':PKEY,'User-Agent':'Mozilla/5.0','Referer':'https://www.pinnacle.com/'}),timeout=20)); json.dump(d,open(cf,'w')); return d
  except Exception as e: print('pinnacle fail',path,e); return load(cf,None)
def pin_props(lid,kinds):
  M=pget(f'leagues/{lid}/matchups') or []; S=pget(f'leagues/{lid}/markets/straight') or []
  pr={s['matchupId']:s for s in S if s.get('period')==0 and s.get('type')=='total'}; out={}
  for m in M:
    if m.get('type')!='special' or (m.get('parent') or {}).get('isLive'): continue
    d=m['special'].get('description','')
    for kw,key in kinds.items():
      if d.endswith(' '+kw) and m['id'] in pr:
        pl=d[:-len(kw)-1]; ps={p['participantId']:p for p in pr[m['id']]['prices']}
        o=next((ps.get(p['id']) for p in m['participants'] if p['name']=='Over'),None); u=next((ps.get(p['id']) for p in m['participants'] if p['name']=='Under'),None)
        if o and u:
          a,b=imp(o['price']),imp(u['price']); out[(pname(pl),key)]={'line':o['points'],'p_over':a/(a+b),'start':m.get('startTime')}
  return out
def pois_ge(lam,k): return 1-sum(pois(lam,i) for i in range(k))
def pois(l,k): return exp(-l)*l**k/math.factorial(k)
def fit_lam(line,p_over):  # Poisson mean that reproduces Pinnacle's P(X>line)
  lo,hi=0.01,40
  for _ in range(60):
    mid=(lo+hi)/2
    if pois_ge(mid,int(line)+1)<p_over: lo=mid
    else: hi=mid
  return (lo+hi)/2
def roster(sp,lg,tid): return get(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/teams/{tid}/roster',ttl=3*3600) or {}
def gamelog(sp,lg,aid,season=None,ttl=3*3600): return get(f'https://site.web.api.espn.com/apis/common/v3/sports/{sp}/{lg}/athletes/{aid}/gamelog'+(f'?season={season}' if season else ''),ttl=ttl) or {}
def glrows(gl):
  names=gl.get('names') or []; evs=gl.get('events') or {}; rows=[]
  for s in gl.get('seasonTypes') or []:
    if 'Regular' not in s.get('displayName',''): continue
    for c in s.get('categories') or []:
      for e in c.get('events') or []:
        r={'eid':e['eventId'],'date':(evs.get(e['eventId']) or {}).get('gameDate','')}
        for i,nm in enumerate(names):
          v=str(e['stats'][i])
          try:
            if '-' in v and nm.startswith(('three','field','free')): mde,att=v.split('-'); r[nm.split('-')[0]]=float(mde); r[nm.split('-')[1]]=float(att)
            else: r[nm]=float(v)
          except Exception: pass
        rows.append(r)
  rows.sort(key=lambda r:r['date'],reverse=True); return rows
BAD={'out','doubtful','questionable','day-to-day','injured reserve','suspension'}
def fdpairs(lg,tab):
  d=get(f"{FD}content-managed-page?page=CUSTOM&customPageId={lg}&_ak={K}&timezone=America/New_York",ttl=240) or {}
  fe=[e for e in ((d.get('attachments') or {}).get('events') or {}).values() if ' @ ' in e['name']]
  pre=[g for g in games.values() if g['sport']==lg and g['state']=='pre' and 0<(ts(g['start'])-now).total_seconds()<30*3600]
  pairs=[]
  for g in pre:
    e=next((e for e in fe if match(e['name'],[g],e['openDate'])),None)
    if e and not e.get('inPlay'): pairs.append((g,e))
  def pg(pe):
    mk={}
    for t in tab: mk.update(((get(f"{FD}event-page?_ak={K}&eventId={pe[1]['eventId']}&tab={t}",ttl=240) or {}).get('attachments') or {}).get('markets') or {})
    return mk
  with ThreadPoolExecutor(10) as ex: return pairs,list(ex.map(pg,pairs))
def rost(sp,lg,g):
  R={}
  for side in('home','away'):
    al=[]
    for grp in roster(sp,lg,g['teams'][side]['tid']).get('athletes') or []: al+=grp['items'] if 'items' in grp else [grp]
    R[side]={pname(a.get('fullName','')):a for a in al}
  return R
def inj(a): return (a.get('injuries') or [{}])[0].get('status','') if a.get('injuries') else ''
def pos(a): return ((a.get('position') or {}).get('abbreviation') or '')
def opp_box(sp,lg,tid,n):
  """Last n completed games of team tid: what its OPPONENTS did (team box + player box)."""
  s=get(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/teams/{tid}/schedule',ttl=6*3600) or {}
  pe=[e for e in s.get('events') or [] if e['competitions'][0]['status']['type']['state']=='post'][-n:]; out=[]
  for e in pe:
    b=(get(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/summary?event={e["id"]}',ttl=7*86400) or {}).get('boxscore') or {}
    ot=[t for t in b.get('teams') or [] if t['team']['id']!=str(tid)]; op=[t for t in b.get('players') or [] if t['team']['id']!=str(tid)]
    me=[t for t in b.get('teams') or [] if t['team']['id']==str(tid)]
    if ot: out.append({'date':e['date'],'team':{x['name']:x['displayValue'] for x in ot[0]['statistics']},'me':{x['name']:x['displayValue'] for x in me[0]['statistics']} if me else {},'players':op[0]['statistics'] if op else []})
  return out,[e['date'] for e in pe]
def ticket(legs,typ):
  p=1; x=1
  for L in legs: p*=L['prob']; x*=dec(L['odds'])
  return {'n':len(legs),'legs':[L['id'] for L in legs],'est_prob':round(p,4),'fd_payout_x':round(x,2),'ev':round(p*x-1,4),'fd_link':fdlink(legs),'type':typ,'favorite':False}
def ladder(pool,nmax,per_game,per_team,reuse,typ):
  uses={}; tix=[]
  for n in range(1,min(nmax,len(pool))+1):
    sel=[]; pg={}; pt={}
    for L in sorted(pool,key=lambda L:-(L['prob']-0.006*uses.get(L['id'],0))):
      if pg.get(L['event'],0)>=per_game or pt.get(L['team'],0)>=per_team or uses.get(L['id'],0)>=reuse: continue
      sel.append(L); pg[L['event']]=pg.get(L['event'],0)+1; pt[L['team']]=pt.get(L['team'],0)+1
      if len(sel)==n: break
    if len(sel)<n: break
    for L in sel: uses[L['id']]=uses.get(L['id'],0)+1
    tix.append(ticket(sorted(sel,key=lambda L:-L['prob']),typ))
  return tix
def spread_of(g,side):  # ESPN details like "PIT -3.5"
  d=g.get('details') or ''; m=re.match(r'(\S+)\s+([+-]?\d+(?:\.\d+)?)',d)
  if not m: return None
  fav=m.group(1); v=float(m.group(2)); T=g['teams']
  favside='home' if fav==T['home']['abbr'] else 'away' if fav==T['away']['abbr'] else None
  if not favside: return None
  return v if side==favside else -v
# ======================= NFL ANYTIME TD =======================
tpairs,tmk=fdpairs('nfl',['td-scorer-props'])
PIN_TD=pin_props(889,{'Total Touchdowns':'td'})
td=[]; tcov={'games':len(tpairs),'fd_selections':0,'players_matched':0,'pinnacle_priced':0,'excluded_injury':[],'unmatched':0}
excl=set(); nomatch=set(); need={}; raw=[]
for (g,e),mk in zip(tpairs,tmk):
  R=rost('football','nfl',g)
  for m in mk.values():
    if m['marketType']!='ANY_TIME_TOUCHDOWN_SCORER' or m.get('marketStatus')!='OPEN' or m.get('inPlay'): continue
    for r in m['runners']:
      if r.get('runnerStatus')!='ACTIVE' or not r.get('winRunnerOdds',{}).get('americanDisplayOdds'): continue
      tcov['fd_selections']+=1; side=next((s for s in R if pname(r['runnerName']) in R[s]),None)
      if not side: nomatch.add(r['runnerName']); continue
      a=R[side][pname(r['runnerName'])]; raw.append((g,m,r,side,a,R)); need[a['id']]=1
def fgl(aid): return aid,(gamelog('football','nfl',aid),gamelog('football','nfl',aid,'2025',ttl=30*86400))
with ThreadPoolExecutor(12) as ex: GL=dict(ex.map(fgl,need))
OPP={}
def fopp(tid): return tid,opp_box('football','nfl',tid,6)[0]
with ThreadPoolExecutor(8) as ex: OPP=dict(ex.map(fopp,{g['teams'][s]['tid'] for g,_ in tpairs for s in('home','away')}))
def tds_allowed(tid):
  G=OPP.get(tid) or []; rush=rec=0
  for x in G:
    for c in x['players']:
      if c['name'] in('rushing','receiving'):
        k=c['keys'].index(c['name']+'Touchdowns') if c['name']+'Touchdowns' in c['keys'] else None
        if k is None: continue
        s=sum(float(a['stats'][k] or 0) for a in c['athletes'] if a.get('stats'))
        if c['name']=='rushing': rush+=s
        else: rec+=s
  return (rush/len(G),rec/len(G),len(G)) if G else None
LG_RUSH,LG_REC=0.85,1.45   # NFL league-average rushing / receiving TDs per team-game (2023-25 seasons, approx.)
for g,m,r,side,a,R in raw:
  st=inj(a); P=pos(a); pl=r['runnerName']
  if st.lower() in BAD: excl.add(f"{pl} ({st})"); continue
  cur,prev=GL.get(a['id'],({},{})); rc=glrows(cur); rp=glrows(prev)[-0:][:17]
  if not rc: continue
  tdg=lambda x:(x.get('rushingTouchdowns',0)+x.get('receivingTouchdowns',0))>=1
  touch=lambda x:x.get('rushingAttempts',0)+x.get('receivingTargets',0)
  o=od(r); fdnv=imp(o)/1.22   # anytime-TD markets carry ~20-25% FanDuel margin; no two-sided price to strip it exactly
  pk=PIN_TD.get((pname(pl),'td')); pin=pk['p_over'] if pk and pk['line']==0.5 else None
  mkt=pin if pin is not None else fdnv
  hw=sum(tdg(x) for x in rc)+0.5*sum(tdg(x) for x in rp); n=len(rc)+0.5*len(rp); k=6.0
  pemp=(hw+k*mkt)/(n+k)
  why=[f"TD in {sum(tdg(x) for x in rc)}/{len(rc)} games this season ({sum(x.get('rushingTouchdowns',0)+x.get('receivingTouchdowns',0) for x in rc):g} TDs)",
       f"last 5: {sum(tdg(x) for x in rc[:5])}/{len(rc[:5])}"]
  if rp: why.append(f"2025: {sum(tdg(x) for x in rp)}/{len(rp)}")
  t5=[touch(x) for x in rc[:5]]; ts_=[touch(x) for x in rc]
  why.append(f"carries+targets {sum(t5)/len(t5):.1f}/g last {len(t5)} (season {sum(ts_)/len(ts_):.1f})")
  adj=0
  if len(rc)>=3 and sum(t5[:2])/2<0.6*sum(ts_)/len(ts_): adj-=0.04; why.append('touches falling -4 pts')
  sp=spread_of(g,side); tt=None
  if sp is not None and g.get('ou'): tt=g['ou']/2-sp/2; f=max(-0.03,min(0.03,(tt/22.5-1)*0.2)); adj+=f; why.append(f"implied team total {tt:.1f} ({f*100:+.1f} pts)")
  ot='away' if side=='home' else 'home'; ta=tds_allowed(g['teams'][ot]['tid'])
  if ta:
    rush,rec,ng=ta; rushy=sum(x.get('rushingAttempts',0) for x in rc)>=sum(x.get('receivingTargets',0) for x in rc)
    ratio=(rush/LG_RUSH) if rushy else (rec/LG_REC); f=max(-0.02,min(0.02,(ratio-1)*0.05)); adj+=f
    why.append(f"{g['teams'][ot]['short']} allowed {rush:.1f} rush / {rec:.1f} rec TDs per game (last {ng}) ({f*100:+.1f} pts)")
  qbs=[x for x in R[side].values() if pos(x)=='QB' and inj(x).lower() in('out','doubtful','questionable')]
  if qbs and P!='QB': why.append('QB listed '+', '.join(f"{x.get('fullName')} ({inj(x)})" for x in qbs[:2]))
  mo=[x.get('fullName') for x in R[side].values() if pos(x)==P and inj(x).lower()=='out' and x['id']!=a['id']]
  if mo and P in('RB','WR','TE'): adj+=0.02; why.append(f"same-position teammates out: {', '.join(mo[:2])} (+2 pts, role absorption; total adjustments capped ±5 pts, never >8 pts above market)")
  adj=max(-0.05,min(0.05,adj)); p=min(0.5*mkt+0.5*pemp+adj,mkt+0.08)
  why.append(f"Pinnacle no-vig {pin*100:.1f}%" if pin is not None else f"FanDuel {o:+d} ≈ {fdnv*100:.1f}% after ~22% margin (no Pinnacle price)")
  if pin is not None: tcov['pinnacle_priced']+=1
  td.append({'id':f"{g['id']}:{r['selectionId']}:{m['marketId']}",'event':g['id'],'sport':'nfl','game':g['name'],'start':g['start'],'market':m['marketName'],'player':pl,'pos':P,
    'team':g['teams'][side]['name'],'pick':f"{pl} anytime TD",'odds':o,'fd_prob':round(fdnv,4),'pin_prob':round(pin,4) if pin is not None else None,'emp_prob':round(pemp,4),
    'prob':round(max(.01,min(.9,p)),4),'why':'; '.join(why),'asof':NOW,'injury':st or 'none listed','aid':a['id'],'stat':'td','line':0.5,'ou':'over',
    'fd_market_id':m['marketId'],'fd_selection_id':r['selectionId'],'team_total':tt})
tcov.update(players_matched=len(td),excluded_injury=sorted(excl),unmatched=len(nomatch))
tpool=sorted([L for L in td if L['odds']<=250 and L['prob']>=0.25],key=lambda L:-L['prob'])
td_tix=ladder(tpool,6,2,1,4,'td')
for t in sorted([t for t in td_tix if 2<=t['n']<=3],key=lambda t:-t['ev'])[:2]: t['favorite']=True
# ======================= NBA THREES & REBOUNDS =======================
npairs,nmk=fdpairs('nba',['player-threes','player-rebounds'])
PIN_NB=pin_props(487,{'Total Threes Made':'threePointFieldGoalsMade','Total Rebounds':'totalRebounds'})
SPEC={'THREES':('threePointFieldGoalsMade','made threes'),'REBOUNDS':('totalRebounds','rebounds')}
nb=[]; ncov={'games':len(npairs),'fd_lines':0,'players_matched':0,'pinnacle_priced':0,'excluded_injury':[],'unmatched':0}; excl=set(); nomatch=set(); raw=[]; need={}
for (g,e),mk in zip(npairs,nmk):
  R=rost('basketball','nba',g)
  for m in mk.values():
    mt=m['marketType']
    if m.get('marketStatus')!='OPEN' or m.get('inPlay') or re.search('QUARTER|HALF|FIRST',mt): continue
    rs=[r for r in m['runners'] if r.get('runnerStatus')=='ACTIVE' and r.get('winRunnerOdds',{}).get('americanDisplayOdds')]
    th=[]; mm=re.fullmatch(r'TO_RECORD_(\d+)\+_(REBOUNDS)',mt) or re.fullmatch(r'(\d+)\+_MADE_(THREES)',mt)
    if mm: th=[(r,r['runnerName'],int(mm.group(1))-0.5,'over',imp(od(r))/1.07,SPEC[mm.group(2)]) for r in rs]
    mm=re.fullmatch(r'PLAYER_[A-Z]_TOTAL_(REBOUNDS|MADE_THREES|THREES)',mt)
    if mm and len(rs)==2:
      S=sum(imp(od(r)) for r in rs); sp_=SPEC['REBOUNDS' if 'REB' in mt else 'THREES']
      th=[(r,r['runnerName'].rsplit(' ',1)[0],r['handicap'],r['runnerName'].rsplit(' ',1)[1].lower(),imp(od(r))/S,sp_) for r in rs]
    for r,pl,line,ou,p,sp_ in th:
      if ou not in('over','under'): continue
      ncov['fd_lines']+=1; side=next((s for s in R if pname(pl) in R[s]),None)
      if not side: nomatch.add(pl); continue
      a=R[side][pname(pl)]; raw.append((g,m,r,pl.strip(),float(line),ou,p,sp_,side,a,R)); need[a['id']]=1
def ngl(aid): return aid,(gamelog('basketball','nba',aid),gamelog('basketball','nba',aid,'2026',ttl=30*86400))
with ThreadPoolExecutor(12) as ex: GL=dict(ex.map(ngl,need))
def nopp(tid): return tid,opp_box('basketball','nba',tid,10)
with ThreadPoolExecutor(8) as ex: NOPP=dict(ex.map(nopp,{g['teams'][s]['tid'] for g,*_ in npairs for s in('home','away')}))
def split(v):
  try: return [float(x) for x in v.split('-')]
  except Exception: return None
def tstats(tid):  # opponent 3PA allowed, rebounds allowed, pace (possessions) per game, last<=10 games
  G=NOPP.get(tid,([],[]))[0]
  if not G: return None
  def poss(t): fg=split(t.get('fieldGoalsMade-fieldGoalsAttempted','')); ft=split(t.get('freeThrowsMade-freeThrowsAttempted',''))
  P=[];A=[];RB=[]
  for x in G:
    t=x['team']; th=split(t.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted',''))
    if th: A.append(th[1])
    try: RB.append(float(t.get('totalRebounds')))
    except Exception: pass
    pp=[]
    for s in (x['team'],x['me']):
      fg=split(s.get('fieldGoalsMade-fieldGoalsAttempted','')); ft=split(s.get('freeThrowsMade-freeThrowsAttempted',''))
      try: pp.append(fg[1]+0.44*ft[1]-float(s['offensiveRebounds'])+float(s.get('totalTurnovers') or s['turnovers']))
      except Exception: pass
    if len(pp)==2: P.append(sum(pp)/2)
  av=lambda v:sum(v)/len(v) if v else None
  return {'3pa':av(A),'reb':av(RB),'pace':av(P),'n':len(G)}
TS={tid:tstats(tid) for tid in NOPP}
def lav(k):
  v=[x[k] for x in TS.values() if x and x.get(k)]; return sum(v)/len(v) if v else None
LA={k:lav(k) for k in('3pa','reb','pace')}
yday=(ET-datetime.timedelta(days=1)).strftime('%Y-%m-%d')
for g,m,r,pl,line,ou,p,sp_,side,a,R in raw:
  st=inj(a)
  if st.lower() in BAD: excl.add(f"{pl} ({st})"); continue
  cur,prev=GL.get(a['id'],({},{})); rc=glrows(cur); rp=glrows(prev)[:20]
  if not rc: continue
  f=sp_[0]; hit=lambda x:(x.get(f,0)>line) if ou=='over' else (x.get(f,0)<line)
  pk=PIN_NB.get((pname(pl),f)); pin=None
  if pk:
    lam=fit_lam(pk['line'],pk['p_over']) if f.startswith('three') else None
    if lam is not None: po=pois_ge(lam,int(line)+1)
    else:  # rebounds: normal with var = 1.3*mean, mean solved from Pinnacle line
      mu=pk['line']; 
      for _ in range(40): mu+= (pk['p_over']-(1-ncdf((pk['line']-mu)/sqrt(1.3*max(mu,1)))))*2
      po=1-ncdf((line-mu)/sqrt(1.3*max(mu,1)))
    pin=po if ou=='over' else 1-po; ncov['pinnacle_priced']+=1
  mkt=0.5*p+0.5*pin if pin is not None else p
  hw=sum(hit(x) for x in rc)+0.4*sum(hit(x) for x in rp); n=len(rc)+0.4*len(rp); pemp=(hw+6*mkt)/(n+6)
  pr=0.5*mkt+0.5*pemp
  l5=rc[:5]; l10=(rc+rp)[:10]
  why=[f"this season {sum(hit(x) for x in rc)}/{len(rc)} (avg {sum(x.get(f,0) for x in rc)/len(rc):.1f})",f"last 5 {sum(hit(x) for x in l5)}/{len(l5)}",f"last 10 incl. 2025-26 {sum(hit(x) for x in l10)}/{len(l10)}"]
  mins=[x.get('minutes') for x in rc if x.get('minutes')]; pm=[x.get('minutes') for x in rp if x.get('minutes')]
  if mins and pm:
    rt=(sum(mins[:3])/len(mins[:3]))/(sum(pm)/len(pm))
    if rt<0.8: pr+=-0.04 if ou=='over' else 0.02; why.append(f"minutes down ({sum(mins[:3])/len(mins[:3]):.0f} vs {sum(pm)/len(pm):.0f})")
    elif rt>1.15: pr+=0.01 if ou=='over' else -0.01; why.append(f"minutes up ({sum(mins[:3])/len(mins[:3]):.0f} vs {sum(pm)/len(pm):.0f})")
  if f.startswith('three'):
    at=[x.get('threePointFieldGoalsAttempted',0) for x in rc]; ap=[x.get('threePointFieldGoalsAttempted',0) for x in rp]
    why.append(f"3PA {sum(at)/len(at):.1f}/g this season"+(f" vs {sum(ap)/len(ap):.1f} late 2025-26" if ap else ''))
  ot='away' if side=='home' else 'home'; T=TS.get(g['teams'][ot]['tid']); adj=0
  if T and LA['3pa'] and f.startswith('three') and T['3pa']: adj+=max(-.03,min(.03,(T['3pa']/LA['3pa']-1)*0.3)); why.append(f"{g['teams'][ot]['short']} allow {T['3pa']:.1f} opp 3PA/g vs {LA['3pa']:.1f} slate avg")
  if T and LA['reb'] and f=='totalRebounds' and T['reb']: adj+=max(-.03,min(.03,(T['reb']/LA['reb']-1)*0.4)); why.append(f"{g['teams'][ot]['short']} allow {T['reb']:.1f} opp reb/g vs {LA['reb']:.1f}")
  Tm=TS.get(g['teams'][side]['tid'])
  if T and Tm and LA['pace'] and T['pace'] and Tm['pace']: pc=(T['pace']+Tm['pace'])/2; adj+=max(-.02,min(.02,(pc/LA['pace']-1)*0.4)); why.append(f"expected pace {pc:.0f} poss vs {LA['pace']:.0f}")
  pr+=adj if ou=='over' else -adj
  mo=[x.get('fullName') for x in R[side].values() if inj(x).lower()=='out' and x['id']!=a['id']]
  if mo and ou=='over': pr+=0.01; why.append('teammates out: '+', '.join(mo[:3])+' (+1 pt)')
  b2b=any(d[:10]==yday for d in NOPP.get(g['teams'][side]['tid'],([],[]))[1])
  if b2b: pr+=-0.02 if ou=='over' else 0.01; why.append('back-to-back (played yesterday) -2 pts')
  if pin is not None: why.append(f"Pinnacle {pk['line']:g} line implies {pin*100:.1f}% here")
  # 2026-10-28 review: graded nba3r through 10-27 - rebounds over 68.3% vs 74.9% model (104), under 54.5% vs 63.7% (33); threes 73.0% vs 77.8% (159).
  hc=(0.06 if ou=='over' else 0.08) if f=='totalRebounds' else 0.03
  pr-=hc; why.append(f"{'rebounds' if f=='totalRebounds' else 'threes'} calibration haircut -{hc*100:.0f} pts (hit below estimate so far)")
  nb.append({'haircut':hc,'id':f"{g['id']}:{r['selectionId']}:{m['marketId']}",'event':g['id'],'sport':'nba','game':g['name'],'start':g['start'],'market':m['marketName'],'player':pl,'team':g['teams'][side]['name'],
    'pick':f"{pl} {'Over' if ou=='over' else 'Under'} {line:g} {sp_[1]}" if '+' not in m['marketType'] else f"{pl} {int(line+0.5)}+ {sp_[1]}",'stat':f,'line':line,'ou':ou,'odds':od(r),
    'fd_prob':round(min(p,.995),4),'pin_prob':round(pin,4) if pin is not None else None,'emp_prob':round(pemp,4),'prob':round(max(.01,min(.97,pr)),4),'why':'; '.join(why),'asof':NOW,
    'injury':st or 'none listed','aid':a['id'],'fd_market_id':m['marketId'],'fd_selection_id':r['selectionId']})
ncov.update(players_matched=len({L['player'] for L in nb}),excluded_injury=sorted(excl),unmatched=len(nomatch),lines_scored=len(nb))
# 2026-10-29 review: rebound UNDERS hit 22/42 (52%) here and 9/20 in Player Props vs ~63% est after haircut - excluded.
cand=[L for L in nb if -1000<=L['odds']<=150 and L['prob']>=0.6 and L['prob']+L.get('haircut',0)-L['fd_prob']>=-0.02 and not(L['stat']=='totalRebounds' and L['ou']=='under')]  # FD-gap check before the haircut
byp={}
for L in cand:
  if L['player'] not in byp or (L['prob'],L['odds'])>(byp[L['player']]['prob'],byp[L['player']]['odds']): byp[L['player']]=L
npool=sorted(byp.values(),key=lambda L:-L['prob'])
nb_tix=ladder(npool,15,2,2,5,'nba3r')
for t in sorted([t for t in nb_tix if t['est_prob']>=0.5 and t['n']>=2],key=lambda t:-t['ev'])[:3]: t['favorite']=True
# ======================= history + grading =======================
H=load('extra2.history.json',{'legs':{},'tickets':{}}); DATE=(ET-datetime.timedelta(hours=1)).strftime('%Y-%m-%d')
keep=lambda L:{k:L.get(k) for k in('id','event','sport','game','start','market','pick','player','aid','stat','line','ou','odds','prob','fd_prob')}
for typ,pool,tix in(('td',tpool,td_tix),('nba3r',npool,nb_tix)):
  for L in pool:
    if ts(L['start'])>now: H['legs'][L['id']]={**keep(L),'type':typ,'date':DATE,'logged':NOW}
  for t in tix:
    k=f"{typ}:{DATE}:{t['n']}"; old=H['tickets'].get(k)
    if not(old and any(ts(H['legs'][i]['start'])<=now for i in old['legs'] if i in H['legs'])): H['tickets'][k]={'type':typ,'date':DATE,'n':t['n'],'legs':t['legs'],'est_prob':t['est_prob'],'logged':NOW}
def grade(x):
  if (now-ts(x['start'])).total_seconds()<3.5*3600: return None
  sp='football' if x['sport']=='nfl' else 'basketball'
  r=next((r for r in glrows(gamelog(sp,x['sport'],x['aid'],ttl=1800)) if r['eid']==x['event']),None)
  if not r: return 'void' if (now-ts(x['start'])).total_seconds()>36*3600 else None
  v=r.get('rushingTouchdowns',0)+r.get('receivingTouchdowns',0) if x['stat']=='td' else r.get(x['stat'],0)
  return 'won' if ((v>x['line']) if x['ou']=='over' else (v<x['line'])) else 'lost'
for x in H['legs'].values():
  if not x.get('result'):
    try: x['result']=grade(x)
    except Exception as e: print('grade fail',x['id'],e)
for t in H['tickets'].values():
  if t.get('result'): continue
  rs=[H['legs'].get(i,{}).get('result') for i in t['legs']]
  if 'lost' in rs: t['result']='lost'
  elif rs and all(r in('won','push','void') for r in rs): t['result']='won'
json.dump(H,open('extra2.history.json','w'))
def st(typ):
  G=[x for x in H['legs'].values() if x['type']==typ and x.get('result') in('won','lost')]; T=[t for t in H['tickets'].values() if t['type']==typ and t.get('result')]; b={}
  for x in G:
    k=f"{int(x['prob']*10)*10}-{int(x['prob']*10)*10+10}%"; s=b.setdefault(k,{'n':0,'w':0,'p':0}); s['n']+=1; s['w']+=x['result']=='won'; s['p']+=x['prob']
  return {'graded_legs':len(G),'won':sum(x['result']=='won' for x in G),'hit':round(sum(x['result']=='won' for x in G)/len(G),4) if G else None,'expected':round(sum(x['prob'] for x in G)/len(G),4) if G else None,
    'tickets_graded':len(T),'tickets_won':sum(t['result']=='won' for t in T),'buckets':{k:{'n':v['n'],'hit':round(v['w']/v['n'],4),'pred':round(v['p']/v['n'],4)} for k,v in sorted(b.items())}}
for L in tpool+npool: L['fd_link']=fdlink([L])
out={'updated':NOW,
 'td':{'legs':{L['id']:L for L in tpool},'parlays':td_tix,'coverage':tcov,'stats':st('td'),
  'rule':"Pregame only, FanDuel PA 'Any Time Touchdown Scorer' (rushing/receiving TDs; ESPN grading also counts only those). Chance = 50% market (Pinnacle no-vig 'Total Touchdowns over 0.5' when listed, else FanDuel price minus ~22% margin) + 50% ESPN game-log TD rate (this season, 2025 at half weight, shrunk toward market), then adjustments: implied team total from ESPN spread/total (±3 pts), opponent rush/receiving TDs allowed in its last 6 games (±2), touches trend, same-position teammate Out (+2); total adjustment capped ±5 pts and never more than 8 pts above the market. Out/Doubtful/Questionable/IR excluded. Max 1 leg per team, 2 per game; legs priced +250 or shorter with est. chance ≥25%. 2+ TD markets skipped (too unlikely). TD legs are coin flips at best, so read each ticket's chance honestly."},
 'nba3r':{'legs':{L['id']:L for L in npool},'parlays':nb_tix,'coverage':ncov,'stats':st('nba3r'),
  'rule':"Pregame only, FanDuel PA made-threes and rebounds (main and alt lines). One leg per player (his highest-chance line −1000 to +150), max 2 per game, each leg in at most 5 tickets, est. chance ≥60% and not more than 2 pts below FanDuel's no-vig. Chance = 50% market (FanDuel no-vig, averaged with Pinnacle's line converted to this threshold when listed) + 50% ESPN game-log hit rate (this season + last 20 games of 2025-26 at 40% weight, shrunk), then: minutes trend, opponent 3PA / rebounds allowed and pace from their last ≤10 box scores (±3/±3/±2 pts), teammates out (+1), back-to-back (−2), then a calibration haircut (rebounds −6 pts; threes −3) because these have hit below estimate so far. Rebound unders are excluded (they hit about 50% so far). Out/Doubtful/Questionable/Day-To-Day excluded."}}
# Keep last board when a fetch failure empties a tab but its prior legs are still pregame.
try:
  _prev=json.load(open('extra2.json'))
  _iso=now.strftime('%Y-%m-%dT%H:%MZ')
  for _k in ('td','nba3r'):
    _pl=(_prev.get(_k) or {}).get('legs') or {}
    if not out[_k]['legs'] and _pl:
      _keep={i:L for i,L in _pl.items() if L.get('start','')>_iso}
      if _keep:
        _ok=set(_keep); _pt=[t for t in (_prev[_k].get('parlays') or []) if all((x if isinstance(x,str) else x.get('id')) in _ok for x in (t.get('legs') or []))]
        out[_k].update({'legs':_keep,'parlays':_pt,'coverage':dict(_prev[_k].get('coverage') or {},stale_since=_prev.get('updated'))}); print('kept last',_k,'board (fetch empty):',len(_keep),'legs',len(_pt),'tix')
except Exception as _e: print('keep-last check failed',_e)
json.dump(out,open('extra2.json','w'),indent=1)
print('TD games',len(tpairs),'sel',tcov['fd_selections'],'scored',len(td),'pool',len(tpool),'tix',len(td_tix),'pin',tcov['pinnacle_priced'],'| NBA games',len(npairs),'lines',ncov['fd_lines'],'scored',len(nb),'pool',len(npool),'tix',len(nb_tix),'pin',ncov['pinnacle_priced'])
