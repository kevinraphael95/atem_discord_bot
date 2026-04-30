// ══════════════════════════════════════════════════════════
//  YUGINATOR — moteur probabiliste à la Akinator, zéro IA
//  Branché sur YGOPRODeck
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
    'Beast':'Bête','Beast-Warrior':'Bête-Guerrier','Winged Beast':'Bête Ailée','Fiend':'Démon',
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
  const map = { 'Banned':'Interdit','Forbidden':'Interdit','Limited':'Limité','Semi-Limited':'Semi-Limité' };
  return map[b] || 'Autorisé';
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

let ALL_CARDS  = [];
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
//  SYSTÈME DE SCORES PROBABILISTES
// ══════════════════════════════════════════════════════════

// Facteurs multiplicatifs selon la réponse
// oui        : cartes qui matchent ×1,    qui ne matchent pas ×FACTOR_NO
// plutot_oui : cartes qui matchent ×1,    qui ne matchent pas ×FACTOR_PNO
// plutot_non : cartes qui matchent ×FACTOR_PNO, qui ne matchent pas ×1
// non        : cartes qui matchent ×FACTOR_NO,  qui ne matchent pas ×1
// ne_sais_pas: aucun changement

const FACTOR_NO  = 0.05;  // quasi-certain que non
const FACTOR_PNO = 0.30;  // probablement non

// yScores : Map<cardId, number>  score entre 0 et 1 (initialisé à 1/N)
let yScores = new Map();

function initScores() {
  yScores = new Map();
  const init = 1 / ALL_CARDS.length;
  for (const c of ALL_CARDS) yScores.set(c.id, init);
}

function applyScores(q, ans) {
  if (ans === 'ne_sais_pas') return; // rien ne change

  let factorMatch, factorNoMatch;
  if      (ans === 'oui')        { factorMatch = 1;          factorNoMatch = FACTOR_NO;  }
  else if (ans === 'plutot_oui') { factorMatch = 1;          factorNoMatch = FACTOR_PNO; }
  else if (ans === 'plutot_non') { factorMatch = FACTOR_PNO; factorNoMatch = 1;          }
  else if (ans === 'non')        { factorMatch = FACTOR_NO;  factorNoMatch = 1;          }
  else return;

  // Applique les facteurs
  for (const c of ALL_CARDS) {
    const s = yScores.get(c.id) || 0;
    const matches = q.test(c);
    yScores.set(c.id, s * (matches ? factorMatch : factorNoMatch));
  }

  // Renormalise pour éviter l'underflow numérique
  normalizeScores();
}

function normalizeScores() {
  let total = 0;
  for (const v of yScores.values()) total += v;
  if (total === 0) return;
  for (const [id, v] of yScores) yScores.set(id, v / total);
}

// Retourne les cartes triées par score décroissant, filtrées au-dessus d'un seuil
function getActivePool(minScore = 1e-6) {
  return ALL_CARDS
    .filter(c => (yScores.get(c.id) || 0) >= minScore)
    .sort((a, b) => (yScores.get(b.id) || 0) - (yScores.get(a.id) || 0));
}

// Score de la carte la plus probable
function topScore() {
  let max = 0;
  for (const v of yScores.values()) if (v > max) max = v;
  return max;
}

// ══════════════════════════════════════════════════════════
//  GÉNÉRATEUR DE QUESTIONS
// ══════════════════════════════════════════════════════════

const ATK_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000, 3500];
const DEF_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000];
const LVL_THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12];

function poolContext(pool) {
  const total    = pool.length;
  if (!total) return 'mixed';
  const monsters = pool.filter(c => MONSTER_FRAMES.has(c.frameType)).length;
  const spells   = pool.filter(c => SPELL_FRAMES.has(c.frameType)).length;
  const traps    = pool.filter(c => TRAP_FRAMES.has(c.frameType)).length;
  if (monsters / total > 0.8) return 'monster';
  if (spells   / total > 0.8) return 'spell';
  if (traps    / total > 0.8) return 'trap';
  return 'mixed';
}

