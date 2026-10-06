// 888WIN demo — créditos virtuais, sem dinheiro real. +18 educacional.
const $=s=>document.querySelector(s);
let balance=parseFloat(localStorage.getItem('win888_balance')??'1000');
if(isNaN(balance))balance=1000;
let history=JSON.parse(localStorage.getItem('win888_history')||'[]');
let walletMode='deposit', currentCat='slots', crashTimer=null, crashState=null;
// Config de estudo: RTP alvo exibido de forma transparente (padrão justo).
// Não configuramos 12% escondido para operação real: seria predatório e
// provavelmente ilegal sem licença e sem informar o jogador.
let rtpTarget=parseFloat(localStorage.getItem('win888_rtp')??'0.97');
if(isNaN(rtpTarget)||rtpTarget<=0||rtpTarget>1)rtpTarget=0.97;
function openRTP(){const v=prompt(`RTP alvo atual: ${(rtpTarget*100).toFixed(1)}%\nPara estudo local, digite novo valor entre 0.05 e 1.0 (ex: 0.12 = 12%):`,String(rtpTarget));if(v===null)return;const n=parseFloat(v.replace(',','.'));if(isNaN(n)||n<0.05||n>1){toast('Valor inválido (use 0.05 a 1.0)','lose');return}rtpTarget=n;localStorage.setItem('win888_rtp',String(n));updateRTPBadge();toast(`RTP de estudo ajustado para ${(n*100).toFixed(1)}% — visível para todos`,'win');if(n<0.5)toast('⚠️ RTP abaixo de 50% é abusivo se usado com dinheiro real sem aviso explícito.','lose')}
function updateRTPBadge(){const el=document.querySelector('#rtpBadge');if(el)el.textContent=`RTP estudo ${(rtpTarget*100).toFixed(0)}%`;}

