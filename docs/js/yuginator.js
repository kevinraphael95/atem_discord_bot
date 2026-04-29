// ══════════════════════════════════════════════════════════
//  YUGINATOR — moteur entropique pur JS, zéro IA
//  Branché sur YGOPRODeck (même normalize() que guesser.js)
//
//  AMÉLIORATIONS :
//  - Pas plus de 5 devinettes consécutives sans question intermédiaire
//  - Bouton Annuler : revenir en arrière sur la dernière réponse
//  - Questions supplémentaires (longueur du nom, mots-clés)
//  - Légère randomisation à partir de la 4e question
// ══════════════════════════════════════════════════════════

// ── NORMALISATION ─────────────────────────────────────────

const MONSTER_FRAMES = new Set(['Normal','Effet','Rituel','Fusion','Synchro','XYZ','Link','Pendule','Jeton','Skill']);
const SPELL_FRAMES   = new Set(['Magie']);
const TRAP_FRAMES    = new Set(['Piège']);
const SPELL_RACES    = new Set(['Normal','Continu','Contre','Jeu rapide','Équipement','Terrain','Rituel']);

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

function raceLabel(v, ctx) {
  if (ctx === 'monster') return `Est-ce un monstre de type "${v}" ?`;
  if (ctx === 'spell')   return `Est-ce une carte Magie de type "${v}" ?`;
  if (ctx === 'trap')    return `Est-ce une carte Piège de type "${v}" ?`;
  if (SPELL_RACES.has(v)) return `Est-ce une carte Magie/Piège de sous-type "${v}" ?`;
  return `Est-ce un monstre de type "${v}" ?`;
}