function raceLabel(v, ctx) {
  if (ctx === 'monster') return `Est-ce un monstre de type "${v}" ?`;
  if (ctx === 'spell')   return `Est-ce une Magie de sous-type "${v}" ?`;
  if (ctx === 'trap')    return `Est-ce un Piège de sous-type "${v}" ?`;
  if (SPELL_RACES.has(v)) return `Est-ce une Magie/Piège de sous-type "${v}" ?`;
  return `Est-ce un monstre de type "${v}" ?`;
}

function buildQuestions(pool) {
  const qs  = [];
  const ctx = poolContext(pool);

  const frames    = [...new Set(pool.map(c => c.frameType))].filter(v => v && v !== '—');
  const attrs     = [...new Set(pool.map(c => c.attribute))].filter(v => v && v !== '—');
  const races     = [...new Set(pool.map(c => c.race))].filter(v => v && v !== '—');
  const bans      = [...new Set(pool.map(c => c.ban))];
  const archetypes = [...new Set(pool.map(c => c.archetype))].filter(v => v && v !== '—');
  const hasArchN  = pool.filter(c => c.archetype !== '—').length;
  const noArchN   = pool.length - hasArchN;

  // ── Catégorie monstre / magie / piège
  const nM = pool.filter(c => MONSTER_FRAMES.has(c.frameType)).length;
  const nS = pool.filter(c => SPELL_FRAMES.has(c.frameType)).length;
  const nT = pool.filter(c => TRAP_FRAMES.has(c.frameType)).length;
  if (nM > 0 && (nS > 0 || nT > 0))
    qs.push({ label: "Est-ce un monstre ?",      key: 'cat_monster', test: c => MONSTER_FRAMES.has(c.frameType), group: 'cardcat' });
  if (nS > 0 && (nM > 0 || nT > 0))
    qs.push({ label: "Est-ce une carte Magie ?", key: 'cat_spell',   test: c => SPELL_FRAMES.has(c.frameType),   group: 'cardcat' });
  if (nT > 0 && (nM > 0 || nS > 0))
    qs.push({ label: "Est-ce une carte Piège ?", key: 'cat_trap',    test: c => TRAP_FRAMES.has(c.frameType),    group: 'cardcat' });

  // ── FrameType détaillé
  frames.forEach(v => qs.push({
    label: `Est-ce une carte "${v}" ?`,
    key: 'frameType_eq_' + v, test: c => c.frameType === v, group: 'frameType',
  }));

  // ── Attribut
  attrs.forEach(v => qs.push({
    label: `L'attribut est-il "${v}" ?`,
    key: 'attr_eq_' + v, test: c => c.attribute === v, group: 'attribute',
  }));

  // ── Race / sous-type
  races.forEach(v => qs.push({
    label: raceLabel(v, ctx),
    key: 'race_eq_' + v, test: c => c.race === v, group: 'race',
  }));

  // ── Archétype
  if (hasArchN > 0 && noArchN > 0)
    qs.push({ label: "Appartient-elle à un archétype ?", key: 'has_archetype', test: c => c.archetype !== '—', group: 'has_archetype' });

  if (archetypes.length > 0) {
    const archInRange = (c, a, z) => c.archetype !== '—' && (c.archetype[0]||'').toUpperCase() >= a && (c.archetype[0]||'').toUpperCase() <= z;
    qs.push({ label: "L'archétype commence-t-il par A–M ?", key: 'arch_AM', test: c => archInRange(c,'A','M'), group: 'arch_alpha' });
    qs.push({ label: "L'archétype commence-t-il par N–Z ?", key: 'arch_NZ', test: c => archInRange(c,'N','Z'), group: 'arch_alpha' });
    qs.push({ label: "L'archétype commence-t-il par A–F ?", key: 'arch_AF', test: c => archInRange(c,'A','F'), group: 'arch_alpha2' });
    qs.push({ label: "L'archétype commence-t-il par G–M ?", key: 'arch_GM', test: c => archInRange(c,'G','M'), group: 'arch_alpha2' });
    qs.push({ label: "L'archétype commence-t-il par N–S ?", key: 'arch_NS', test: c => archInRange(c,'N','S'), group: 'arch_alpha2' });
    qs.push({ label: "L'archétype commence-t-il par T–Z ?", key: 'arch_TZ', test: c => archInRange(c,'T','Z'), group: 'arch_alpha2' });

    if (pool.length <= 300) {
      'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach(l => qs.push({
        label: `L'archétype commence-t-il par "${l}" ?`,
        key: 'arch_letter_' + l,
        test: c => c.archetype !== '—' && (c.archetype[0]||'').toUpperCase() === l,
        group: 'arch_letter',
      }));
    }
    if (archetypes.length <= 20) {
      archetypes.forEach(v => qs.push({
        label: `Est-ce une carte de l'archétype "${v}" ?`,
        key: 'arch_eq_' + v, test: c => c.archetype === v, group: 'archetype',
      }));
    }
  }

  // ── Banlist
  if (bans.length > 1) {
    bans.forEach(v => qs.push({
      label: `Est-elle "${v}" sur la Banlist TCG ?`,
      key: 'ban_eq_' + v, test: c => c.ban === v, group: 'ban',
    }));
  }

  // ── Stats numériques
  const hasAtk = pool.some(c => c.atk >= 0);
  const hasDef = pool.some(c => c.def >= 0);
  const hasLvl = pool.some(c => c.level > 0);

  if (hasAtk) ATK_THRESHOLDS.forEach(t => qs.push({
    label: `L'ATK est-elle ≥ ${t} ?`,
    key: 'atk_gte_' + t, test: c => c.atk >= 0 && c.atk >= t, group: 'atk',
  }));
  if (hasDef) DEF_THRESHOLDS.forEach(t => qs.push({
    label: `La DEF est-elle ≥ ${t} ?`,
    key: 'def_gte_' + t, test: c => c.def >= 0 && c.def >= t, group: 'def',
  }));
  if (hasLvl) LVL_THRESHOLDS.forEach(t => qs.push({
    label: `Le Niveau / Rang est-il ≥ ${t} ?`,
    key: 'lvl_gte_' + t, test: c => c.level >= t, group: 'level',
  }));

  if (hasLvl && pool.length <= 400) {
    [1,2,3,4,5,6,7,8,10,12].forEach(n => qs.push({
      label: `Le Niveau / Rang est-il exactement ${n} ?`,
      key: 'lvl_eq_' + n, test: c => c.level === n, group: 'level_exact',
    }));
  }
  if (hasAtk && pool.length <= 120) {
    [...new Set(pool.map(c => c.atk).filter(v => v >= 0))].forEach(v => qs.push({
      label: `L'ATK est-elle exactement ${v} ?`,
      key: 'atk_eq_' + v, test: c => c.atk === v, group: 'atk_exact',
    }));
  }
  if (pool.some(c => c.atk >= 0 && c.def >= 0)) {
    qs.push({ label: "L'ATK est-elle supérieure à la DEF ?", key: 'atk_gt_def', test: c => c.atk >= 0 && c.def >= 0 && c.atk > c.def, group: 'atk_vs_def' });
  }

  // ── Questions sur le nom
  const NAME_THRESH = 1500;
  if (pool.length <= NAME_THRESH) {
    const inRange = (c, a, z) => { const l = (c.name[0]||'').toUpperCase(); return l >= a && l <= z; };
    qs.push({ label: "Le nom commence-t-il par A–M ?", key: 'name_AM', test: c => inRange(c,'A','M'), group: 'name_alpha' });
    qs.push({ label: "Le nom commence-t-il par N–Z ?", key: 'name_NZ', test: c => inRange(c,'N','Z'), group: 'name_alpha' });
    qs.push({ label: "Le nom commence-t-il par A–F ?", key: 'name_AF', test: c => inRange(c,'A','F'), group: 'name_alpha2' });
    qs.push({ label: "Le nom commence-t-il par G–M ?", key: 'name_GM', test: c => inRange(c,'G','M'), group: 'name_alpha2' });
    qs.push({ label: "Le nom commence-t-il par N–S ?", key: 'name_NS', test: c => inRange(c,'N','S'), group: 'name_alpha2' });
    qs.push({ label: "Le nom commence-t-il par T–Z ?", key: 'name_TZ', test: c => inRange(c,'T','Z'), group: 'name_alpha2' });

    if (pool.length <= 200) {
      'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach(l => qs.push({
        label: `Le nom commence-t-il par "${l}" ?`,
        key: 'name_letter_' + l, test: c => (c.name[0]||'').toUpperCase() === l, group: 'name_letter',
      }));
    }

    [1,2,3,4,5].forEach(t => qs.push({
      label: `Le nom contient-il plus de ${t} mot${t>1?'s':''} ?`,
      key: 'name_words_' + t, test: c => c.name.trim().split(/\s+/).length > t, group: 'name_words',
    }));
  }

  // ── Mots fréquents dans les noms
  if (pool.length > 6 && pool.length <= NAME_THRESH) {
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
        key: 'name_word_' + w, test: c => c.name.toLowerCase().includes(w), group: 'name_word',
      }));
  }

  return qs;
}