const GAMES=[
 {id:'tiger',name:'Fortune Tiger',cat:['popular','slots'],icon:'🐯',prov:'PG SOFT',bg:'linear-gradient(135deg,#f59e0b,#7c2d12)',rtp:'96.8%',desc:'Até 2.500x • Fortune',players:2314,jack:'R$ 48.200'},
 {id:'dragon',name:'Fortune Dragon',cat:['popular','slots'],icon:'🐲',prov:'PG SOFT',bg:'linear-gradient(135deg,#059669,#022c22)',rtp:'96.5%',desc:'Até 2.500x • Fortune',players:1187,jack:'R$ 32.900'},
 {id:'slots777',name:'Super 777',cat:['popular','slots'],icon:'🎰',prov:'PRAGMATIC',bg:'linear-gradient(135deg,#7c3aed,#9d174d)',rtp:'97.1%',desc:'Clássico 50x',players:1932,jack:'R$ 25.400'},
 {id:'rabbit',name:'Fortune Rabbit',cat:['popular','slots'],icon:'🐰',prov:'PG SOFT',bg:'linear-gradient(135deg,#ec4899,#500f28)',rtp:'96.6%',desc:'Até 5.000x',players:2091,jack:'R$ 51.700'},
 {id:'ox',name:'Fortune Ox',cat:['popular','slots'],icon:'🐂',prov:'PG SOFT',bg:'linear-gradient(135deg,#b45309,#1c0a00)',rtp:'96.6%',desc:'Até 2.000x',players:864,jack:'R$ 18.300'},
 {id:'gates',name:'Gates of Olympus',cat:['popular','slots'],icon:'⚡',prov:'PRAGMATIC',bg:'linear-gradient(135deg,#4f46e5,#020617)',rtp:'96.5%',desc:'Até 5.000x',players:1764,jack:'R$ 96.000'},
 {id:'fruits',name:'Fruit Party',cat:['slots'],icon:'🍒',prov:'PRAGMATIC',bg:'linear-gradient(135deg,#16a34a,#052e16)',rtp:'96.9%',desc:'Cluster 5.000x',players:642,jack:'R$ 12.800'},
 {id:'diamonds',name:'Diamonds VIP',cat:['slots'],icon:'💎',prov:'EVOPLAY',bg:'linear-gradient(135deg,#06b6d4,#0f1033)',rtp:'96.7%',desc:'Jackpot progressivo',players:519,jack:'R$ 74.500'},
 {id:'crash',name:'Crash Avião',cat:['popular','crash'],icon:'🚀',prov:'SPRIBE',bg:'linear-gradient(135deg,#0ea5e9,#172554)',rtp:'97.0%',desc:'Saque antes de crashar',players:3120,jack:'20x max'},
 {id:'mines',name:'Mines',cat:['popular','crash'],icon:'💣',prov:'SPRIBE',bg:'linear-gradient(135deg,#334155,#020617)',rtp:'97.2%',desc:'5x5 desvie das minas',players:1544,jack:'50x max'},
 {id:'roleta',name:'Roleta Europeia',cat:['popular','mesa'],icon:'🎡',prov:'EVOLUTION',bg:'linear-gradient(135deg,#16a34a,#02170c)',rtp:'97.3%',desc:'36x número exato',players:732,jack:'Mesa VIP'},
 {id:'blackjack',name:'Blackjack VIP',cat:['mesa'],icon:'🃏',prov:'EVOLUTION',bg:'linear-gradient(135deg,#1f2937,#030712)',rtp:'99.4%',desc:'Paga 3:2',players:428,jack:'Mesa VIP'},
 {id:'dice',name:'Dice Premium',cat:['crash','mesa'],icon:'🎲',prov:'SPRIBE',bg:'linear-gradient(135deg,#f97316,#431407)',rtp:'98.0%',desc:'Over/Under',players:311,jack:'9.9x max'},
 {id:'coin',name:'Cara ou Coroa',cat:['crash'],icon:'🪙',prov:'ORIGINAIS',bg:'linear-gradient(135deg,#eab308,#422006)',rtp:'98.0%',desc:'1.96x rápido',players:402,jack:'1.96x'},
 {id:'hilo',name:'Hi-Lo Cards',cat:['mesa'],icon:'♥️',prov:'ORIGINAIS',bg:'linear-gradient(135deg,#dc2626,#1c0505)',rtp:'97.5%',desc:'Sequência x1.4',players:188,jack:'10x+ seq.'},
 {id:'raspa',name:'Raspadinha Ouro',cat:['slots'],icon:'🎫',prov:'ORIGINAIS',bg:'linear-gradient(135deg,#0891b2,#083344)',rtp:'95.0%',desc:'3 iguais 20x',players:356,jack:'R$ 8.900'},
 {id:'sports',name:'Esportes',cat:['popular','esporte'],icon:'⚽',prov:'SPORTSBOOK',bg:'linear-gradient(135deg,#22c55e,#052e16)',rtp:'var.',desc:'Odds ao vivo demo',players:5210,jack:'Combinadas'},
];
const MATCHES=[
 {a:'Flamengo',b:'Palmeiras',o:[2.10,3.20,3.40]},
 {a:'Corinthians',b:'São Paulo',o:[2.80,3.00,2.60]},
 {a:'Real Madrid',b:'Barcelona',o:[2.50,3.40,2.70]},
 {a:'Man City',b:'Arsenal',o:[1.95,3.60,3.80]},
 {a:'Brasil',b:'Argentina',o:[2.70,3.10,2.55]},
 {a:'Tigers SP',b:'Dragons RJ',o:[1.80,3.80,4.20]},
];
function fmt(v){return v.toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}
function save(){localStorage.setItem('win888_balance',balance);localStorage.setItem('win888_history',JSON.stringify(history.slice(0,80)))}
function updateBal(){ $('#balance').textContent=fmt(balance); $('#walletBalance')&&($('#walletBalance').textContent=fmt(balance)); }
function toast(msg,cls=''){const t=document.createElement('div');t.className='toast '+cls;t.textContent=msg;$('#toasts').appendChild(t);setTimeout(()=>t.remove(),3200)}
function rnd(n){const a=new Uint32Array(n);crypto.getRandomValues(a);return [...a]}
function pick(arr){return arr[rnd(1)[0]%arr.length]}
function addHist(game,bet,payout){history.unshift({g:game,b:bet,p:payout,t:new Date().toLocaleString('pt-BR')});save()}
function canBet(v){if(v<=0){toast('Aposta inválida','lose');return false}if(v>balance){toast('Saldo insuficiente — clique em Depositar (demo)','lose');return false}return true}
function settle(game,bet,payout){balance-=bet;balance+=payout;addHist(game,bet,payout);updateBal();save();
 if(payout>bet)toast(`🏆 ${game}: +${fmt(payout-bet)}`,'win');else if(payout===bet)toast(`↩️ ${game}: devolvido`);else toast(`😞 ${game}: -${fmt(bet-payout)}`,'lose');}

