// ══════════════════════════════════════════════════════════
//  YUGINATOR — moteur entropique pur JS, zéro IA
//  Branché sur YGOPRODeck (même normalize() que guesser.js)
// ══════════════════════════════════════════════════════════

// ── NORMALISATION (identique à guesser.js) ────────────────

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
  const map = { 'Banned':'Interdit','Limited':'Limité','Semi-Limited':'Semi-Limité' };
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

// ── CHARGEMENT ────────────────────────────────────────────

let ALL_CARDS = [];
let yugiLoaded = false;

async function yugiLoadCards() {
  const bar = document.getElementById('yLoadBar');
  if (bar) bar.style.display = 'flex';

  try {
    const resp = await fetch('https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes&language=fr');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const json = await resp.json();
    const seen = new Set();
    for (const c of (json.data || [])) {
      if (!seen.has(c.id)) { seen.add(c.id); ALL_CARDS.push(normalize(c)); }
    }
    yugiLoaded = true;
    if (bar) {
      bar.textContent = '✅ ' + ALL_CARDS.length.toLocaleString('fr') + ' cartes chargées';
      setTimeout(() => bar.style.display = 'none', 1200);
    }
    yugiInit();
  } catch(e) {
    if (bar) bar.textContent = '❌ ' + e.message;
    console.error(e);
  }
}

// ══════════════════════════════════════════════════════════
//  MOTEUR ENTROPIQUE
// ══════════════════════════════════════════════════════════

// ── GÉNÉRATEUR DE QUESTIONS ───────────────────────────────
// Chaque question est un prédicat sur une carte.
// On génère dynamiquement les questions depuis les valeurs
// présentes dans le pool courant.

const ATK_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000, 3500];
const DEF_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000];
const LVL_THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12];

function buildQuestions(pool) {
  const qs = [];

  // Valeurs distinctes dans le pool
  const frames    = [...new Set(pool.map(c => c.frameType))].filter(v => v && v !== '—');
  const attrs     = [...new Set(pool.map(c => c.attribute))].filter(v => v && v !== '—');
  const races     = [...new Set(pool.map(c => c.race))].filter(v => v && v !== '—');
  const archetypes= [...new Set(pool.map(c => c.archetype))].filter(v => v && v !== '—');
  const bans      = [...new Set(pool.map(c => c.ban))];
  const formats   = [...new Set(pool.map(c => c.format))];

  // Questions par valeur exacte (frameType, attribut, race, archétype, ban, format)
  frames.forEach(v => qs.push({
    label: `Est-ce une carte de type "${v}" ?`,
    key: 'frameType_eq_' + v,
    test: c => c.frameType === v,
    group: 'frameType',
  }));

  attrs.forEach(v => qs.push({
    label: `Est-ce que l'attribut est "${v}" ?`,
    key: 'attr_eq_' + v,
    test: c => c.attribute === v,
    group: 'attribute',
  }));

  races.forEach(v => qs.push({
    label: `Est-ce un monstre de type "${v}" ?`,
    key: 'race_eq_' + v,
    test: c => c.race === v,
    group: 'race',
  }));

  archetypes.forEach(v => qs.push({
    label: `Est-ce une carte de l'archétype "${v}" ?`,
    key: 'arch_eq_' + v,
    test: c => c.archetype === v,
    group: 'archetype',
  }));

  bans.forEach(v => qs.push({
    label: `Est-ce que la carte est "${v}" sur la Banlist ?`,
    key: 'ban_eq_' + v,
    test: c => c.ban === v,
    group: 'ban',
  }));

  formats.forEach(v => qs.push({
    label: `Est-ce une carte du format "${v}" ?`,
    key: 'format_eq_' + v,
    test: c => c.format === v,
    group: 'format',
  }));

  // Questions de seuil (ATK, DEF, Niveau)
  ATK_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que l'ATK est supérieure ou égale à ${t} ?`,
    key: 'atk_gte_' + t,
    test: c => c.atk >= 0 && c.atk >= t,
    group: 'atk',
  }));

  DEF_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que la DEF est supérieure ou égale à ${t} ?`,
    key: 'def_gte_' + t,
    test: c => c.def >= 0 && c.def >= t,
    group: 'def',
  }));

  LVL_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que le Niveau / Rang est supérieur ou égal à ${t} ?`,
    key: 'lvl_gte_' + t,
    test: c => c.level >= t,
    group: 'level',
  }));

  return qs;
}