// ── SÉLECTION DE LA MEILLEURE QUESTION ────────────────────
// Entropie de Shannon sur les scores, pas juste ratio 50/50

function bestQuestion(pool, askedKeys, resolvedGroups) {
  const qs = buildQuestions(pool).filter(q =>
    !askedKeys.has(q.key) && !resolvedGroups.has(q.group)
  );
  if (qs.length === 0) return null;

  // Score = réduction d'entropie attendue (pondéré par les scores des cartes)
  const scoreQ = q => {
    let pYes = 0, pNo = 0;
    for (const c of pool) {
      const s = yScores.get(c.id) || 0;
      if (q.test(c)) pYes += s; else pNo += s;
    }
    const total = pYes + pNo;
    if (total === 0 || pYes === 0 || pNo === 0) return -1;
    // Entropie binaire de Shannon
    const pY = pYes / total, pN = pNo / total;
    const entropy = -(pY * Math.log2(pY) + pN * Math.log2(pN)); // max = 1 quand pY=pN=0.5
    // Bruit aléatoire pour varier les parties (±8%)
    return entropy + (Math.random() * 0.16 - 0.08);
  };

  // Groupes de priorité — groupes au même niveau sont mélangés aléatoirement entre eux
  const PRIORITY_TIERS = [
    ['cardcat'],
    ['frameType', 'attribute', 'race'],
    ['has_archetype'],
    ['arch_alpha', 'arch_alpha2', 'arch_letter', 'archetype'],
    ['atk_vs_def', 'name_alpha', 'name_alpha2'],
    ['name_letter', 'name_words', 'name_word'],
    ['atk', 'def', 'level'],
    ['level_exact', 'atk_exact', 'ban'],
  ];

  const MIN_ENTROPY = 0.08; // question doit apporter un minimum d'info

  for (const tier of PRIORITY_TIERS) {
    // Mélange les groupes dans ce tier pour varier l'ordre
    const shuffledTier = tier.slice().sort(() => Math.random() - 0.5);
    let best = null, bestScore = -1;
    for (const grp of shuffledTier) {
      if (resolvedGroups.has(grp)) continue;
      const candidates = qs.filter(q => q.group === grp);
      for (const q of candidates) {
        const s = scoreQ(q);
        if (s >= MIN_ENTROPY && s > bestScore) { bestScore = s; best = q; }
      }
    }
    if (best) return best;
  }

  // Fallback : n'importe quelle question disponible avec le meilleur score
  let best = null, bestScore = -1;
  for (const q of qs) {
    const s = scoreQ(q);
    if (s > bestScore) { bestScore = s; best = q; }
  }
  return best;
}