// ---- catalog ----
function renderGrid(){
 const q=($('#search').value||'').toLowerCase();
 const g=$('#grid');g.innerHTML='';
 let list=GAMES.filter(x=>(currentCat==='all'||x.cat.includes(currentCat))&&x.name.toLowerCase().includes(q));
 $('#gridTitle').textContent=currentCat==='all'?'🎮 Todos os jogos':document.querySelector(`[data-cat="${currentCat}"]`)?.textContent+' ';
 $('#count').textContent=list.length+' jogos';
 list.forEach(x=>{const d=document.createElement('div');d.className='card';d.onclick=()=>openGame(x.id);
  d.innerHTML=`<div class="card-art" style="background:${x.bg}"><span class="shine"></span><img src="${x.id}.svg" alt="${x.name}" style="width:100%;height:100%;object-fit:cover;position:absolute;inset:0"><span class="rtp">RTP ${x.rtp}</span><span class="prov">${x.prov||'ORIGINAIS'}</span><span class="jack">🏆 ${x.jack||''}</span><div class="play"><span>▶ JOGAR</span></div></div><div class="card-info"><div><b>${x.name}</b><small>${x.desc}</small></div><span class="players">● ${(x.players||500).toLocaleString('pt-BR')}</span></div>`;g.appendChild(d)});
}
function setCat(c,el){currentCat=c;document.querySelectorAll('.cat').forEach(b=>b.classList.remove('active'));el.classList.add('active');renderGrid()}
function filterGames(){renderGrid()}
function renderMatchesPreview(){const w=$('#matchesPreview');w.innerHTML='';MATCHES.slice(0,3).forEach((m,i)=>{w.appendChild(matchCard(m,i))})}
function matchCard(m,i){const d=document.createElement('div');d.className='match';d.innerHTML=`<b>${m.a} x ${m.b}</b><small class="muted"> hoje • demo resolve na hora</small><div class="odds"><button class="odd" onclick="betSport(${i},0)">1<b>${m.o[0].toFixed(2)}</b></button><button class="odd" onclick="betSport(${i},1)">X<b>${m.o[1].toFixed(2)}</b></button><button class="odd" onclick="betSport(${i},2)">2<b>${m.o[2].toFixed(2)}</b></button></div>`;return d}
function fakeWinners(){const n=['Lucas*','Ana*','Pedro*','Julia*','Rafa*','Thi*','Bru*','Gui*'];let s='';for(let i=0;i<12;i++)s+=`🏆 ${pick(n)} ganhou ${fmt(50+rnd(1)[0]%5000)} no ${pick(GAMES).name}  •  `;$('#winners').innerHTML=s+s}