// ── SCORE D'ENTROPIE ──────────────────────────────────────
// Score = 1 - |ratio - 0.5| * 2   → 1.0 si 50/50, 0 si 100/0
// On filtre les questions déjà posées et celles dont le groupe
// est déjà résolu (on connaît déjà la valeur exacte).

function bestQuestion(pool, askedKeys, resolvedGroups) {
  const qs = buildQuestions(pool).filter(q =>
    !askedKeys.has(q.key) && !resolvedGroups.has(q.group)
  );

  let best = null, bestScore = -1;
  for (const q of qs) {
    const yes = pool.filter(q.test).length;
    const no  = pool.length - yes;
    if (yes === 0 || no === 0) continue; // question inutile
    const ratio = yes / pool.length;
    const score = 1 - Math.abs(ratio - 0.5) * 2;
    if (score > bestScore) { bestScore = score; best = q; }
  }
  return best; // null si plus rien à demander
}

// ══════════════════════════════════════════════════════════
//  ÉTAT DU JEU
// ══════════════════════════════════════════════════════════

let yPool = [];          // cartes candidates restantes
let yAsked = new Set();  // clés des questions posées
let yResolved = new Set(); // groupes dont la valeur est fixée
let yHistory = [];       // [{q, label, ans}]
let yGuessIdx = 0;       // index dans les candidates triées pour devinette
let yGameOver = false;
let yCurQ = null;        // question courante {label, key, test, group}
let yThinking = false;
let yQCount = 0;

const GUESS_THRESHOLD = 4; // devine quand pool ≤ N cartes

// ── INIT ──────────────────────────────────────────────────

function yugiInit() {
  yPool = ALL_CARDS.slice();
  yAsked = new Set();
  yResolved = new Set();
  yHistory = [];
  yGuessIdx = 0;
  yGameOver = false;
  yCurQ = null;
  yThinking = false;
  yQCount = 0;

  renderHistory();
  updatePoolInfo();
  nextStep();
}

// ── ÉTAPE SUIVANTE : question ou devinette ─────────────────

function nextStep() {
  if (yGameOver) return;

  // Si pool assez petit → devinette
  if (yPool.length <= GUESS_THRESHOLD && yPool.length > 0) {
    showGuessStep();
    return;
  }
  if (yPool.length === 0) {
    showGiveUp();
    return;
  }

  // Cherche la meilleure question
  const q = bestQuestion(yPool, yAsked, yResolved);
  if (!q) {
    // Plus de questions utiles → devinette forcée
    showGuessStep();
    return;
  }

  yCurQ = q;
  showQuestion(q);
}

// ── AFFICHAGE QUESTION ────────────────────────────────────

function showQuestion(q) {
  yThinking = false;
  setUI('question');
  document.getElementById('yQnum').textContent = 'QUESTION ' + (yQCount + 1);
  document.getElementById('yQtext').textContent = q.label;
  const pct = Math.round(Math.max(5, Math.min(95, (1 - yPool.length / ALL_CARDS.length) * 100)));
  document.getElementById('yConf').textContent = pct + '%';
  document.getElementById('yProgFill').style.width = pct + '%';
}

// ── RÉPONSE UTILISATEUR ───────────────────────────────────

