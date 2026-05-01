// ── COLONNES ─────────────────────────────────────────────
const COLS = [
  {k:'frameType', lb:'TYPE'},
  {k:'race',      lb:'RACE'},
  {k:'attribute', lb:'ATTRIBUT'},
  {k:'level',     lb:'NIVEAU'},
  {k:'atk',       lb:'ATK'},
  {k:'def',       lb:'DEF'},
  {k:'archetype', lb:'ARCHÉTYPE'},
  {k:'ban',       lb:'BANLIST'},
  {k:'format',    lb:'FORMAT'},
];
const MAX = 8;
const $ = id => document.getElementById(id);

let CARDS = [];
let loaded = false;

// ── TRADUCTIONS ───────────────────────────────────────────

function normFrame(f) {
  const map = {
    normal:'Normal', effect:'Effet', ritual:'Rituel',
    fusion:'Fusion', synchro:'Synchro', xyz:'XYZ',
    link:'Link', spell:'Magie', trap:'Piège',
    token:'Jeton', skill:'Skill',
    normal_pendulum:'Pendule', effect_pendulum:'Pendule',
    ritual_pendulum:'Pendule', fusion_pendulum:'Pendule',
    synchro_pendulum:'Pendule', xyz_pendulum:'Pendule',
  };
  return map[(f || '').toLowerCase()] || f || '—';
}

function normRace(r) {
  const map = {
    'Spellcaster':'Magicien','Warrior':'Guerrier','Dragon':'Dragon',
    'Beast':'Bête','Beast-Warrior':'Bête-Guerrier','Fiend':'Démon',
    'Fairy':'Elfe','Insect':'Insecte','Dinosaur':'Dinosaure',
    'Reptile':'Reptile','Fish':'Poisson','Sea Serpent':'Serpent marin',
    'Aqua':'Aqua','Pyro':'Pyro','Thunder':'Tonnerre','Machine':'Machine',
    'Rock':'Rocher','Plant':'Plante','Zombie':'Zombi','Psychic':'Psychique',
    'Divine-Beast':'Divinité','Cyberse':'Cyberse','Wyrm':'Wyrm',
    'Creator-God':'Dieu créateur',
    'Normal':'Normal','Continuous':'Continu','Counter':'Contre',
    'Quick-Play':'Jeu rapide','Equip':'Équipement','Field':'Terrain',
    'Ritual':'Rituel',
  };
  return map[r] || r || '—';
}

function normAttr(a) {
  const map = {
    'DARK':'TÉNÈBRES','LIGHT':'LUMIÈRE','WATER':'EAU',
    'FIRE':'FEU','EARTH':'TERRE','WIND':'VENT','DIVINE':'DIVIN',
  };
  return map[a] || a || '—';
}

function normBan(info) {
  if (!info) return 'Autorisé';
  const b = info.ban_tcg;
  if (!b) return 'Autorisé';
  const map = {
    'Banned':'Interdit','Limited':'Limité','Semi-Limited':'Semi-Limité',
  };
  return map[b] || b;
}

function normFormat(misc) {
  if (!misc) return 'TCG';
  const f = misc.formats || [];
  if (f.includes('tcg')) return 'TCG';
  if (f.includes('ocg')) return 'OCG';
  return (f[0] || 'TCG').toUpperCase();
}

function normalize(raw) {
  return {
    id:        raw.id,
    name:      raw.name,
    frameType: normFrame(raw.frameType),
    race:      normRace(raw.race),
    attribute: normAttr(raw.attribute),
    level:     raw.level ?? raw.linkval ?? 0,
    atk:       raw.atk ?? -1,
    def:       raw.def ?? -1,
    archetype: raw.archetype || '—',
    ban:       normBan(raw.banlist_info),
    format:    normFormat(raw.misc_info?.[0]),
    img:       raw.card_images?.[0]?.image_url_small || '',
  };
}

// ── CHARGEMENT TOUTES LES CARTES ─────────────────────────
// L'API YGOPRODeck retourne toutes les cartes en un seul appel,
// on charge donc toute la base (12 000+ cartes) avec misc & banlist