// ---- modal ----
function openGame(id){clearInterval(crashTimer);$('#gameOverlay').classList.add('open');const meta=GAMES.find(g=>g.id===id);$('#gameTitle').textContent=`${meta.icon} ${meta.name} — saldo ${fmt(balance)}`;({tiger:uiTiger,dragon:uiTiger,rabbit:uiTiger,ox:uiTiger,gates:uiTiger,fruits:uiTiger,diamonds:uiTiger,slots777:uiSlots,crash:uiCrash,mines:uiMines,roleta:uiRoleta,blackjack:uiBJ,dice:uiDice,coin:uiCoin,hilo:uiHilo,raspa:uiRaspa,sports:uiSports}[id])()}
function closeGame(){clearInterval(crashTimer);$('#gameOverlay').classList.remove('open');$('#gameTitle').textContent='Jogo';renderGrid()}
function betInput(def=10){return `<div class="betbar"><label>Aposta R$<input id="bet" type="number" value="${def}" min="1" max="100000"></label><label style="flex:2">Atalhos<div class="row" style="margin:4px 0 0"><button class="btn sm ghost" onclick="document.querySelector('#bet').value=5">5</button><button class="btn sm ghost" onclick="document.querySelector('#bet').value=10">10</button><button class="btn sm ghost" onclick="document.querySelector('#bet').value=50">50</button><button class="btn sm ghost" onclick="document.querySelector('#bet').value=100">100</button></div></label></div>`}
function getBet(){return Math.floor(Number(document.querySelector('#bet')?.value||10))}

// ---- TIGER / DRAGON ----
function uiTiger(){const B=$('#gameBody');const syms=['🐯','💰','🍊','🐉','🔔','⭐','🧧'];B.innerHTML=`${betInput(10)}<div class="slot-frame"><div class="slot3" id="tgrid">${'<div>❓</div>'.repeat(9)}</div></div><div class="row"><button class="btn gold" style="flex:1;font-size:17px" onclick="spinTiger()">🐯 GIRAR • GANHE ATÉ 2500x</button></div><p class="muted">Linha do meio 3 iguais = 5x • 3x 🐯 = 25x • Tela cheia = 100x • Modo Fortuna x10 aleatório. Demo sem dinheiro real.</p><div id="tmsg" style="font-weight:800"></div>`;
 window.spinTiger=()=>{const bet=getBet();if(!canBet(bet))return;const grid=Array.from({length:9},()=>pick(syms));const cells=[...document.querySelectorAll('#tgrid div')];cells.forEach((c)=>{c.textContent='🎰';c.classList.add('spinning');c.classList.remove('win');});setTimeout(()=>{cells.forEach((c,i)=>{c.textContent=grid[i];c.classList.remove('spinning')});let mult=0;const mid=[grid[3],grid[4],grid[5]];
  if(mid[0]===mid[1]&&mid[1]===mid[2])mult=mid[0]==='🐯'?25:5;
  if(new Set(grid).size===1)mult=100;
  if(rnd(1)[0]%10===0&&mult>0){mult*=10;$('#tmsg').innerHTML='<b style="color:#bef264">🔥 MODO FORTUNA x10!</b>'}
  const pay=bet*mult;settle('Tiger',bet,pay);if(mult){[3,4,5].forEach(i=>cells[i].classList.add('win'))}if(!mult)$('#tmsg').innerHTML='Tente de novo! 🍀';else $('#tmsg').innerHTML+=`<br>Prêmio: <b>${mult}x = ${fmt(pay)}</b>`;$('#gameTitle').textContent=`🐯 Jogo do Tiger — saldo ${fmt(balance)}`},600)};}

// ---- SLOTS 777 ----
function uiSlots(){const B=$('#gameBody');B.innerHTML=`${betInput(10)}<div class="slot3" id="sgrid"><div>7️⃣</div><div>7️⃣</div><div>7️⃣</div></div><div class="row"><button class="btn" style="flex:1" onclick="spinSlots()">GIRAR 777</button></div><p class="muted">7️⃣7️⃣7️⃣=50x • 💎💎💎=20x • par=2x • 🍒 bônus=1x</p><div id="smsg"></div>`;
 window.spinSlots=()=>{const bet=getBet();if(!canBet(bet))return;const s=['7️⃣','💎','🍒','🔔','⭐','🍋'];const r=[pick(s),pick(s),pick(s)];$('#sgrid').innerHTML=r.map(x=>`<div>🎰</div>`).join('');setTimeout(()=>{$('#sgrid').innerHTML=r.map(x=>`<div>${x}</div>`).join('');let m=0;if(r[0]==='7️⃣'&&r[1]==='7️⃣'&&r[2]==='7️⃣')m=50;else if(r.every(x=>x==='💎'))m=20;else if(r[0]===r[1]&&r[1]===r[2])m=8;else if(r[0]===r[1]||r[1]===r[2])m=2;else if(r.includes('🍒'))m=1;settle('Slots777',bet,bet*m);$('#smsg').innerHTML=m?`Ganhou <b>${m}x</b>!`:'Sem sorte dessa vez.';$('#gameTitle').textContent=`🎰 Slots — saldo ${fmt(balance)}`},500)};}

