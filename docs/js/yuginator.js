// ══════════════════════════════════════════════════════════
//  YUGINATOR — moteur entropique pur JS, zéro IA
//  Branché sur YGOPRODeck (même normalize() que guesser.js)
// ══════════════════════════════════════════════════════════

// ── NORMALISATION ─────────────────────────────────────────

// Catégories de frameType pour distinguer monstre/magie/piège
const MONSTER_FRAMES = new Set(['Normal','Effet','Rituel','Fusion','Synchro','XYZ','Link','Pendule','Jeton','Skill']);
const SPELL_FRAMES   = new Set(['Magie']);
const TRAP_FRAMES    = new Set(['Piège']);

// Sous-types "race" qui appartiennent aux sorts/pièges
const SPELL_RACES = new Set(['Normal','Continu','Contre','Jeu rapide','Équipement','Terrain','Rituel']);

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
    img:       raw.card_images?.[0]?.image_url_small || '',
  };
}

// ── CHARGEMENT ────────────────────────────────────────────

let ALL_CARDS = [];
let yugiLoaded = false;

async function yugiLoadCards() {
  const bar = document.getElementById('yLoadBar');
  if (bar) { bar.style.display = 'flex'; bar.textContent = '⚡ Chargement des cartes…'; }

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
      setTimeout(() => { bar.style.display = 'none'; }, 1200);
    }
    yugiInit();
  } catch(e) {
    if (bar) bar.textContent = '❌ ' + e.message;
    console.error(e);
  }
}

// ══════════════════════════════════════════════════════════
//  GÉNÉRATEUR DE QUESTIONS
// ══════════════════════════════════════════════════════════

const ATK_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000, 3500];
const DEF_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000];
const LVL_THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12];

// Détermine si le pool contient surtout des monstres, sorts, pièges ou un mix
function poolContext(pool) {
  const monsters = pool.filter(c => MONSTER_FRAMES.has(c.frameType)).length;
  const spells   = pool.filter(c => SPELL_FRAMES.has(c.frameType)).length;
  const traps    = pool.filter(c => TRAP_FRAMES.has(c.frameType)).length;
  const total    = pool.length;
  if (monsters / total > 0.8) return 'monster';
  if (spells   / total > 0.8) return 'spell';
  if (traps    / total > 0.8) return 'trap';
  return 'mixed';
}

// Label contextuel pour la race (sous-type)
function raceLabel(v, ctx) {
  if (ctx === 'monster') return `Est-ce un monstre de type "${v}" ?`;
  if (ctx === 'spell')   return `Est-ce une carte Magie de type "${v}" ?`;
  if (ctx === 'trap')    return `Est-ce une carte Piège de type "${v}" ?`;
  // mixed : détermine au cas par cas
  if (SPELL_RACES.has(v)) return `Est-ce une carte Magie/Piège de sous-type "${v}" ?`;
  return `Est-ce un monstre de type "${v}" ?`;
}

function buildQuestions(pool) {
  const qs  = [];
  const ctx = poolContext(pool);

  const frames     = [...new Set(pool.map(c => c.frameType))].filter(v => v && v !== '—');
  const attrs      = [...new Set(pool.map(c => c.attribute))].filter(v => v && v !== '—');
  const races      = [...new Set(pool.map(c => c.race))].filter(v => v && v !== '—');
  const archetypes = [...new Set(pool.map(c => c.archetype))].filter(v => v && v !== '—');
  const bans       = [...new Set(pool.map(c => c.ban))];

  // ── Type de carte (frameType)
  frames.forEach(v => qs.push({
    label: `Est-ce une carte "${v}" ?`,
    key: 'frameType_eq_' + v,
    test: c => c.frameType === v,
    group: 'frameType',
  }));

  // ── Attribut (monstres)
  attrs.forEach(v => {
    if (v === '—') return;
    qs.push({
      label: `Est-ce que l'attribut est "${v}" ?`,
      key: 'attr_eq_' + v,
      test: c => c.attribute === v,
      group: 'attribute',
    });
  });

  // ── Race / sous-type (label adapté au contexte)
  races.forEach(v => qs.push({
    label: raceLabel(v, ctx),
    key: 'race_eq_' + v,
    test: c => c.race === v,
    group: 'race',
  }));

  // ── Archétype
  archetypes.forEach(v => qs.push({
    label: `Est-ce une carte de l'archétype "${v}" ?`,
    key: 'arch_eq_' + v,
    test: c => c.archetype === v,
    group: 'archetype',
  }));

  // ── Banlist (seulement si plusieurs valeurs présentes)
  if (bans.length > 1) {
    bans.forEach(v => qs.push({
      label: `Est-ce que la carte est "${v}" sur la Banlist TCG ?`,
      key: 'ban_eq_' + v,
      test: c => c.ban === v,
      group: 'ban',
    }));
  }

  // ── Seuils ATK / DEF / Niveau (seulement si pertinents dans le pool)
  const hasAtk = pool.some(c => c.atk >= 0);
  const hasDef = pool.some(c => c.def >= 0);
  const hasLvl = pool.some(c => c.level > 0);

  if (hasAtk) ATK_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que l'ATK est ≥ ${t} ?`,
    key: 'atk_gte_' + t,
    test: c => c.atk >= 0 && c.atk >= t,
    group: 'atk',
  }));

  if (hasDef) DEF_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que la DEF est ≥ ${t} ?`,
    key: 'def_gte_' + t,
    test: c => c.def >= 0 && c.def >= t,
    group: 'def',
  }));

  if (hasLvl) LVL_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que le Niveau / Rang est ≥ ${t} ?`,
    key: 'lvl_gte_' + t,
    test: c => c.level >= t,
    group: 'level',
  }));

  return qs;
}