// ══════════════════════════════════════════════════════════
//  ÉTAT DU JEU
// ══════════════════════════════════════════════════════════

let yPool           = []; // cartes encore "actives" (score > seuil)
let yAsked          = new Set();
let yResolved       = new Set();
let yHistory        = [];
let yHistory_states = [];
let yGameOver       = false;
let yCurQ           = null;
let yThinking       = false;
let yQCount         = 0;

// Seuil de score pour qu'une carte soit "active"
const SCORE_THRESHOLD     = 1e-6;
// Seuil de confiance pour proposer une devinette directement
const GUESS_CONFIDENCE    = 0.60;
// Nombre max de cartes actives pour passer en mode devinette forcée
const GUESS_POOL_MAX      = 4;

// ── INIT ──────────────────────────────────────────────────

function yugiInit() {
  yAsked          = new Set();
  yResolved       = new Set();
  yHistory        = [];
  yHistory_states = [];
  yGameOver       = false;
  yCurQ           = null;
  yThinking       = false;
  yQCount         = 0;

  initScores();
  yPool = getActivePool(SCORE_THRESHOLD);

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

  yPool = getActivePool(SCORE_THRESHOLD);

  if (yPool.length === 0) { showGiveUp(); return; }

  // Si une carte domine largement → proposer directement
  const top = topScore();
  if (top >= GUESS_CONFIDENCE || yPool.length <= GUESS_POOL_MAX) {
    showGuessStep();
    return;
  }

  const q = bestQuestion(yPool, yAsked, yResolved);
  if (!q) { showGuessStep(); return; }

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
  const top = topScore();
  const pct = Math.round(Math.min(99, top * 100));
  document.getElementById('yConf').textContent = pct + '%';
  document.getElementById('yProgFill').style.width = Math.max(2, pct) + '%';
}

