// Best 2-Leg Parlays tab + enhanced Track record (record.json). Times shown in Eastern.
(function(){
const $=id=>document.getElementById(id),pc=p=>p==null?'–':(p*100).toFixed(1)+'%';
const tm=s=>new Date(s).toLocaleString('en-US',{timeZone:'America/New_York',weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' ET';
const fb=(u,t)=>u?`<a class=fdbtn data-pa="${u}" href="${u}">${t}</a>`:'';
const od=o=>o==null?'':(o>0?'+':'')+o, ic=r=>r=='win'?'✅':r=='loss'?'❌':r=='void'?'↩️':'⏳';
function two(){fetch('twoleg.json?'+Date.now()).then(r=>r.json()).then(x=>{
 const b=x.backtest||{},r=x.record||{};
 let h=`<div class=card><h2>✌️ Best 2-Leg Parlays</h2><p>${x.rule}</p><table><tr><th></th><th>Tickets</th><th>Won</th><th>Win %</th></tr><tr><td>Backtest at this bar (${b.days} graded days)</td><td>${b.tickets}</td><td>${b.won}</td><td>${pc(b.win_pct)}</td></tr><tr><td>Live record (since Oct 31)</td><td>${(r.won||0)+(r.lost||0)}</td><td>${r.won||0}</td><td>${pc(r.win_pct)}</td></tr></table><small>Backtest sample is small, so treat it as a strict filter, not a promise. Looser bars won less: ${(b.grid||[]).map(g=>`${(g.leg_bar*100).toFixed(0)}%+ legs: ${g.won}/${g.tickets}`).join(' · ')}. Updated ${tm(x.updated.replace(' UTC','Z').replace(' ','T'))}.</small></div>`;
 h+=(x.board||[]).map(t=>`<div class="card fav"><h3>2-leg parlay · calibrated chance ${pc(t.joint)}</h3>${fb(t.fd_link,'Bet this 2-leg parlay on FanDuel')}${t.legs.map(l=>`<div class=leg>${fb(l.fd_link,'Bet single')}<b>${l.pick}</b> · ${l.market||''}<br><small>${l.game} · ${tm(l.start)}</small><br>${od(l.odds)} · calibrated ${pc(l.calibrated)} <small>(model ${pc(l.model)})</small>${l.why?`<br><small class=why>Why: ${l.why}</small>`:''}</div>`).join('')}</div>`).join('')
  ||`<div class=card><b>No 2-leg parlay meets the bar right now.</b> Quality first, so nothing is padded in. Closest legs today (need ${(x.bar.leg*100).toFixed(0)}%+ each):<ul>${(x.near_miss||[]).map(n=>`<li>${n.pick} · ${n.game} · ${tm(n.start)} · ${pc(n.calibrated)}</li>`).join('')}</ul></div>`;
 $('twoleg').innerHTML=h+'<div class=card><small>Nothing is guaranteed. Bet only what you can afford to lose.</small></div>';
}).catch(()=>{})}
let R=null,F='all',LIM=30;
const TL={ladder:'Ladder',best:'Best Parlay',lottery:'Lottery',twoleg:'2-Leg',green:"👑 Green (King's Favorites)"};
function rows(){return (R.tickets||[]).filter(t=>F=='all'||(F=='green'?t.favorite:F=='loss'?t.result=='loss':t.type==F))}
function drawRec(){if(!R)return;const by=R.by_type||{},o=R.overall||{};
 let h=`<div class=card><h2>📒 Full ticket record</h2><p>Every graded ticket with each leg's result, why it won or lost, and what we changed. Updated ${R.updated_et}. ${R.pending} pending.</p><table><tr><th>Type</th><th>W-L</th><th>Win %</th></tr><tr><td><b>All</b></td><td>${o.won}-${o.lost}</td><td>${pc(o.win_pct)}</td></tr>${Object.entries(by).map(([k,v])=>`<tr><td>${TL[k]||k}</td><td>${v.won}-${v.lost}</td><td>${pc(v.win_pct)}</td></tr>`).join('')}</table>
 <div class=rf>${['all','green','twoleg','ladder','best','lottery','loss'].map(k=>`<button data-f=${k} class="${F==k?'on':''}">${k=='all'?'All':k=='loss'?'Losses only':TL[k]}</button>`).join('')}</div></div>`;
 const xs=rows();let last='';
 h+=xs.slice(0,LIM).map(t=>{let d='';if(t.date!=last){last=t.date;const bd=(R.by_day||{})[t.date]||{};d=`<h3 class=rday>${new Date(t.date+'T12:00:00Z').toLocaleDateString('en-US',{timeZone:'America/New_York',weekday:'long',month:'short',day:'numeric'})} · ${bd.won}-${bd.lost}</h3>`}
  return d+`<details class="card rt ${t.favorite?'fav':''}"><summary>${ic(t.result)} <b>${t.label}</b>${t.favorite?' 👑':''} · ${t.n} legs · est. ${pc(t.est)}${t.payout_x?` · ~${t.payout_x}x`:''}</summary>
  <p><b>Why it ${t.result=='win'?'won':'lost'}:</b> ${t.reason}</p><p><b>What we learned / changed:</b></p><ul>${t.learned.map(s=>`<li>${s}</li>`).join('')}</ul>
  <p><small><b>Review ${t.review.title}:</b> ${t.review.changes||'No change.'}</small></p>${t.logged_et?`<small>Logged ${t.logged_et}</small>`:''}
  <ul class=rlegs>${t.legs.map(l=>`<li>${ic(l.result)} ${l.pick} <small>(${od(l.odds)} · ${pc(l.est)} · ${l.game}${l.final?' · final '+l.final:''}${l.margin!=null?' · margin '+(l.margin>0?'+':'')+l.margin:''}${l.tags&&l.tags.length?' · '+l.tags.join(', '):''})</small></li>`).join('')}</ul></details>`}).join('');
 if(xs.length>LIM)h+=`<button class="card rmore">Show more (${xs.length-LIM} left)</button>`;
 h+=`<details class=card><summary><b>Review log (improvements.md)</b></summary>${(R.reviews||[]).map(r=>`<p><b>${r.title}</b><br><small>${r.changes}</small></p>`).join('')}</details><div class=card><small>Nothing is guaranteed.</small></div>`;
 $('trkr').innerHTML=h;
 $('trkr').querySelectorAll('.rf button').forEach(b=>b.onclick=()=>{F=b.dataset.f;LIM=30;drawRec()});
 const m=$('trkr').querySelector('.rmore');if(m)m.onclick=()=>{LIM+=30;drawRec()};}
function rec(){fetch('record.json?'+Date.now()).then(r=>r.json()).then(x=>{R=x;drawRec()}).catch(()=>{})}
two();rec();setInterval(()=>{two();rec()},300000);
})();