async function loadCards() {
  const bar   = $('loadBar');
  const prog  = document.querySelector('.load-fill');

  bar.classList.remove('hidden');
  bar.textContent = '⏳ Chargement de toutes les cartes…';

  // Créer la barre de progression si elle n'existe pas
  if (!document.querySelector('.load-progress')) {
    const pb = document.createElement('div');
    pb.className = 'load-progress on';
    pb.innerHTML = '<div class="load-fill"></div>';
    bar.insertAdjacentElement('afterend', pb);
  }
  const fill = document.querySelector('.load-fill');

  try {
    // L'API retourne TOUTES les cartes en un seul appel (pas de pagination)
    // misc=yes → formats, banlist_info=yes → ban data
    // language=fr → noms français (quand disponible)
    const url = 'https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes&language=fr';

    // Étape 1 : fetch
    bar.textContent = '⏳ Téléchargement de la base complète…';
    fill && (fill.style.width = '20%');

    const resp = await fetch(url);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);

    fill && (fill.style.width = '60%');
    bar.textContent = '⏳ Traitement des cartes…';

    const json = await resp.json();
    const raw  = json.data || [];

    fill && (fill.style.width = '80%');

    // Normalisation
    const seen = new Set();
    for (const c of raw) {
      if (!seen.has(c.id)) {
        seen.add(c.id);
        CARDS.push(normalize(c));
      }
    }

    if (CARDS.length === 0) throw new Error('Aucune carte reçue');

    fill && (fill.style.width = '100%');
    bar.textContent = '✅ ' + CARDS.length.toLocaleString('fr') + ' cartes chargées !';

    setTimeout(() => {
      bar.classList.add('hidden');
      const pb = document.querySelector('.load-progress');
      if (pb) pb.style.display = 'none';
    }, 1200);

    loaded = true;
    $('gi').disabled  = false;
    $('gbtn').disabled = false;
    $('gi').placeholder = 'Entrez le nom d\'une carte…';
    initGame();

  } catch(e) {
    bar.textContent = '❌ Erreur : ' + e.message + '. Rechargez la page.';
    const pb = document.querySelector('.load-progress');
    if (pb) pb.style.display = 'none';
    console.error(e);
  }
}

// ── SEED / CARTE DU JOUR ──────────────────────────────────