// ── RETOUR ARRIÈRE ────────────────────────────────────────

function yugiUndo() {
  if (yHistory_states.length === 0 || yGameOver) return;
  const snap       = yHistory_states.pop();
  yScores          = snap.scores;
  yAsked           = snap.asked;
  yResolved        = snap.resolved;
  yHistory         = snap.history;
  yQCount          = snap.qCount;
  yCurQ            = snap.curQ;
  yPool            = getActivePool(SCORE_THRESHOLD);
  yThinking        = false;

  renderHistory();
  updatePoolInfo();
  showQuestion(yCurQ);
}

// ── RÉPONSE UTILISATEUR ───────────────────────────────────

function yugiAnswer(ans) {
  if (yThinking || yGameOver || !yCurQ) return;
  const q = yCurQ;

  // Snapshot pour undo
  yHistory_states.push({
    scores:   new Map(yScores),
    asked:    new Set(yAsked),
    resolved: new Set(yResolved),
    history:  yHistory.slice(),
    qCount:   yQCount,
    curQ:     yCurQ,
  });

  yAsked.add(q.key);
  yQCount++;

  // Mise à jour des scores probabilistes
  applyScores(q, ans);

  // Marquer groupes résolus (réponse franche)
  if (ans === 'oui') {
    if (q.key.includes('_eq_')) yResolved.add(q.group);
    if (q.group === 'cardcat')  yResolved.add('cardcat');
    if (q.key === 'has_archetype') yResolved.add('has_archetype');
  }
  if (ans === 'non') {
    if (q.group === 'cardcat') yResolved.add('cardcat');
    if (q.key === 'has_archetype') { yResolved.add('has_archetype'); yResolved.add('archetype'); }
  }

  yPool = getActivePool(SCORE_THRESHOLD);

  const ansLabel = { oui:'OUI', non:'NON', plutot_oui:'~OUI', plutot_non:'~NON', ne_sais_pas:'?' };
  yHistory.push({ label: q.label, ans: ansLabel[ans] || ans, pool: yPool.length });
  renderHistory();
  updatePoolInfo();

  yThinking = true;
  setUI('thinking');
  setTimeout(() => nextStep(), 500);
}