function buildQuestions(pool) {
  const qs  = [];
  const ctx = poolContext(pool);

  const frames     = [...new Set(pool.map(c => c.frameType))].filter(v => v && v !== '—');
  const attrs      = [...new Set(pool.map(c => c.attribute))].filter(v => v && v !== '—');
  const races      = [...new Set(pool.map(c => c.race))].filter(v => v && v !== '—');
  const bans       = [...new Set(pool.map(c => c.ban))];

  const hasArchPool  = pool.filter(c => c.archetype !== '—').length;
  const noArchPool   = pool.length - hasArchPool;
  const archetypes   = [...new Set(pool.map(c => c.archetype))].filter(v => v && v !== '—');

  // ── Catégorie générale monstre / magie / piège
  const nMonsters = pool.filter(c => MONSTER_FRAMES.has(c.frameType)).length;
  const nSpells   = pool.filter(c => SPELL_FRAMES.has(c.frameType)).length;
  const nTraps    = pool.filter(c => TRAP_FRAMES.has(c.frameType)).length;
  if (nMonsters > 0 && (nSpells > 0 || nTraps > 0))
    qs.push({ label: "Est-ce un monstre ?", key: 'cat_monster', test: c => MONSTER_FRAMES.has(c.frameType), group: 'cardcat' });
  if (nSpells > 0 && (nMonsters > 0 || nTraps > 0))
    qs.push({ label: "Est-ce une carte Magie ?", key: 'cat_spell', test: c => SPELL_FRAMES.has(c.frameType), group: 'cardcat' });
  if (nTraps > 0 && (nMonsters > 0 || nSpells > 0))
    qs.push({ label: "Est-ce une carte Piège ?", key: 'cat_trap', test: c => TRAP_FRAMES.has(c.frameType), group: 'cardcat' });

  // ── frameType détaillé
  frames.forEach(v => qs.push({
    label: `Est-ce une carte "${v}" ?`,
    key: 'frameType_eq_' + v,
    test: c => c.frameType === v,
    group: 'frameType',
  }));

  // ── Attribut
  attrs.forEach(v => {
    if (v === '—') return;
    qs.push({
      label: `Est-ce que l'attribut est "${v}" ?`,
      key: 'attr_eq_' + v,
      test: c => c.attribute === v,
      group: 'attribute',
    });
  });

  // ── Race / sous-type
  races.forEach(v => qs.push({
    label: raceLabel(v, ctx),
    key: 'race_eq_' + v,
    test: c => c.race === v,
    group: 'race',
  }));

  // ── Archétype : appartenance puis valeurs
  if (hasArchPool > 0 && noArchPool > 0)
    qs.push({
      label: `Est-ce que la carte appartient à un archétype ?`,
      key: 'has_archetype',
      test: c => c.archetype !== '—',
      group: 'has_archetype',
    });

  const MAX_ARCH = 40;
  const archScored = archetypes.map(v => {
    const yes = pool.filter(c => c.archetype === v).length;
    const ratio = yes / pool.length;
    return { v, score: 1 - Math.abs(ratio - 0.5) * 2 };
  }).sort((a, b) => b.score - a.score).slice(0, MAX_ARCH);
  archScored.forEach(({ v }) => qs.push({
    label: `Est-ce une carte de l'archétype "${v}" ?`,
    key: 'arch_eq_' + v,
    test: c => c.archetype === v,
    group: 'archetype',
  }));

  // ── Banlist
  if (bans.length > 1)
    bans.forEach(v => qs.push({
      label: `Est-ce que la carte est "${v}" sur la Banlist TCG ?`,
      key: 'ban_eq_' + v,
      test: c => c.ban === v,
      group: 'ban',
    }));

  // ── ATK / DEF / Niveau
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

  // ── Questions sur le nom (seuil abaissé à 3000 pour intervenir plus tôt)
  const NAME_POOL_THRESHOLD = 3000;

  if (pool.length <= NAME_POOL_THRESHOLD) {
    const nameInRange = (c, a, z) => { const l = (c.name[0] || '').toUpperCase(); return l >= a && l <= z; };
    [
      { label: "Le nom commence-t-il par une lettre entre A et M ?", key: 'name_AM', test: c => nameInRange(c,'A','M') },
      { label: "Le nom commence-t-il par une lettre entre N et Z ?", key: 'name_NZ', test: c => nameInRange(c,'N','Z') },
    ].forEach(q => qs.push({ ...q, group: 'name_alpha' }));
    [
      { label: "Le nom commence-t-il par une lettre entre A et F ?", key: 'name_AF', test: c => nameInRange(c,'A','F') },
      { label: "Le nom commence-t-il par une lettre entre G et M ?", key: 'name_GM', test: c => nameInRange(c,'G','M') },
      { label: "Le nom commence-t-il par une lettre entre N et S ?", key: 'name_NS', test: c => nameInRange(c,'N','S') },
      { label: "Le nom commence-t-il par une lettre entre T et Z ?", key: 'name_TZ', test: c => nameInRange(c,'T','Z') },
    ].forEach(q => qs.push({ ...q, group: 'name_alpha2' }));

    if (pool.length <= 200) {
      'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach(l => qs.push({
        label: `Le nom commence-t-il par la lettre "${l}" ?`,
        key: 'name_letter_' + l,
        test: c => (c.name[0] || '').toUpperCase() === l,
        group: 'name_letter',
      }));
    }

    // Longueur du nom (NOUVEAU)
    [5, 10, 15, 20].forEach(t => qs.push({
      label: `Le nom contient-il plus de ${t} caractères ?`,
      key: 'name_len_' + t,
      test: c => c.name.length > t,
      group: 'name_len',
    }));

    // Nombre de mots
    const wordCount = c => c.name.trim().split(/\s+/).length;
    [1, 2, 3, 4, 5].forEach(t => qs.push({
      label: `Le nom contient-il plus de ${t} mot${t > 1 ? 's' : ''} ?`,
      key: 'name_words_' + t,
      test: c => wordCount(c) > t,
      group: 'name_words',
    }));

    // Présence d'un chiffre dans le nom (NOUVEAU)
    qs.push({
      label: 'Le nom contient-il un chiffre ?',
      key: 'name_has_digit',
      test: c => /\d/.test(c.name),
      group: 'name_digit',
    });
  }

  // ── Mots fréquents du nom (seuil abaissé à 4000 pour être plus actif)
  if (pool.length > 6 && pool.length <= 4000) {
    const STOP = new Set(['de','du','des','le','la','les','un','une','et','en','a','au','aux',
      'par','sur','dans','pour','avec','sans','que','qui','ou','the','of','to','an','and','in','on','for','with','from']);
    const freq = {};
    pool.forEach(c => {
      c.name.split(/[\s\-\/''!?,.:]+/).forEach(w => {
        const wl = w.toLowerCase().replace(/[^a-z\u00c0-\u024f]/gi,'');
        if (wl.length >= 3 && !STOP.has(wl)) freq[wl] = (freq[wl]||0) + 1;
      });
    });
    const total = pool.length;
    Object.entries(freq)
      .filter(([,cnt]) => cnt >= total*0.1 && cnt <= total*0.9)
      .sort((a,b) => Math.abs(a[1]/total-0.5) - Math.abs(b[1]/total-0.5))
      .slice(0, 20)
      .forEach(([w]) => qs.push({
        label: `Le nom contient-il le mot "${w}" ?`,
        key: 'name_word_' + w,
        test: c => c.name.toLowerCase().includes(w),
        group: 'name_word',
      }));
  }

  return qs;
}