// ---- CRASH ----
function uiCrash(){const B=$('#gameBody');B.innerHTML=`${betInput(20)}<div class="crash-graph"><div class="crash-mult" id="cmult">1.00x</div><div class="crash-rocket" id="crock">🚀</div></div><div class="row"><button class="btn" id="cstart" style="flex:1" onclick="startCrash()">Começar voo</button><button class="btn ghost" id="ccash" disabled onclick="cashCrash()">Sacar</button></div><p class="muted">Crash aleatório 1.00x–20x. Saque antes!</p>`;
 window.startCrash=()=>{const bet=getBet();if(!canBet(bet))return;clearInterval(crashTimer);const crashAt=1+ (rnd(1)[0]%2000)/100*2;let m=1;$('#cstart').disabled=true;$('#ccash').disabled=false;crashState={bet,dead:false};
  crashTimer=setInterval(()=>{m+=0.05+m*0.03;$('#cmult').textContent=m.toFixed(2)+'x';$('#crock').style.bottom=(Math.min(m*8,110))+'px';
   if(m>=crashAt){clearInterval(crashTimer);crashState.dead=true;$('#cstart').disabled=false;$('#ccash').disabled=true;$('#cmult').textContent='💥 '+m.toFixed(2)+'x CRASH';settle('Crash',bet,0)}},100);
  crashState.mult=()=>m;};
 window.cashCrash=()=>{if(!crashState||crashState.dead)return;clearInterval(crashTimer);const m=parseFloat($('#cmult').textContent);const pay=Math.floor(crashState.bet*m);settle('Crash',crashState.bet,pay);crashState.dead=true;$('#cstart').disabled=false;$('#ccash').disabled=true;};}

// ---- MINES ----
let minesState=null;
function uiMines(){const B=$('#gameBody');B.innerHTML=`${betInput(20)}<label>Nº de minas<select id="mn"><option>3</option><option>5</option><option>8</option></select></label><div class="mines5" id="mgrid"></div><div class="row"><button class="btn" style="flex:1" onclick="startMines()">Iniciar</button><button class="btn ghost" onclick="cashMines()">Sacar (<span id="mval">0</span>)</button></div><p class="muted">Ache 💎 e multiplique. 💣 encerra.</p>`;
 window.startMines=()=>{const bet=getBet();if(!canBet(bet))return;const n=Number($('#mn').value);const pos=new Set();while(pos.size<n)pos.add(rnd(1)[0]%25);minesState={bet,mines:pos,open:0,over:false};const g=$('#mgrid');g.innerHTML='';for(let i=0;i<25;i++){const b=document.createElement('button');b.className='mine';b.textContent='❔';b.onclick=()=>openMine(i,b);g.appendChild(b)}$('#mval').textContent=fmt(0)};
 window.openMine=(i,btn)=>{if(!minesState||minesState.over)return;if(minesState.mines.has(i)){btn.textContent='💣';btn.style.background='#dc2626';minesState.over=true;settle('Mines',minesState.bet,0);[...document.querySelectorAll('.mine')].forEach((b,j)=>{if(minesState.mines.has(j))b.textContent='💣'})}else{btn.textContent='💎';btn.style.background='#14532d';btn.disabled=true;minesState.open++;const mult=Math.pow(1+minesState.mines.size/8,minesState.open);$('#mval').textContent=fmt(Math.floor(minesState.bet*mult))}};
 window.cashMines=()=>{if(!minesState||minesState.over||!minesState.open)return;const mult=Math.pow(1+minesState.mines.size/8,minesState.open);minesState.over=true;settle('Mines',minesState.bet,Math.floor(minesState.bet*mult))};}

