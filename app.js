const $=id=>document.getElementById(id);
function load(){fetch('picks.json?'+Date.now()).then(r=>r.json()).then(d=>{
const L=Object.fromEntries(d.legs.map(l=>[l.id,l]));
$('upd').textContent='Last updated: '+d.updated+' · slate '+d.date;
const odd=l=>`<span class=${l.verified?'v':'u'}>${l.odds}</span>`;
const leg=l=>`<div class=leg><b>${l.market}</b> · ${l.game} <small>(${l.status})</small><br>${odd(l)} · est. <span class=p>${Math.round(l.prob*100)}%</span>${l.result?' · <b>'+l.result.toUpperCase()+'</b>':''}<br>${l.why} <a href="${l.src}" target=_blank rel=noopener>source</a></div>`;
$('parlays').innerHTML=`<div class=card>${d.note} Green odds = verified FanDuel; amber = check FanDuel.</div>`+d.parlays.map(p=>`<details class=card ${p.legs_count<=2?'open':''}><summary><b>${p.legs_count}-leg</b> · est. hit ${(p.est_prob*100).toFixed(p.est_prob<.01?2:1)}% · ${p.fd_verified_legs}/${p.legs_count} FanDuel-verified</summary>${p.legs.map(i=>leg(L[i])).join('')}</details>`).join('');
$('legs').innerHTML=[...d.legs].sort((a,b)=>b.prob-a.prob).map(l=>`<div class=card>${leg(l)}</div>`).join('');
$('games').innerHTML=d.games.map(g=>{const t=Object.entries(g.teams).map(([n,x])=>`${n} ${x.score??''}`).join(' — ');return `<div class=card><small>${g.sport.toUpperCase()}</small> ${g.state=='in'?'<span class=live>LIVE</span> ':''}<b>${t}</b><br><small>${g.status} · ${g.line||''} ${g.total?'O/U '+g.total:''} ${g.book?'('+g.book+')':''}</small></div>`}).join('');
const ri=()=>{const q=$('q').value.toLowerCase();$('injl').innerHTML=d.injuries.filter(i=>(i.team+i.t).toLowerCase().includes(q)).map(i=>`<div class=card><b>${i.team}</b>: ${i.t}<br><small>${i.src}</small></div>`).join('')};$('q').oninput=ri;ri();
$('wx').innerHTML=d.weather.map(w=>`<div class=card><b>${w.g}</b>: ${w.w} <small>(${w.src})</small></div>`).join('')||'<div class=card>No outdoor games.</div>';
$('lines').innerHTML='<div class=card>Moneyline open → now (ESPN/DraftKings feed; snapshots stored in lines.history.json each refresh)</div>'+d.moves.map(m=>`<div class=card>${m.team} <small>(${m.g})</small>: ${m.open} → <b>${m.now}</b></div>`).join('');
})}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('on',x==b));document.querySelectorAll('main section').forEach(s=>s.hidden=s.id!=b.dataset.t)});
load();setInterval(load,120000);