// ── SCORE D'ENTROPIE ──────────────────────────────────────

function scoreQ(q, pool) {
  const yes = pool.filter(q.test).length;
  const no  = pool.length - yes;
  if (yes === 0 || no === 0) return -1;
  return 1 - Math.abs(yes / pool.length - 0.5) * 2;
}

// ── SÉLECTION DE LA MEILLEURE QUESTION ────────────────────
//
//  RANDOMISATION PARTIELLE (demandée) :
//  - Les N_FIXED premières questions (cardcat, frameType, attribute, race)
//    sont choisies de façon déterministe (meilleur score entropique pur).
//  - À partir de la 4e question, on introduit un tirage pondéré parmi les
//    top-K candidats du groupe prioritaire courant, afin de varier les
//    parties sans sacrifier l'efficacité.

const N_FIXED = 3;    // les 3 premières questions restent stables
const RANDOM_TOP_K = 4; // parmi les 4 meilleures candidates, on tire au sort

const PRIORITY = [
  'cardcat', 'frameType', 'attribute', 'race',
  'has_archetype', 'archetype',
  'name_alpha', 'name_alpha2', 'name_letter',
  'name_words', 'name_len', 'name_digit', 'name_word',
];

function bestQuestion(pool, askedKeys, resolvedGroups, totalAsked) {
  const qs = buildQuestions(pool).filter(q =>
    !askedKeys.has(q.key) && !resolvedGroups.has(q.group)
  );

  const useRandom = totalAsked >= N_FIXED;

  // Cherche dans les groupes prioritaires dans l'ordre
  for (const grp of PRIORITY) {
    if (resolvedGroups.has(grp)) continue;
    const candidates = qs
      .filter(q => q.group === grp)
      .map(q => ({ q, s: scoreQ(q, pool) }))
      .filter(x => x.s >= 0)
      .sort((a, b) => b.s - a.s);
    if (candidates.length === 0) continue;

    if (!useRandom) {
      return candidates[0].q;
    }
    // Tirage pondéré parmi les top-K
    const pool2 = candidates.slice(0, RANDOM_TOP_K);
    const total = pool2.reduce((s, x) => s + x.s, 0);
    let r = Math.random() * total;
    for (const x of pool2) {
      r -= x.s;
      if (r <= 0) return x.q;
    }
    return pool2[0].q;
  }

  // Meilleur score global (fallback)
  const all = qs
    .map(q => ({ q, s: scoreQ(q, pool) }))
    .filter(x => x.s >= 0)
    .sort((a, b) => b.s - a.s);
  if (all.length === 0) return null;
  if (!useRandom) return all[0].q;
  const pool2 = all.slice(0, RANDOM_TOP_K);
  const total = pool2.reduce((s, x) => s + x.s, 0);
  let r = Math.random() * total;
  for (const x of pool2) { r -= x.s; if (r <= 0) return x.q; }
  return pool2[0].q;
}