// ---- ROLETA ----
function uiRoleta(){const B=$('#gameBody');B.innerHTML=`${betInput(10)}<div class="roulette-wheel" id="rwheel">🎡</div><div id="rnum" style="text-align:center;font-size:28px">—</div><label>Aposta em<select id="rtype"><option value="red">🔴 Vermelho (2x)</option><option value="black">⚫ Preto (2x)</option><option value="green">🟢 Zero (36x)</option><option value="num">🔢 Número exato (36x)</option></select></label><label id="rnumWrap" style="display:none">Número 0-36<input id="rpick" type="number" value="7" min="0" max="36"></label><button class="btn" style="width:100%" onclick="spinRoleta()">GIRAR ROLETA</button>`;
 document.querySelector('#rtype').onchange=e=>{$('#rnumWrap').style.display=e.target.value==='num'?'block':'none'};
 const reds=new Set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]);
 window.spinRoleta=()=>{const bet=getBet();if(!canBet(bet))return;const w=$('#rwheel');w.classList.add('spinning');setTimeout(()=>{w.classList.remove('spinning');const n=rnd(1)[0]%37;$('#rnum').textContent=n;const type=$('#rtype').value;let win=false;if(type==='red')win=reds.has(n);if(type==='black')win=n!==0&&!reds.has(n);if(type==='green')win=n===0;if(type==='num')win=n===Number($('#rpick').value);const mult=type==='num'||type==='green'?36:2;settle('Roleta',bet,win?bet*mult:0)},1200)};}

// ---- BLACKJACK ----
function uiBJ(){const B=$('#gameBody');B.innerHTML=`${betInput(25)}<div><small class="muted">Dealer</small><div class="cards" id="dcards"></div><small class="muted">Você (<span id="ppts"></span>)</small><div class="cards" id="pcards"></div></div><div class="row"><button class="btn" onclick="bjHit()">+ Carta</button><button class="btn ghost" onclick="bjStand()">Parar</button><button class="btn ghost" onclick="bjNew()">Nova mão</button></div><div id="bjmsg"></div>`;
 let deck=[],ph=[],dh=[],over=false,bet=0;
 const val=h=>{let s=h.reduce((a,c)=>a+(c>10?10:c===1?11:c),0),a=h.filter(c=>c===1).length;while(s>21&&a--){s-=10}return s};
 const card=()=>1+rnd(1)[0]%13; const show=()=>{const f=c=>c===1?'A':c===11?'J':c===12?'Q':c===13?'K':c;$('#pcards').innerHTML=ph.map(c=>`<div class="pcard ${c===13||c===12?'red':''}">${f(c)}</div>`).join('');$('#dcards').innerHTML=dh.map((c,i)=>`<div class="pcard">${i===1&&!over?'🂠':f(c)}</div>`).join('');$('#ppts').textContent=val(ph)};
 window.bjNew=()=>{bet=getBet();if(!canBet(bet))return;deck=[];ph=[card(),card()];dh=[card(),card()];over=false;show();$('#bjmsg').textContent='Sua vez!';if(val(ph)===21)bjStand()};
 window.bjHit=()=>{if(over||!ph.length)return;ph.push(card());show();if(val(ph)>21){over=true;show();$('#bjmsg').textContent='💥 Estourou! 21+';settle('Blackjack',bet,0)}};
 window.bjStand=()=>{if(over||!ph.length)return;over=true;while(val(dh)<17)dh.push(card());show();const p=val(ph),d=val(dh);let pay=0;if(d>21||p>d)pay=bet*2;else if(p===d)pay=bet;$('#bjmsg').textContent=`Você ${p} x Dealer ${d} — ${pay>bet?'🏆 Ganhou!':pay===bet?'Empate':'Dealer ganhou'}`;settle('Blackjack',bet,pay)};
 bjNew();}