function seededShuffle(arr, seed) {
  const a = arr.slice(); let s = seed >>> 0;
  for (let i = a.length - 1; i > 0; i--) {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    const j = s % (i + 1); [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function dayNum() {
  const s = new Date('2025-01-01'); const t = new Date(); t.setHours(0,0,0,0);
  return Math.floor((t - s) / 86400000);
}

function todayCard() {
  const d = dayNum();
  return seededShuffle(CARDS, d ^ 0xA7E)[d % CARDS.length];
}

function todayKey() {
  const d = new Date();
  return d.getFullYear() + '-' + (d.getMonth()+1) + '-' + d.getDate();
}

// ── COMPARAISON ───────────────────────────────────────────

function cmp(m, t) {
  const dAtk = Math.abs((m.atk < 0 ? 0 : m.atk) - (t.atk < 0 ? 0 : t.atk));
  const dDef = Math.abs((m.def < 0 ? 0 : m.def) - (t.def < 0 ? 0 : t.def));
  const dLvl = Math.abs(m.level - t.level);
  return [
    { v: m.frameType, s: m.frameType === t.frameType ? 'correct' : 'wrong',    a: '' },
    { v: m.race,      s: m.race      === t.race      ? 'correct' : 'wrong',    a: '' },
    { v: m.attribute, s: m.attribute === t.attribute ? 'correct' : 'wrong',    a: '' },
    { v: m.level === 0 ? '—' : m.level,
                      s: m.level === t.level ? 'correct' : dLvl <= 1 ? 'close' : 'wrong',
                      a: m.level < t.level ? '▲' : m.level > t.level ? '▼' : '' },
    { v: m.atk < 0 ? '—' : m.atk,
                      s: m.atk === t.atk ? 'correct' : dAtk <= 500 ? 'close' : 'wrong',
                      a: m.atk < t.atk ? '▲' : m.atk > t.atk ? '▼' : '' },
    { v: m.def < 0 ? '—' : m.def,
                      s: m.def === t.def ? 'correct' : dDef <= 500 ? 'close' : 'wrong',
                      a: m.def < t.def ? '▲' : m.def > t.def ? '▼' : '' },
    { v: m.archetype, s: m.archetype === t.archetype ? 'correct' : 'wrong',    a: '' },
    { v: m.ban,       s: m.ban === t.ban ? 'correct' : 'wrong',                a: '' },
    { v: m.format,    s: m.format === t.format ? 'correct' : 'wrong',          a: '' },
  ];
}

// ── RENDU ─────────────────────────────────────────────────

function mkRow(m, f, tgt) {
  const row = document.createElement('div'); row.className = 'row';
  const nc = document.createElement('div');
  nc.className = 'cell ' + (m.name === tgt.name ? 'correct' : 'wrong');
  nc.textContent = m.name; row.appendChild(nc);
  f.forEach(x => {
    const c = document.createElement('div'); c.className = 'cell ' + x.s;
    c.innerHTML = x.v + (x.a ? '<span style="font-size:7px;margin-left:2px">' + x.a + '</span>' : '');
    row.appendChild(c);
  });
  $('gr').prepend(row);
}

function mkCard(m, f, tgt) {
  const win = m.name === tgt.name;
  const card = document.createElement('div'); card.className = 'card ' + (win ? 'ok' : 'ko');
  const top = document.createElement('div'); top.className = 'ctop';
  const nm = document.createElement('div');
  nm.className = 'cname ' + (win ? 'correct' : 'wrong'); nm.textContent = m.name;
  const badge = document.createElement('div'); badge.className = 'cbadge';
  badge.innerHTML = m.frameType + '<br>' + (m.attribute !== '—' ? m.attribute : m.race);
  top.appendChild(nm); top.appendChild(badge); card.appendChild(top);
  const g = document.createElement('div'); g.className = 'cgrid';
  COLS.forEach((col, i) => {
    const x = f[i];
    const cc = document.createElement('div'); cc.className = 'cc ' + x.s;
    const lb = document.createElement('div'); lb.className = 'cl'; lb.textContent = col.lb;
    const vl = document.createElement('div'); vl.className = 'cv';
    vl.innerHTML = x.v + (x.a ? '<span style="font-size:.5rem;opacity:.8"> ' + x.a + '</span>' : '');
    cc.appendChild(lb); cc.appendChild(vl); g.appendChild(cc);
  });
  card.appendChild(g); $('gc').prepend(card);
}

function clr() { $('gr').innerHTML = ''; $('gc').innerHTML = ''; }

// ── ÉTAT ──────────────────────────────────────────────────

let mode = 'daily';
let tgt, dG = [], dOver = false, dSel = -1;
let sStr = 0, sBst = 0, sKil = 0;
let sQ = [], sQi = 0, sCur = null, sG = [], sSel = -1, sOver = false, sRec = 0;

function initGame() {
  tgt = todayCard();
  loadD();
  if (!dOver) foc();
}

// ── SWITCH MODE ───────────────────────────────────────────

function switchMode(m) {
  mode = m;
  $('btnD').classList.toggle('active', m === 'daily');
  $('btnS').classList.toggle('active', m === 'survival');
  $('dbar').style.display = m === 'daily' ? 'flex' : 'none';
  $('sbar').classList.toggle('on', m === 'survival');
  $('htitle').textContent = m === 'daily' ? 'Règles — Quotidien' : 'Règles — Survie';
  $('hd').style.display = m === 'daily' ? '' : 'none';
  $('hs').style.display = m === 'survival' ? '' : 'none';
  $('flash').classList.remove('on');
  document.body.classList.toggle('survival-mode', m === 'survival');
  if (m === 'daily') {
    $('send').classList.remove('on'); clr();
    dG.forEach(x => { mkRow(x.m, x.f, tgt); mkCard(x.m, x.f, tgt); });
    updDots();
    if (dOver) showDRes(dG.some(x => x.m.name === tgt.name));
    else $('rb').classList.remove('on');
    $('gi').disabled = dOver; $('gbtn').disabled = dOver;
    if (!dOver) foc();
  } else {
    $('rb').classList.remove('on');
    if (sOver) { clr(); showSEnd(); }
    else {
      clr();
      if (!sCur) sInit();
      else sG.forEach(x => { mkRow(x.m, x.f, sCur); mkCard(x.m, x.f, sCur); });
      updSUI(); $('gi').disabled = false; $('gbtn').disabled = false; foc();
    }
  }
}

function foc() { setTimeout(() => $('gi').focus(), 60); }

// ── SAUVEGARDE QUOTIDIEN ──────────────────────────────────

function saveD(won) {
  try {
    localStorage.setItem('ygog_v2_fr', JSON.stringify({
      date: todayKey(),
      guesses: dG.map(x => ({ n: x.m.name })),
      over: dOver, won
    }));
  } catch(e) {}
}

function loadD() {
  try {
    const s = JSON.parse(localStorage.getItem('ygog_v2_fr'));
    if (!s || s.date !== todayKey()) return;
    for (const sv of (s.guesses || [])) {
      const fr = CARDS.find(x => x.name === sv.n); if (!fr) continue;
      dG.push({ m: fr, f: cmp(fr, tgt) });
    }
    dOver = s.over || false;
    if (mode === 'daily') {
      dG.forEach(x => { mkRow(x.m, x.f, tgt); mkCard(x.m, x.f, tgt); });
      updDots(); if (dOver) showDRes(s.won);
    }
  } catch(e) {}
}

function updDots() {
  const r = $('dots'); r.innerHTML = '';
  for (let i = 0; i < MAX; i++) {
    const d = document.createElement('div'); d.className = 'dot';
    if (i < dG.length) {
      const w = dG[i].m.name === tgt.name;
      d.classList.add(w ? 'win' : (dOver && i === dG.length-1 ? 'lose' : 'used'));
    }
    r.appendChild(d);
  }
  $('cnt').textContent = dG.length + '/' + MAX;
}

function showDRes(won) {
  const b = $('rb'); b.classList.add('on', won ? 'win' : 'lose');
  $('rttl').textContent = won ? '🃏 BIEN JOUÉ !' : '☠ ÉCHEC';
  $('rimg').src = tgt.img;
  $('rchar').textContent = tgt.name;
  $('rdesc').textContent = won
    ? tgt.name + ' trouvée en ' + dG.length + ' essai' + (dG.length > 1 ? 's' : '') + '.'
    : tgt.name + ' · ' + tgt.frameType + ' · ' + tgt.attribute + ' · Niv.' + tgt.level + ' · ATK ' + (tgt.atk < 0 ? '—' : tgt.atk);
  $('gi').disabled = true; $('gbtn').disabled = true;
  tick(); setInterval(tick, 1000);
}

function tick() {
  const now = new Date(), tom = new Date(now);
  tom.setDate(tom.getDate() + 1); tom.setHours(0,0,0,0);
  const d = tom - now;
  $('nt').textContent =
    String(Math.floor(d/3600000)).padStart(2,'0') + ':' +
    String(Math.floor((d%3600000)/60000)).padStart(2,'0') + ':' +
    String(Math.floor((d%60000)/1000)).padStart(2,'0');
}

function share() {
  let t = 'YGO Guessr ' + todayKey() + '\n' + dG.length + '/' + MAX + '\n\n';
  dG.forEach(x => {
    t += (x.m.name === tgt.name ? '🃏 ' : '') + x.m.name + '\n';
    t += x.f.map(f => f.s === 'correct' ? '🟩' : f.s === 'close' ? '🟨' : '🟥').join('') + '\n';
  });
  try { navigator.clipboard.writeText(t); } catch(e) {}
  const b = document.querySelector('.xbtn'); b.textContent = '✓ Copié !';
  setTimeout(() => b.textContent = '📋 Copier le résultat', 2000);
}

// ── MODE SURVIE ───────────────────────────────────────────

function loadRec() {
  try { const s = JSON.parse(localStorage.getItem('ygog_surv')); if (s) sRec = s.best || 0; } catch(e) {}
}
function saveRec() {
  try { localStorage.setItem('ygog_surv', JSON.stringify({ best: sRec })); } catch(e) {}
}
function rndQ() {
  const a = CARDS.slice();
  for (let i = a.length-1; i > 0; i--) {
    const j = Math.floor(Math.random()*(i+1)); [a[i],a[j]] = [a[j],a[i]];
  }
  return a;
}
function sInit() {
  sStr=0; sBst=0; sKil=0; sQ=rndQ(); sQi=0; sOver=false;
  $('send').classList.remove('on'); sNext();
}
function sNext() {
  if(sQi>=sQ.length){ sQ=rndQ(); sQi=0; }
  sCur=sQ[sQi++]; sG=[]; clr();
  $('flash').classList.remove('on');
  $('gi').disabled=false; $('gbtn').disabled=false;
  foc(); updSUI();
}
function updSUI() {
  $('sstreak').textContent = sStr; $('sbest').textContent = sRec;
  const el = $('sdots'); el.innerHTML = '';
  for (let i = 0; i < MAX; i++) {
    const d = document.createElement('div'); d.className = 'sdot';
    if (i < sG.length) d.classList.add(sG[i] && sG[i].m.name === sCur.name ? 'win' : 'used');
    el.appendChild(d);
  }
}
function showFlash(type, msg) {
  const f = $('flash');
  f.className = 'flash on ' + (type === 'ok' ? 'ok' : 'ko');
  f.textContent = msg;
  clearTimeout(f._t); f._t = setTimeout(() => f.classList.remove('on'), 2500);
}
function sGameOver(name) {
  sOver=true;
  if(sStr>sRec){ sRec=sStr; saveRec(); }
  showFlash('ko','☠ ' + name + ' — Game Over !');
  $('gi').disabled=true; $('gbtn').disabled=true;
  setTimeout(() => showSEnd(), 1500);
}
function sCorrect() {
  sKil++; sStr++;
  if(sStr>sBst) sBst=sStr;
  if(sStr>sRec){ sRec=sStr; saveRec(); }
  showFlash('ok','✓ '+sCur.name+' trouvée'+(sStr>=3?' 🔥 ×'+sStr:''));
  $('gi').disabled=true; $('gbtn').disabled=true; updSUI();
  setTimeout(() => sNext(), 1900);
}
function showSEnd() {
  clr(); $('send').classList.add('on');
  $('sedesc').innerHTML = 'Série de <em>'+sStr+'</em> — '+sKil+' carte'+(sKil>1?'s':'')+'.';
  $('sek').textContent=sKil; $('seb').textContent=sBst; $('ser').textContent=sRec;
  $('gi').disabled=true; $('gbtn').disabled=true; updSUI();
}
function sRestart() { sInit(); }
function sShare() {
  const t='YGO Guessr — Survie\nSérie : '+sStr+'\nTrouvées : '+sKil+'\nRecord : '+sRec;
  try{ navigator.clipboard.writeText(t); }catch(e){}
  const b=document.querySelector('.xbtn2'); b.textContent='✓ Copié !';
  setTimeout(()=>b.textContent='📋 Copier le score',2000);
}

// ── SOUMISSION ────────────────────────────────────────────

function sub() { mode==='daily' ? subD() : subS(); }

function subD() {
  if(dOver||!loaded) return;
  const inp=$('gi'); const v=inp.value.trim(); if(!v) return;
  const m=CARDS.find(x=>x.name.toLowerCase()===v.toLowerCase());
  if(!m){ shake(inp,'Carte introuvable…'); return; }
  if(dG.find(x=>x.m.name===m.name)){ shake(inp,'Déjà essayée !'); return; }
  const f=cmp(m,tgt); dG.push({m,f});
  mkRow(m,f,tgt); mkCard(m,f,tgt); updDots();
  inp.value=''; $('acl').innerHTML='';
  const won=m.name===tgt.name;
  if(won||dG.length>=MAX){ dOver=true; saveD(won); setTimeout(()=>showDRes(won),400); }
  else saveD(false);
}

function subS() {
  if(sOver||!sCur||!loaded) return;
  const inp=$('gi'); const v=inp.value.trim(); if(!v) return;
  const m=CARDS.find(x=>x.name.toLowerCase()===v.toLowerCase());
  if(!m){ shake(inp,'Carte introuvable…'); return; }
  if(sG.find(x=>x.m.name===m.name)){ shake(inp,'Déjà essayée !'); return; }
  const f=cmp(m,sCur); sG.push({m,f});
  mkRow(m,f,sCur); mkCard(m,f,sCur);
  inp.value=''; $('acl').innerHTML=''; updSUI();
  if(m.name===sCur.name) sCorrect();
  else if(sG.length>=MAX) sGameOver(sCur.name);
}

function shake(inp, msg) {
  inp.style.borderColor='var(--ko-bd)'; inp.placeholder=msg;
  inp.animate(
    [{transform:'translateX(-4px)'},{transform:'translateX(4px)'},{transform:'translateX(0)'}],
    {duration:240}
  );
  setTimeout(()=>{ inp.style.borderColor=''; inp.placeholder='Entrez le nom d\'une carte…'; }, 1500);
}

// ── AUTOCOMPLETE ──────────────────────────────────────────

function onIn() {
  const v=$('gi').value.toLowerCase().trim();
  const l=$('acl'); l.innerHTML='';
  if(mode==='daily') dSel=-1; else sSel=-1;
  if(!v||!loaded) return;
  const done=new Set((mode==='daily'?dG:sG).map(x=>x.m.name));

  // Tri : commence par le terme en premier, puis contient
  const starts = CARDS.filter(x=>x.name.toLowerCase().startsWith(v) && !done.has(x.name));
  const contains = CARDS.filter(x=>!x.name.toLowerCase().startsWith(v) && x.name.toLowerCase().includes(v) && !done.has(x.name));
  const results = [...starts, ...contains].slice(0, 10);

  results.forEach(x=>{
    const i=document.createElement('div'); i.className='aci';
    i.innerHTML=x.name+'<span class="acb">'+x.frameType+' · '+(x.attribute!=='—'?x.attribute:x.race)+'</span>';
    i.onclick=()=>{ $('gi').value=x.name; l.innerHTML=''; sub(); };
    l.appendChild(i);
  });
}

function onKD(e) {
  const l=$('acl'); const items=l.querySelectorAll('.aci');
  let sel=mode==='daily'?dSel:sSel;
  if(e.key==='ArrowDown'){
    e.preventDefault(); sel=Math.min(sel+1,items.length-1);
    items.forEach((x,i)=>x.classList.toggle('sel',i===sel));
    if(items[sel]) $('gi').value=items[sel].firstChild.textContent.trim();
  } else if(e.key==='ArrowUp'){
    e.preventDefault(); sel=Math.max(sel-1,-1);
    items.forEach((x,i)=>x.classList.toggle('sel',i===sel));
    if(sel>=0&&items[sel]) $('gi').value=items[sel].firstChild.textContent.trim();
  } else if(e.key==='Enter'){
    e.preventDefault(); l.innerHTML=''; sub();
  } else if(e.key==='Escape') l.innerHTML='';
  if(mode==='daily') dSel=sel; else sSel=sel;
}

document.addEventListener('click', e => { if(!e.target.closest('.acw')) $('acl').innerHTML=''; });
function toggleHelp(){ $('hpanel').classList.toggle('on'); }

// ── INIT ──────────────────────────────────────────────────
loadRec();
updDots();
loadCards();
