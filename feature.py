"""Best Parlay per-leg breakdown, built only from fetched sources; missing data -> 'not found'."""
NF='not found'
def M(x,t,ab):
  tm=x.get('team',{}); return t['name'] in (tm.get('displayName'),tm.get('name')) or ab in (tm.get('abbreviation'),tm.get('shortDisplayName'))
def build(bestp,legs,games,cands,moves,wx,inj,get,SPORTS):
  if not bestp: return None
  G={g['id']:g for g in games}; out=[]
  for i in bestp['legs']:
    L=legs[i]; g=G[L['event']]; sp=L['sport']
    s=get(f"https://site.api.espn.com/apis/site/v2/sports/{SPORTS[sp]}/{sp}/summary?event={g['id']}",1800) or {}
    teams={}
    for side in('away','home'):
      t=g['teams'][side]; ab=t['short']
      l5=next((x for x in s.get('lastFiveGames',[]) if M(x,t,ab)),None)
      l5s=', '.join(f"{e.get('gameResult')} {e.get('score')} {e.get('atVs')} {e.get('opponent',{}).get('abbreviation')}" for e in (l5 or {}).get('events',[])) or NF
      ij=next((x for x in s.get('injuries',[]) if M(x,t,ab)),None)
      ijs=[f"{x['athlete']['displayName']}: {x['status']}" for x in (ij or {}).get('injuries',[])]
      ijs+= [n['t'] for n in inj if n.get('team')==t['name'] and 'X' in str(n.get('src',''))]
      ld=next((x for x in s.get('leaders',[]) if M(x,t,ab)),None)
      lds=[f"{c['displayName'] if 'displayName' in c else c['name']}: {c['leaders'][0]['athlete']['displayName']} {c['leaders'][0]['displayValue']}" for c in (ld or {}).get('leaders',[]) if c.get('leaders')][:3]
      teams[side]={'name':t['name'],'record':t.get('record') or NF,'last5':l5s+(' (ESPN; may include preseason)' if l5 else ''),
        'injuries':'; '.join(ijs) if ij is not None else NF,'injuries_none_listed':ij is not None and not ijs,'leaders':'; '.join(lds) or NF}
    pr=s.get('predictor') or {}
    pred=f"ESPN BPI: home {pr.get('homeTeam',{}).get('gameProjection')}% / away {pr.get('awayTeam',{}).get('gameProjection')}%" if pr else NF
    ss=(s.get('seasonseries') or [{}])[0].get('summary') or NF
    alts=sorted([c for c in cands if c['event']==g['id'] and c['odds']>=-300],key=lambda c:-c['prob'])
    nxt=[f"{c['pick']} ({c['market']}, {c['odds']:+d}, {c['prob']*100:.1f}%)" for c in alts[1:4]]
    mv=[f"{m['team']} ML {m['open']} -> {m['now']} ({m['src']})" for m in moves if m['g']==g['name']]
    w=next((x for x in wx if x.get('g')==g['name']),None)
    out.append({'id':i,'game':g['name'],'start':g['start'],'pick':L['pick'],'market':L['market'],'odds':L['odds'],
      'odds_status':'FanDuel-verified (FanDuel public sportsbook API, NJ)' if L.get('verified') else 'check FanDuel',
      'teams':teams,'h2h':ss,'rest_travel':NF,'coaching':NF,
      'venue':f"{g.get('venue') or NF}{' (indoor)' if g.get('indoor') else ''}",'weather':'indoor - n/a' if g.get('indoor') else (w and f"{w.get('w')} ({w.get('src')})") or NF,
      'line_moves':'; '.join(mv) or 'no recorded move','sharp_public':NF+' (no free public betting-split source)',
      'espn_line':f"{g.get('book') or 'ESPN'}: {g.get('line') or NF}, O/U {g.get('total') or NF}",'predictor':pred,
      'probs':{'fanduel_no_vig':L.get('fd_prob'),'distribution_model':L.get('dist_prob'),'team_model':L.get('model'),'final':L['prob']},
      'why':f"Highest blended win probability of {len(alts)} FanDuel markets priced -300 or longer for this game. Next best: "+('; '.join(nxt) or 'none')})
  return {'criteria':'Per game, the highest-probability FanDuel market priced -300 or longer (so each leg pays something); one leg per game, games not started; choose 3-6 legs maximizing P(win) x ln(payout) with payout >= 3.5x.',
          'n':bestp['n'],'est_prob':bestp['est_prob'],'fd_payout_x':bestp['fd_payout_x'],'legs':out}