// ---- DICE ----
function uiDice(){const B=$('#gameBody');B.innerHTML=`${betInput(10)}<label>Chance de ganhar: <b id="dchance">50%</b><input id="drange" type="range" min="5" max="95" value="50" oninput="document.querySelector('#dchance').textContent=this.value+'%'"></label><div class="row"><button class="btn" style="flex:1" onclick="rollDice(true)">🎲 Rolar ACIMA</button><button class="btn ghost" style="flex:1" onclick="rollDice(false)">Rolar ABAIXO</button></div><div id="dmsg" style="font-size:40px;text-align:center"></div><p class="muted">Pagamento = 99/chance. Ex: 50% paga 1.98x.</p>`;
 window.rollDice=up=>{const bet=getBet();if(!canBet(bet))return;const ch=Number($('#drange').value);const roll=(rnd(1)[0]%10000)/100;$('#dmsg').textContent='🎲 '+roll.toFixed(2);const win=up?roll>100-ch:roll<ch;const pay=win?Math.floor(bet*99/ch):0;settle('Dice',bet,pay)};}

// ---- COIN ----
function uiCoin(){const B=$('#gameBody');B.innerHTML=`${betInput(10)}<div style="font-size:80px;text-align:center" id="cface">🪙</div><div class="row"><button class="btn" style="flex:1" onclick="flipCoin('cara')">Cara</button><button class="btn ghost" style="flex:1" onclick="flipCoin('coroa')">Coroa</button></div>`;
 window.flipCoin=c=>{const bet=getBet();if(!canBet(bet))return;$('#cface').textContent='🔄';setTimeout(()=>{const r=Math.random()<.5?'cara':'coroa';$('#cface').textContent=r==='cara'?'🙂':'👑';settle('CaraCoroa',bet,r===c?bet*1.96:0)},500)};}

// ---- HILO ----
let hiloCard=null;
function uiHilo(){const B=$('#gameBody');B.innerHTML=`${betInput(10)}<div class="cards"><div class="pcard" id="hcard" style="font-size:34px">🂠</div></div><div class="row"><button class="btn" style="flex:1" onclick="hiloGuess(1)">▲ Maior</button><button class="btn ghost" style="flex:1" onclick="hiloGuess(-1)">▼ Menor</button></div><div class="row"><button class="btn ghost sm" onclick="hiloNew()">Nova carta</button><button class="btn sm" onclick="hiloCash()">Sacar (<span id="hval">0</span>)</button></div><p class="muted">Acertos encadeiam x1.3. Errar zera. Saque quando quiser.</p>`;hiloNew(true);
 window.hiloNew=init=>{hiloCard=1+rnd(1)[0]%13;window.hiloStreak=0;window.hiloBet=init?0:(window.hiloBet||0);$('#hcard').textContent='KQJA23456789TJQK'[0]||hiloCard;$('#hcard').textContent=hiloCard;$('#hval').textContent=fmt(0)};
 window.hiloGuess=dir=>{const bet=window.hiloBet||getBet();if(!window.hiloBet){if(!canBet(bet))return;window.hiloBet=bet;balance-=bet;updateBal()}const next=1+rnd(1)[0]%13;const win=(dir===1&&next>hiloCard)||(dir===-1&&next<hiloCard);if(next===hiloCard){$('#hcard').textContent=next+' empate — mantém';return}
  if(win){window.hiloStreak++;hiloCard=next;$('#hcard').textContent=next;const v=Math.floor(window.hiloBet*Math.pow(1.4,window.hiloStreak));$('#hval').textContent=fmt(v)}else{addHist('HiLo',window.hiloBet,0);save();toast('😞 Hi-Lo: errou','lose');window.hiloBet=0;window.hiloStreak=0;hiloCard=next;$('#hcard').textContent=next;$('#hval').textContent=fmt(0);updateBal()}};
 window.hiloCash=()=>{if(!window.hiloBet||!window.hiloStreak)return;const v=Math.floor(window.hiloBet*Math.pow(1.4,window.hiloStreak));balance+=v;addHist('HiLo',window.hiloBet,v);save();updateBal();toast(`🏆 Hi-Lo: +${fmt(v-window.hiloBet)}`,'win');window.hiloBet=0;window.hiloStreak=0;$('#hval').textContent=fmt(0)};}