function yugiAnswer(ans) {
  if (yThinking || yGameOver || !yCurQ) return;

  const q = yCurQ;
  yAsked.add(q.key);
  yQCount++;

  // Filtre le pool
  let newPool;
  if (ans === 'oui') {
    newPool = yPool.filter(q.test);
    // Si réponse exacte connue → marque le groupe comme résolu
    if (q.key.includes('_eq_')) yResolved.add(q.group);
  } else if (ans === 'non') {
    newPool = yPool.filter(c => !q.test(c));
  } else {
    // "je ne sais pas" → on ne filtre pas, on marque juste comme posée
    newPool = yPool;
  }

  // Évite un pool vide suite à une mauvaise réponse de l'utilisateur
  yPool = newPool.length > 0 ? newPool : yPool;

  // Historique
  const labels = { oui:'OUI', non:'NON', ne_sais_pas:'?' };
  yHistory.push({ label: q.label, ans: labels[ans] || ans, pool: yPool.length });
  renderHistory();
  updatePoolInfo();

  // Pause visuelle
  yThinking = true;
  setUI('thinking');
  setTimeout(() => nextStep(), 500);
}

// ── DEVINETTE ─────────────────────────────────────────────

function showGuessStep() {
  // Trie le pool par "notoriété" approximative : on devine d'abord
  // les cartes avec ATK/DEF/level les plus iconiques (heuristique simple)
  const sorted = yPool.slice().sort((a, b) => {
    // Favorise les cartes avec attribut connu et ATK élevée
    const sa = (a.atk > 0 ? a.atk : 0) + (a.level > 0 ? a.level * 50 : 0);
    const sb = (b.atk > 0 ? b.atk : 0) + (b.level > 0 ? b.level * 50 : 0);
    return sb - sa;
  });

  if (yGuessIdx >= sorted.length) { showGiveUp(); return; }
  const card = sorted[yGuessIdx];
  yGuessIdx++;

  setUI('guess');
  document.getElementById('yQnum').textContent = '🎯 DEVINETTE ' + yGuessIdx;
  document.getElementById('yQtext').textContent = 'Est-ce que vous pensez à… ' + card.name + ' ?';
  const pct = Math.round(Math.min(98, 70 + yQCount * 2));
  document.getElementById('yConf').textContent = pct + '%';
  document.getElementById('yProgFill').style.width = pct + '%';

  // Stocke la carte pour confirmGuess
  document.getElementById('yAnswers').dataset.guessCard = card.name;
  document.getElementById('yAnswers').dataset.guessImg  = card.img || '';
}

function yugiConfirmGuess(ok) {
  const name = document.getElementById('yAnswers').dataset.guessCard;
  const img  = document.getElementById('yAnswers').dataset.guessImg;
  if (ok) {
    yGameOver = true;
    setUI('none');
    showResult(true, name, img);
  } else {
    // Retire la carte du pool et continue
    yPool = yPool.filter(c => c.name !== name);
    yHistory.push({ label: 'Est-ce ' + name + ' ?', ans: 'NON', pool: yPool.length });
    renderHistory();
    updatePoolInfo();
    yThinking = true;
    setUI('thinking');
    setTimeout(() => {
      if (yPool.length === 0) { showGiveUp(); return; }
      showGuessStep();
    }, 500);
  }
}

function showGiveUp() {
  yGameOver = true;
  setUI('none');
  showResult(false, null, null);
}

// ── RÉSULTAT ──────────────────────────────────────────────

function showResult(won, name, img) {
  const r = document.getElementById('yResult');
  r.className = 'y-result on ' + (won ? 'win' : 'def');
  document.getElementById('yRttl').textContent = won
    ? '🃏 TROUVÉ EN ' + yQCount + ' QUESTION' + (yQCount > 1 ? 'S' : '')
    : '☠ LE YUGINATOR S\'INCLINE';
  document.getElementById('yRcard').textContent = won ? name : '???';
  if (img && document.getElementById('yRimg')) {
    document.getElementById('yRimg').src = img;
    document.getElementById('yRimg').style.display = img ? 'block' : 'none';
  }
  document.getElementById('yRdesc').textContent = won
    ? 'Le Yuginator a percé le voile en analysant ' + yQCount + ' réponses et ' + ALL_CARDS.length.toLocaleString('fr') + ' cartes.'
    : 'Votre carte a résisté à l\'analyse. ' + yPool.length + ' candidates restaient. Quelle était-elle ?';
  document.getElementById('yRestart').classList.add('on');
}

