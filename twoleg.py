"""Best 2-Leg Parlays (pregame). Strict bar calibrated from graded shadow legs (all v1 candidate legs logged each refresh).
Bar: each leg's calibrated chance >= LEG_BAR and joint >= JOINT_BAR, per-game top leg only (v1_top), no two legs from one game,
each leg used once, NHL 0.85+ capped at 0.80 (same as build.py), haircuts already in v1 probs. Quality first: zero tickets is allowed.
Writes twoleg.json (board + record + backtest) and twoleg.history.json (locks at first kickoff, graded from shadow.json)."""
import json,collections,datetime,itertools
def load(f,d):
  try: return json.load(open(f))
  except Exception: return d
LEG_BAR=0.92; JOINT_BAR=0.85; M=15
now=datetime.datetime.now(datetime.timezone.utc)
P=load('picks.json',{}); DATE=P.get('date'); SH=load('shadow.json',{'legs':{}})['legs']
def grp(sp): return 'soccer' if '.' in sp else sp
def p1(r):
  p=r.get('v1') or r.get('prob') or 0
  return min(p,0.80) if r['sport']=='nhl' and p>=0.85 else p
G=[r for r in SH.values() if r.get('result') in('win','loss') and r.get('v1') is not None]
def calib(excl=None):
  B=collections.defaultdict(lambda:[0,0])
  for r in G:
    if r['date']==excl: continue
    k=(grp(r['sport']),int(p1(r)*40)); B[k][0]+=1; B[k][1]+=r['result']=='win'
  return B
def cp(r,B):
  p=p1(r); n,w=B.get((grp(r['sport']),int(p*40)),[0,0]); return (w+M*p)/(n+M)
def pairs(rows,B):
  L=sorted([(cp(r,B),r) for r in rows if r.get('v1_top')],key=lambda x:-x[0]); used=set(); q=[]
  for c,r in L:
    if c<LEG_BAR or r['event'] in used: continue
    used.add(r['event']); q.append((c,r))
  out=[]
  for i in range(0,len(q)-1,2):
    (c1,a),(c2,b)=q[i],q[i+1]
    if c1*c2>=JOINT_BAR: out.append(((a,c1),(b,c2),c1*c2))
  return out
# backtest (leave-one-day-out calibration, so no day grades itself)
bt=[];
for d in sorted({r['date'] for r in G}):
  B=calib(d)
  for (a,_),(b,_),j in pairs([r for r in G if r['date']==d],B): bt.append({'date':d,'joint':round(j,3),'won':a['result']=='win' and b['result']=='win'})
grid=[]
for lb in (0.80,0.86,0.88,0.90,0.92):
  B0=LEG_BAR; globals()['LEG_BAR']=lb; n=w=0
  for d in sorted({r['date'] for r in G}):
    B=calib(d)
    for (a,_),(b,_),j in pairs([r for r in G if r['date']==d],B): n+=1; w+=a['result']=='win' and b['result']=='win'
  grid.append({'leg_bar':lb,'tickets':n,'won':w,'win_pct':round(w/n,3) if n else None}); LEG_BAR=B0
# today's board
B=calib(); LEGS=P.get('legs',{})
def started(r): return datetime.datetime.fromisoformat(r['start'].replace('Z','+00:00'))<=now
today=[r for r in SH.values() if r.get('date')==DATE and r.get('result') is None and r.get('start') and not started(r)]
def link(ids): return 'https://sportsbook.fanduel.com/addToBetslip?'+'&'.join(f"marketId%5B{i}%5D={x.split(':')[2]}&selectionId%5B{i}%5D={x.split(':')[1]}" for i,x in enumerate(ids))
def leg(r,c): return {'id':r['id'],'event':r['event'],'sport':r['sport'],'pick':r['pick'],'market':r.get('market'),'game':r['game'],'start':r['start'],
  'odds':r.get('odds_last') or r.get('odds_first'),'model':round(p1(r),4),'calibrated':round(c,4),'fd_link':link([r['id']]),'result':None,
  'why':(LEGS.get(r['id']) or {}).get('why')}
board=[]
for (a,c1),(b,c2),j in pairs(today,B):
  if any(len(r['id'].split(':'))<3 for r in (a,b)): continue
  board.append({'id':f"{DATE}-2L-{a['id']}-{b['id']}",'date':DATE,'n':2,'joint':round(j,4),'legs':[leg(a,c1),leg(b,c2)],'fd_link':link([a['id'],b['id']])})
nearmiss=sorted([{'pick':r['pick'],'game':r['game'],'sport':r['sport'],'start':r['start'],'calibrated':round(cp(r,B),3)} for r in today if r.get('v1_top')],key=lambda x:-x['calibrated'])[:6]
# history: tickets added while pregame; unlocked ones that drop below the bar are removed; lock at first leg start; grade from shadow
H={x['id']:x for x in load('twoleg.history.json',[])}
for k in [k for k,x in H.items() if x['date']==DATE and not x.get('locked')]:
  if k not in {t['id'] for t in board}: H.pop(k)
for t in board:
  if t['id'] not in H or not H[t['id']].get('locked'): H[t['id']]={**t,'logged':now.strftime('%Y-%m-%d %H:%M UTC'),'locked':False,'result':None}
for x in H.values():
  if any(started(l) for l in x['legs']): x['locked']=True
  for l in x['legs']:
    if l.get('result') is None: l['result']=(SH.get(l['id']) or {}).get('result')
  r=[l['result'] for l in x['legs']]
  x['result']='loss' if 'loss' in r else 'win' if all(v in('win','void') for v in r) else None
hist=sorted(H.values(),key=lambda x:(x['date'],x['id']),reverse=True)
json.dump(hist,open('twoleg.history.json','w'),indent=1)
gr=[x for x in hist if x['result']]; w=sum(x['result']=='win' for x in gr)
bw=sum(x['won'] for x in bt)
json.dump({'updated':now.strftime('%Y-%m-%d %H:%M UTC'),'date':DATE,'bar':{'leg':LEG_BAR,'joint':JOINT_BAR,'shrink_m':M},
 'board':board,'near_miss':nearmiss,
 'record':{'won':w,'lost':len(gr)-w,'pending':len(hist)-len(gr),'win_pct':round(w/len(gr),3) if gr else None},
 'backtest':{'tickets':len(bt),'won':bw,'win_pct':round(bw/len(bt),3) if bt else None,'avg_joint':round(sum(x['joint'] for x in bt)/len(bt),3) if bt else None,'days':len({r['date'] for r in G}),'grid':grid,'tickets_detail':bt},
 'rule':f"A 2-leg ticket qualifies only if both legs are their game's top-rated pregame leg, from different games, each calibrated to at least {LEG_BAR*100:.0f}% from graded history (sport + 2.5-pt bucket, shrunk toward the model with weight {M}), and the joint chance is at least {JOINT_BAR*100:.0f}%. NHL 85%+ legs are capped at 80% first, and the existing haircuts apply. No padding: some days nothing qualifies. Nothing is guaranteed."},open('twoleg.json','w'),indent=1)
print('twoleg board',len(board),[t['joint'] for t in board],'backtest',bw,'/',len(bt),'record',w,len(gr)-w)