// ── SCORE D'ENTROPIE ──────────────────────────────────────
// Score = 1 - |ratio - 0.5| * 2  →  1.0 si 50/50, 0 si 100/0

function bestQuestion(pool, askedKeys, resolvedGroups) {
  const qs = buildQuestions(pool).filter(q =>
    !askedKeys.has(q.key) && !resolvedGroups.has(q.group)
  );

  let best = null, bestScore = -1;
  for (const q of qs) {
    const yes = pool.filter(q.test).length;
    const no  = pool.length - yes;
    if (yes === 0 || no === 0) continue;
    const ratio = yes / pool.length;
    const score = 1 - Math.abs(ratio - 0.5) * 2;
    if (score > bestScore) { bestScore = score; best = q; }
  }
  return best;
}

// ══════════════════════════════════════════════════════════
//  ÉTAT DU JEU
// ══════════════════════════════════════════════════════════

let yPool      = [];
let yAsked     = new Set();
let yResolved  = new Set();
let yHistory   = [];
let yGuessIdx  = 0;
let yGameOver  = false;
let yCurQ      = null;
let yThinking  = false;
let yQCount    = 0;
// Pool trié mémorisé pour la phase devinette (stable entre tentatives)
let ySortedPool = [];

const GUESS_THRESHOLD = 5;

// ── INIT ──────────────────────────────────────────────────

function yugiInit() {
  yPool      = ALL_CARDS.slice();
  yAsked     = new Set();
  yResolved  = new Set();
  yHistory   = [];
  yGuessIdx  = 0;
  yGameOver  = false;
  yCurQ      = null;
  yThinking  = false;
  yQCount    = 0;
  ySortedPool = [];

  document.getElementById('yResult').className = 'y-result';
  document.getElementById('yRestart').classList.remove('on');
  const rimg = document.getElementById('yRimg');
  if (rimg) { rimg.src = ''; rimg.style.display = 'none'; }

  renderHistory();
  updatePoolInfo();
  nextStep();
}

// ── ÉTAPE SUIVANTE ─────────────────────────────────────────

function nextStep() {
  if (yGameOver) return;

  if (yPool.length === 0) { showGiveUp(); return; }

  if (yPool.length <= GUESS_THRESHOLD) {
    enterGuessPhase();
    return;
  }

  const q = bestQuestion(yPool, yAsked, yResolved);
  if (!q) { enterGuessPhase(); return; }

  yCurQ = q;
  showQuestion(q);
}

// ── AFFICHAGE QUESTION ────────────────────────────────────

function showQuestion(q) {
  yThinking = false;
  setUI('question');
  document.getElementById('yQnum').textContent = 'QUESTION ' + (yQCount + 1);
  document.getElementById('yQtext').textContent = q.label;
  updateProgress();
}

function updateProgress() {
  const pct = Math.round(Math.max(5, Math.min(95, (1 - yPool.length / ALL_CARDS.length) * 100)));
  document.getElementById('yConf').textContent = pct + '%';
  document.getElementById('yProgFill').style.width = pct + '%';
}

// ── RÉPONSE UTILISATEUR ───────────────────────────────────
// "plutôt oui" → garde 80 % des cartes qui passent le test + 20 % qui ne passent pas
// "plutôt non" → inverse
// Cela conserve l'incertitude sans bloquer complètement les candidats

function applyAnswer(pool, q, ans) {
  if (ans === 'oui') {
    const filtered = pool.filter(q.test);
    return filtered.length > 0 ? filtered : pool;
  }
  if (ans === 'non') {
    const filtered = pool.filter(c => !q.test(c));
    return filtered.length > 0 ? filtered : pool;
  }
  if (ans === 'plutot_oui') {
    // Garde les "oui" + 15 % des "non" (bruit)
    const yes = pool.filter(q.test);
    const no  = pool.filter(c => !q.test(c));
    const kept = no.filter((_, i) => i % 7 === 0); // ~14 %
    const merged = [...yes, ...kept];
    return merged.length > 0 ? merged : pool;
  }
  if (ans === 'plutot_non') {
    const yes = pool.filter(q.test);
    const no  = pool.filter(c => !q.test(c));
    const kept = yes.filter((_, i) => i % 7 === 0);
    const merged = [...no, ...kept];
    return merged.length > 0 ? merged : pool;
  }
  // ne_sais_pas → pas de filtre
  return pool;
}