// ---- RASPADINHA ----
function uiRaspa(){const B=$('#gameBody');B.innerHTML=`${betInput(10)}<div class="slot3" id="rgrid"></div><button class="btn" style="width:100%" onclick="raspar()">🎫 Raspar (3 iguais ganham)</button><div id="rmsg"></div>`;
 window.raspar=()=>{const bet=getBet();if(!canBet(bet))return;const s=['💎','⭐','🍒','🔔','💰','7️⃣'];let grid=Array.from({length:9},()=>pick(s));if(Math.random()<.3){const w=pick(s);grid=[w,w,w,...grid.slice(3)]}$('#rgrid').innerHTML=grid.map(x=>`<div>${x}</div>`).join('');const counts={};grid.forEach(x=>counts[x]=(counts[x]||0)+1);const best=Math.max(...Object.values(counts));const win=best>=3;const mult=best>=6?20:best>=5?8:best>=4?4:best>=3?2:0;settle('Raspadinha',bet,bet*mult);$('#rmsg').innerHTML=win?`🎉 ${best}x iguais = ${mult}x!`:'Nada dessa vez.'};}

// ---- SPORTS ----
function uiSports(){const B=$('#gameBody');B.innerHTML=`${betInput(20)}<div id="slist"></div>`;const l=B.querySelector('#slist');MATCHES.forEach((m,i)=>l.appendChild(matchCard(m,i)));
 window.betSport=(i,o)=>{const bet=getBet();if(!canBet(bet))return;const m=MATCHES[i];const odd=m.o[o];const r=Math.random();const p=1/odd*0.95;const win=r<p;const pay=win?Math.floor(bet*odd):0;settle(`Esporte ${m.a}x${m.b}`,bet,pay);toast(win?`⚽ GOL! ${m.a} x ${m.b} bateu @${odd}`:`⚽ Não bateu @${odd}`,win?'win':'lose')};}

// ---- wallet/history ----
function openWallet(mode){walletMode=mode;$('#walletTitle').textContent=mode==='deposit'?'💰 Depositar (demo)':'🏧 Sacar (demo)';$('#walletOverlay').classList.add('open');updateBal()}
function closeWallet(){$('#walletOverlay').classList.remove('open')}
function confirmWallet(){const v=Math.floor(Number($('#walletAmount').value||0));if(v<=0)return toast('Valor inválido','lose');if(walletMode==='deposit'){balance+=v;toast(`✅ +${fmt(v)} demo adicionado`,'win')}else{if(v>balance)return toast('Saldo insuficiente','lose');balance-=v;toast(`✅ Saque demo de ${fmt(v)}`)}save();updateBal();closeWallet();renderGrid()}
function resetBalance(){balance=1000;save();updateBal();toast('Saldo resetado para R$ 1.000 demo')}
function openHistory(){$('#histOverlay').classList.add('open');const l=$('#histList');l.innerHTML=history.length?history.map(h=>`<div style="border-bottom:1px solid #ffffff1a;padding:6px 0;font-size:13px"><b>${h.g}</b> — aposta ${fmt(h.b)} → retorno ${fmt(h.p)}<br><small class="muted">${h.t}</small></div>`).join(''):'<p class="muted">Sem apostas ainda.</p>'}
function closeHistory(){$('#histOverlay').classList.remove('open')}
function clearHistory(){history=[];save();openHistory()}

// init
updateBal();renderGrid();renderMatchesPreview();fakeWinners();updateRTPBadge();
try{const j=new URLSearchParams(location.search).get('jogo');if(j&&GAMES.some(g=>g.id===j))openGame(j);}catch{}
setInterval(()=>{const e=$('#online');if(e)e.textContent=(11000+rnd(1)[0]%5000).toLocaleString('pt-BR')},4000);
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeGame();closeWallet();closeHistory()}});