// ══════════════════════════════════════════════════════════
//  ÉTAT DU JEU
// ══════════════════════════════════════════════════════════

let yPool      = [];
let yAsked     = new Set();
let yResolved  = new Set();
let yHistory   = [];   // { label, ans, ansLabel, pool, snapshot }
let yGuessIdx  = 0;
let yGameOver  = false;
let yCurQ      = null;
let yThinking  = false;
let yQCount    = 0;
let ySortedPool = [];

// ── Compteur de devinettes consécutives ──
// Quand on enchaîne trop de devinettes sans question intermédiaire,
// on force au moins une question avant de redeviner.
let yConsecGuesses = 0;
const MAX_CONSEC_GUESSES = 5;

const GUESS_THRESHOLD = 3;

// ── SNAPSHOT pour le bouton Annuler ──
// Chaque réponse sauvegarde l'état complet avant application.
function makeSnapshot() {
  return {
    pool:          yPool.slice(),
    asked:         new Set(yAsked),
    resolved:      new Set(yResolved),
    guessIdx:      yGuessIdx,
    sortedPool:    ySortedPool.slice(),
    qCount:        yQCount,
    consecGuesses: yConsecGuesses,
    curQ:          yCurQ,
  };
}
function restoreSnapshot(snap) {
  yPool          = snap.pool;
  yAsked         = snap.asked;
  yResolved      = snap.resolved;
  yGuessIdx      = snap.guessIdx;
  ySortedPool    = snap.sortedPool;
  yQCount        = snap.qCount;
  yConsecGuesses = snap.consecGuesses;
  yCurQ          = snap.curQ;
}

// ── INIT ──────────────────────────────────────────────────

function yugiInit() {
  yPool          = ALL_CARDS.slice();
  yAsked         = new Set();
  yResolved      = new Set();
  yHistory       = [];
  yGuessIdx      = 0;
  yGameOver      = false;
  yCurQ          = null;
  yThinking      = false;
  yQCount        = 0;
  ySortedPool    = [];
  yConsecGuesses = 0;

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

  // Forcer une question si on a enchaîné trop de devinettes
  if (yConsecGuesses >= MAX_CONSEC_GUESSES) {
    const q = bestQuestion(yPool, yAsked, yResolved, yQCount);
    if (q) {
      yConsecGuesses = 0;
      yCurQ = q;
      showQuestion(q);
      return;
    }
    // Vraiment plus de questions : on laisse passer en devinette
  }

  if (yPool.length <= GUESS_THRESHOLD) {
    enterGuessPhase();
    return;
  }

  const q = bestQuestion(yPool, yAsked, yResolved, yQCount);
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
    const yes = pool.filter(q.test);
    const no  = pool.filter(c => !q.test(c));
    const kept = no.filter((_, i) => i % 7 === 0);
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
  return pool; // ne_sais_pas
}

function yugiAnswer(ans) {
  if (yThinking || yGameOver || !yCurQ) return;

  const q = yCurQ;
  const snap = makeSnapshot();

  yAsked.add(q.key);
  yQCount++;

  yPool = applyAnswer(yPool, q, ans);

  if (ans === 'oui' && q.key.includes('_eq_')) yResolved.add(q.group);
  if (q.group === 'cardcat' && (ans === 'oui' || ans === 'non')) yResolved.add('cardcat');
  if (q.key === 'has_archetype') {
    if (ans === 'non' || ans === 'plutot_non') {
      yResolved.add('archetype');
      yResolved.add('has_archetype');
    } else {
      yResolved.add('has_archetype');
    }
  }

  const ansLabel = { oui:'OUI', non:'NON', plutot_oui:'~OUI', plutot_non:'~NON', ne_sais_pas:'?' };
  yHistory.push({ label: q.label, ans: ansLabel[ans] || ans, pool: yPool.length, snapshot: snap });
  renderHistory();
  updatePoolInfo();

  yThinking = true;
  setUI('thinking');
  setTimeout(() => nextStep(), 500);
}