// ── PHASE DEVINETTE ───────────────────────────────────────
// Propose toujours la carte avec le meilleur score

function showGuessStep() {
  yPool = getActivePool(SCORE_THRESHOLD);
  if (yPool.length === 0) { showGiveUp(); return; }

  // La carte en tête de pool (meilleur score)
  const card = yPool[0];
  const pct  = Math.round(Math.min(99, (yScores.get(card.id) || 0) * 100));

  setUI('guess');
  document.getElementById('yQnum').textContent = '🎯 MA PROPOSITION';
  document.getElementById('yQtext').textContent = 'Est-ce que vous pensez à… ' + card.name + ' ?';
  document.getElementById('yConf').textContent = pct + '%';
  document.getElementById('yProgFill').style.width = Math.max(2, pct) + '%';

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
    return;
  }

  // Mauvaise proposition → score de cette carte à zéro
  const card = ALL_CARDS.find(c => c.name === name);
  if (card) {
    yScores.set(card.id, 0);
    normalizeScores();
  }

  yPool = getActivePool(SCORE_THRESHOLD);
  yHistory.push({ label: 'Est-ce ' + name + ' ?', ans: 'NON', pool: yPool.length });
  renderHistory();
  updatePoolInfo();

  yThinking = true;
  setUI('thinking');
  setTimeout(() => nextStep(), 400);
}

function showGiveUp() {
  // Sécurité : si des cartes restent, on continue à deviner
  yPool = getActivePool(SCORE_THRESHOLD);
  if (yPool.length > 0) { showGuessStep(); return; }

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
    else              { rimg.style.display = 'none'; }
  }

  const remaining = getActivePool(SCORE_THRESHOLD);
  document.getElementById('yRdesc').textContent = won
    ? 'Le Yuginator a percé le voile en ' + yQCount + ' réponse' + (yQCount > 1 ? 's' : '') + ' sur ' + ALL_CARDS.length.toLocaleString('fr') + ' cartes.'
    : 'Votre carte a résisté à l\'analyse. ' + remaining.length + ' candidate' + (remaining.length > 1 ? 's' : '') + ' restai' + (remaining.length > 1 ? 'ent' : 't') + '. Quelle était-elle ?';

  if (!won && remaining.length > 0 && remaining.length <= 20) {
    // Retire les anciens éléments extra
    const old = document.getElementById('yResult').querySelector('.y-extra');
    if (old) old.remove();
    const extra = document.createElement('div');
    extra.className = 'y-extra';
    extra.style.cssText = 'font-family:"DM Sans",sans-serif;font-size:.78rem;color:var(--dim);margin-top:.5rem;font-style:italic;';
    extra.textContent = 'Candidats restants : ' + remaining.slice(0,8).map(c => c.name).join(', ') + (remaining.length > 8 ? '…' : '');
    document.getElementById('yResult').appendChild(extra);
  }

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

  if (yHistory_states.length > 0 && mode !== 'guess') {
    const undoBtn = document.createElement('button');
    undoBtn.className = 'y-btn undo';
    undoBtn.textContent = '↩ RETOUR';
    undoBtn.title = 'Annuler la dernière réponse';
    undoBtn.onclick = yugiUndo;
    ans.appendChild(undoBtn);
  }
}

function updatePoolInfo() {
  const el = document.getElementById('yPoolInfo');
  if (!el) return;
  const n = getActivePool(SCORE_THRESHOLD).length;
  el.textContent = n.toLocaleString('fr') + ' carte' + (n > 1 ? 's' : '') + ' candidate' + (n > 1 ? 's' : '');
}

function renderHistory() {
  const list = document.getElementById('yHist');
  if (!list) return;
  list.innerHTML = '';
  yHistory.forEach(h => {
    const item = document.createElement('div');
    item.className = 'y-hi';
    const clsMap = { 'OUI':'yes','NON':'no','~OUI':'pyesbtn','~NON':'pnobtn','?':'idk' };
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
  list.scrollTop = list.scrollHeight;
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