function yugiAnswer(ans) {
  if (yThinking || yGameOver || !yCurQ) return;

  const q = yCurQ;
  yAsked.add(q.key);
  yQCount++;

  const newPool = applyAnswer(yPool, q, ans);
  yPool = newPool;

  // Marque le groupe résolu seulement pour une réponse franche "oui" exacte
  if (ans === 'oui' && q.key.includes('_eq_')) {
    yResolved.add(q.group);
  }

  const ansLabel = { oui:'OUI', non:'NON', plutot_oui:'~OUI', plutot_non:'~NON', ne_sais_pas:'?' };
  yHistory.push({ label: q.label, ans: ansLabel[ans] || ans, pool: yPool.length });
  renderHistory();
  updatePoolInfo();

  yThinking = true;
  setUI('thinking');
  setTimeout(() => nextStep(), 500);
}

// ── PHASE DEVINETTE ───────────────────────────────────────

function enterGuessPhase() {
  // Construit le pool trié une seule fois à l'entrée en phase devinette
  ySortedPool = yPool.slice().sort((a, b) => {
    // Heuristique notoriété : ATK élevée + niveau élevé en priorité
    const sa = (a.atk > 0 ? a.atk : 0) + (a.level > 0 ? a.level * 50 : 0);
    const sb = (b.atk > 0 ? b.atk : 0) + (b.level > 0 ? b.level * 50 : 0);
    return sb - sa;
  });
  yGuessIdx = 0;
  showGuessStep();
}

function showGuessStep() {
  if (yGuessIdx >= ySortedPool.length) { showGiveUp(); return; }
  const card = ySortedPool[yGuessIdx];
  yGuessIdx++;

  setUI('guess');
  document.getElementById('yQnum').textContent = '🎯 DEVINETTE ' + yGuessIdx;
  document.getElementById('yQtext').textContent = 'Est-ce que vous pensez à… ' + card.name + ' ?';

  const pct = Math.min(99, 65 + yQCount * 3);
  document.getElementById('yConf').textContent = pct + '%';
  document.getElementById('yProgFill').style.width = pct + '%';

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
    // Retire la carte du pool global ET du pool trié
    yPool       = yPool.filter(c => c.name !== name);
    ySortedPool = ySortedPool.filter(c => c.name !== name);

    yHistory.push({ label: 'Est-ce ' + name + ' ?', ans: 'NON', pool: yPool.length });
    renderHistory();
    updatePoolInfo();

    yThinking = true;
    setUI('thinking');
    setTimeout(() => {
      if (ySortedPool.length === 0) { showGiveUp(); return; }
      showGuessStep();
    }, 400);
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

  const rimg = document.getElementById('yRimg');
  if (rimg) {
    if (won && img) {
      rimg.src = img;
      rimg.style.display = 'block';
    } else {
      rimg.style.display = 'none';
    }
  }

  document.getElementById('yRdesc').textContent = won
    ? 'Le Yuginator a percé le voile en ' + yQCount + ' réponse' + (yQCount > 1 ? 's' : '') + ' sur ' + ALL_CARDS.length.toLocaleString('fr') + ' cartes.'
    : 'Votre carte a résisté à l\'analyse. ' + yPool.length + ' candidate' + (yPool.length > 1 ? 's' : '') + ' restai' + (yPool.length > 1 ? 'ent' : 't') + '. Quelle était-elle ?';

  document.getElementById('yRestart').classList.add('on');
}

// ── UI HELPERS ────────────────────────────────────────────

function setUI(mode) {
  const ans = document.getElementById('yAnswers');
  const orb = document.getElementById('yOrb');

  if (mode === 'thinking') {
    orb.classList.add('thinking');
    orb.textContent = '⚡';
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
  if (el) {
    const n = yPool.length;
    el.textContent = n.toLocaleString('fr') + ' carte' + (n > 1 ? 's' : '') + ' restante' + (n > 1 ? 's' : '');
  }
}

function renderHistory() {
  const list = document.getElementById('yHist');
  if (!list) return;
  list.innerHTML = '';
  [...yHistory].reverse().forEach(h => {
    const item = document.createElement('div');
    item.className = 'y-hi';
    const clsMap = { 'OUI':'yes', 'NON':'no', '~OUI':'pyesbtn', '~NON':'pnobtn', '?':'idk' };
    const cls = clsMap[h.ans] || 'idk';
    item.innerHTML = `<span class="hq">${h.label}</span><span class="ha ${cls}">${h.ans}</span>`;
    if (h.pool !== undefined) {
      const pi = document.createElement('span');
      pi.className = 'hpool';
      pi.textContent = h.pool.toLocaleString('fr');
      item.appendChild(pi);
    }
    list.appendChild(item);
  });
  // Scroll vers le haut (entrée la plus récente)
  list.scrollTop = 0;
}

function yugiRestart() {
  document.getElementById('yOrb').textContent = '🔮';
  document.getElementById('yOrb').className = 'y-orb';
  document.getElementById('yHist').innerHTML = '';
  document.getElementById('yProgFill').style.width = '0%';
  document.getElementById('yConf').textContent = '0%';
  yugiInit();
}

// ── BOOTSTRAP (appelé depuis le HTML) ─────────────────────
// startGame() → yugiLoadCards() → yugiInit()