// ── ANNULER LA DERNIÈRE RÉPONSE ───────────────────────────

function yugiUndo() {
  if (yThinking || yGameOver) return;
  if (yHistory.length === 0) return;

  const last = yHistory.pop();
  if (!last.snapshot) { renderHistory(); return; }

  restoreSnapshot(last.snapshot);
  renderHistory();
  updatePoolInfo();

  // Réaffiche la question annulée
  setUI('question');
  document.getElementById('yQnum').textContent = 'QUESTION ' + (yQCount + 1);
  document.getElementById('yQtext').textContent = last.label;
  updateProgress();
}

// ── PHASE DEVINETTE ───────────────────────────────────────

function enterGuessPhase() {
  if (yPool.length > GUESS_THRESHOLD) {
    const q = bestQuestion(yPool, yAsked, yResolved, yQCount);
    if (q) { yCurQ = q; showQuestion(q); return; }
  }

  ySortedPool = yPool.slice().sort((a, b) => {
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
  yConsecGuesses++;

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
    yPool       = yPool.filter(c => c.name !== name);
    ySortedPool = ySortedPool.filter(c => c.name !== name);

    yHistory.push({ label: 'Est-ce ' + name + ' ?', ans: 'NON', pool: yPool.length });
    renderHistory();
    updatePoolInfo();

    yThinking = true;
    setUI('thinking');
    setTimeout(() => {
      yThinking = false;
      // Si trop de devinettes consécutives → essaie une question avant la suivante
      if (yConsecGuesses >= MAX_CONSEC_GUESSES) {
        const q = bestQuestion(yPool, yAsked, yResolved, yQCount);
        if (q) {
          yConsecGuesses = 0;
          yCurQ = q;
          showQuestion(q);
          return;
        }
      }
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
    if (won && img) { rimg.src = img; rimg.style.display = 'block'; }
    else rimg.style.display = 'none';
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

  // Bouton Annuler visible dès qu'il y a un historique annulable (pas pour les devinettes)
  const canUndo = yHistory.length > 0 && yHistory[yHistory.length - 1].snapshot !== undefined;
  const undoBtn = canUndo
    ? `<button class="y-btn undo" onclick="yugiUndo()">↩ Annuler</button>`
    : '';

  if (mode === 'question') {
    ans.innerHTML = `
      <button class="y-btn yes"     onclick="yugiAnswer('oui')">✅ OUI</button>
      <button class="y-btn pyesbtn" onclick="yugiAnswer('plutot_oui')">🟡 PLUTÔT OUI</button>
      <button class="y-btn pnobtn"  onclick="yugiAnswer('plutot_non')">🟠 PLUTÔT NON</button>
      <button class="y-btn no"      onclick="yugiAnswer('non')">❌ NON</button>
      <button class="y-btn idk"     onclick="yugiAnswer('ne_sais_pas')">🤷 JE NE SAIS PAS</button>
      ${undoBtn}`;
  } else if (mode === 'guess') {
    ans.innerHTML = `
      <button class="y-btn yes" onclick="yugiConfirmGuess(true)">✅ OUI, C'EST ÇA !</button>
      <button class="y-btn no"  onclick="yugiConfirmGuess(false)">❌ NON, CE N'EST PAS ÇA</button>
      ${undoBtn}`;
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

// ── BOOTSTRAP ─────────────────────────────────────────────
// startGame() → yugiLoadCards() → yugiInit()