// ── UI HELPERS ────────────────────────────────────────────

function setUI(mode) {
  const ans = document.getElementById('yAnswers');
  const orb = document.getElementById('yOrb');

  if (mode === 'thinking') {
    orb.classList.add('thinking'); orb.textContent = '⚡';
    document.getElementById('yQnum').textContent = 'ANALYSE EN COURS…';
    document.getElementById('yQtext').textContent = '…';
    ans.style.display = 'none';
    return;
  }

  orb.classList.remove('thinking');
  orb.textContent = mode === 'guess' ? '🎯' : '🔮';

  if (mode === 'none') { ans.style.display = 'none'; return; }

  ans.style.display = 'flex';

  if (mode === 'question') {
    ans.innerHTML = `
      <button class="y-btn yes"     onclick="yugiAnswer('oui')">✅ OUI</button>
      <button class="y-btn pyesbtn" onclick="yugiAnswer('plutot_oui')">🟡 PLUTÔT OUI</button>
      <button class="y-btn pnobtn"  onclick="yugiAnswer('plutot_non')">🟠 PLUTÔT NON</button>
      <button class="y-btn no"      onclick="yugiAnswer('non')">❌ NON</button>
      <button class="y-btn idk"     onclick="yugiAnswer('ne_sais_pas')">🤷 JE NE SAIS PAS</button>`;
  } else if (mode === 'guess') {
    ans.innerHTML = `
      <button class="y-btn yes" onclick="yugiConfirmGuess(true)">✅ OUI, C'EST ÇA !</button>
      <button class="y-btn no"  onclick="yugiConfirmGuess(false)">❌ NON, CE N'EST PAS ÇA</button>`;
  }
}

function updatePoolInfo() {
  const el = document.getElementById('yPoolInfo');
  if (el) el.textContent = yPool.length.toLocaleString('fr') + ' carte' + (yPool.length > 1 ? 's' : '') + ' restante' + (yPool.length > 1 ? 's' : '');
}

function renderHistory() {
  const list = document.getElementById('yHist');
  if (!list) return;
  list.innerHTML = '';
  [...yHistory].reverse().forEach(h => {
    const item = document.createElement('div'); item.className = 'y-hi';
    const cls = h.ans === 'OUI' ? 'yes' : h.ans === 'NON' ? 'no' : 'idk';
    item.innerHTML = `<span class="hq">${h.label}</span><span class="ha ${cls}">${h.ans}</span>`;
    if (h.pool !== undefined) {
      const pi = document.createElement('span');
      pi.className = 'hpool';
      pi.textContent = h.pool.toLocaleString('fr') + ' restantes';
      item.appendChild(pi);
    }
    list.appendChild(item);
  });
}

function yugiRestart() {
  document.getElementById('yResult').className = 'y-result';
  document.getElementById('yRestart').classList.remove('on');
  document.getElementById('yOrb').textContent = '🔮';
  document.getElementById('yOrb').className = 'y-orb';
  document.getElementById('yHist').innerHTML = '';
  document.getElementById('yProgFill').style.width = '0%';
  document.getElementById('yConf').textContent = '0%';
  const rimg = document.getElementById('yRimg');
  if (rimg) { rimg.src = ''; rimg.style.display = 'none'; }
  yugiInit();
}

// ── BOOTSTRAP ─────────────────────────────────────────────
// Appelé par le HTML quand la page est prête :
//   yugiLoadCards();
