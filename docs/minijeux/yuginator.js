// ══════════════════════════════════════════════════════════
//  YUGINATOR v2 — moteur entropique pur JS, zéro IA
//  Branché sur YGOPRODeck API v7 (misc=yes)
// ══════════════════════════════════════════════════════════

// ── SETS DE CLASSIFICATION ────────────────────────────────

const MONSTER_FRAMES = new Set(['Normal','Effet','Rituel','Fusion','Synchro','XYZ','Link','Pendule','Jeton','Skill']);
const SPELL_FRAMES   = new Set(['Magie']);
const TRAP_FRAMES    = new Set(['Piège']);
const EXTRA_DECK     = new Set(['Fusion','Synchro','XYZ','Link']);
const MAIN_DECK      = new Set(['Normal','Effet','Rituel','Pendule']);
const SPELL_RACES    = new Set(['Normal','Continu','Contre','Jeu rapide','Équipement','Terrain','Rituel']);

// ── VARIATION DES QUESTIONS ────────────────────────────────
const Q_VARIANTS = {
  cat_monster: [
    "Est-ce un monstre ?",
    "S'agit-il d'une carte Monstre ?",
    "La carte à laquelle vous pensez est-elle un Monstre ?",
    "Avez-vous en tête une carte Monstre ?",
    "Pensez-vous à une carte Monstre ?",
    "La carte est-elle un Monstre ?",
    "Avez-vous choisi un Monstre ?",
  ],
  cat_spell: [
    "Est-ce une carte Magie ?",
    "S'agit-il d'une carte Magie ?",
    "La carte à laquelle vous pensez est-elle un Magie ?",
    "Avez-vous en tête une carte Magie ?",
    "Pensez-vous à une carte Magie ?",
    "La carte est-elle une Magie ?",
    "Avez-vous choisi une Magie ?",
  ],
  cat_trap: [
    "Est-ce une carte Piège ?",
    "S'agit-il d'une carte Piège ?",
    "La carte à laquelle vous pensez est-elle un Piège ?",
    "Avez-vous en tête une carte Piège ?",
    "Pensez-vous à une carte Piège ?",
    "La carte est-elle un Piège ?",
    "Avez-vous choisi un Piège ?",
  ],
  cat_extra: [
    "Est-ce un monstre de l'Extra Deck (Fusion, Synchro, Xyz ou Link) ?",
    "Votre monstre provient-il de l'Extra Deck ?",
    "S'agit-il d'un Fusion, Synchro, Xyz ou Link ?",
  ],
  has_archetype: [
    "Est-ce que la carte appartient à un archétype ?",
    "La carte fait-elle partie d'un archétype précis ?",
    "Y a-t-il un archétype associé à cette carte ?",
  ],
  has_effect_1: [
    "Est-ce que la carte possède un vrai effet de jeu ?",
    "Cette carte a-t-elle un effet actif (pas juste un texte de lore) ?",
    "La carte a-t-elle un effet mécanique en jeu ?",
  ],
  frame_normal: [
    "Est-ce un monstre Normal (cadre jaune, sans effet) ?",
    "S'agit-il d'un monstre Normal sans effet ?",
    "La carte est-elle un Normal Monster (fond jaune) ?",
  ],
};


function pickVariant(key, defaultLabel) {
  const variants = Q_VARIANTS[key];
  if (!variants) return defaultLabel;
  return variants[Math.floor(Math.random() * variants.length)];
}

// ── NORMALISATION ─────────────────────────────────────────

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
  const map = {
    'Banned':'Interdit','Forbidden':'Interdit',
    'Limited':'Limité','Semi-Limited':'Semi-Limité',
  };
  return map[b] || 'Autorisé';
}

function normEpoch(tcgDate) {
  if (!tcgDate) return '—';
  const year = parseInt(tcgDate.slice(0, 4), 10);
  if (isNaN(year)) return '—';
  const start = Math.floor((year - 2002) / 5) * 5 + 2002;
  return `${start}-${start + 4}`;
}

function normYear(tcgDate) {
  if (!tcgDate) return null;
  const y = parseInt(tcgDate.slice(0, 4), 10);
  return isNaN(y) ? null : y;
}

function normPriceTier(prices) {
  if (!prices || !prices[0]) return '—';
  const p = parseFloat(prices[0].cardmarket_price);
  if (isNaN(p) || p <= 0) return 'Gratuit/commun';
  if (p < 0.5)  return 'Très commun (<0,50€)';
  if (p < 2)    return 'Commun (0,50–2€)';
  if (p < 10)   return 'Peu cher (2–10€)';
  if (p < 30)   return 'Modéré (10–30€)';
  if (p < 100)  return 'Cher (30–100€)';
  return 'Très cher (>100€)';
}

function normFormats(misc) {
  if (!misc || !misc[0] || !misc[0].formats) return new Set();
  return new Set(misc[0].formats.map(f => f.toLowerCase()));
}

const LINK_MARKER_FR = {
  'Top':          'Haut',
  'Bottom':       'Bas',
  'Left':         'Gauche',
  'Right':        'Droite',
  'Top-Left':     'Haut-Gauche',
  'Top-Right':    'Haut-Droite',
  'Bottom-Left':  'Bas-Gauche',
  'Bottom-Right': 'Bas-Droite',
};
function normLinkMarkers(raw) {
  if (!raw || !raw.linkmarkers) return [];
  return raw.linkmarkers.map(m => LINK_MARKER_FR[m] || m);
}

// ══════════════════════════════════════════════════════════
//  ARCHÉTYPES EN→FR
// ══════════════════════════════════════════════════════════

const ARCHETYPE_FR = {
  'Abyss Actor':'Acteur des Abîmes','Adamancipator':'Adamancipateur','Aesir':'Ases',
  'Alien':'Alien','Altergeist':'Altergiste','Amazoness':'Amazonesse','Amorphage':'Amorphage',
  'Ancient Gear':'Rouages Ancients','Ancient Warriors':'Guerriers Antiques','Archfiend':'Archdémon',
  'Aroma':'Arôme','Artifact':'Artéfact','Assault Mode':'Mode Assaut','Atlantean':'Atlante',
  'B.E.S.':'B.E.S.','Baby Dragon':'Bébé Dragon','Barrier Statue':'Statue Barrière',
  'Battlin\' Boxer':'Boxeur de Combat','Black Luster Soldier':'Soldat du Lustre Noir',
  'Blackwing':'Aile Noire','Blue-Eyes':'Yeux Bleus','Brotherhood of the Fire Fist':'Fraternité du Poing de Feu',
  'Burning Abyss':'Abîme Ardent','Buster Blader':'Buster Blader','Celtic Guard':'Celt',
  'Chronomaly':'Chronomalie','Code Talker':'Codeur','Constellar':'Constellaire',
  'Crystal Beast':'Bête de Cristal','Crystron':'Cryston','Cubic':'Cubique',
  'Cyber':'Cyber','Cyber Angel':'Ange Cyber','Cyber Dragon':'Cyber Dragon',
  'Cyberdark':'Cybersombre','Cybernetic':'Cybernétique','Cyberse':'Cyberse',
  'D.D.':'D.D.','D/D':'D/D','D/D/D':'D/D/D','Dark Magician':'Magicien Sombre',
  'Dark World':'Monde Ténébreux','Darklord':'Ange Déchu','Destiny HERO':'HÉROS du Destin',
  'Dinomist':'Dinomiste','Dinomorphia':'Dinomorphia','Dogmatika':'Dogmatika',
  'Dragunity':'Dragunité','Dragonmaid':'Servante Dragon','Dragon Ruler':'Seigneur Dragon',
  'Drytron':'Drytron','Earthbound':'Esprit de la Terre','Eldlich':'Eldlich',
  'Elemental HERO':'HÉROS Élémentaire','Endymion':'Endymion','Evilswarm':'Verminpeste',
  'Evil HERO':'HÉROS du Mal','Evil Eye':'Mauvais Œil','Evolsaur':'Évolosaure',
  'Exodia':'Éxodia','Exosister':'Exosœur','F.A.':'F.A.','Fabled':'Légendaire',
  'Fallen of Albaz':'Chute d\'Albaz','Floowandereeze':'Floowandereeze','Fluffal':'Peluche',
  'Fortune Lady':'Dame Fortune','Frog':'Grenouille','Fur Hire':'En Service',
  'Gagaga':'Gagaga','Galaxy':'Galaxie','Galaxy-Eyes':'Yeux Galaxie',
  'Gate Guardian':'Gardien de la Porte','Gem-Knight':'Chevalier Gemme','Generaider':'Généraider',
  'Ghostrick':'Fantôruse','Gimmick Puppet':'Marionnette Gadget','Gishki':'Gishki',
  'Goblin':'Gobelin','Gouki':'Gouki','Gravekeeper\'s':'Protecteurs du Tombeau',
  'Guardian':'Gardien','Gusto':'Gusto','HERO':'HÉROS','Harpie':'Harpie',
  'Hieratic':'Hiératique','Hi-Speedroid':'Hi-Speedroïd','Horus':'Horus',
  'Ice Barrier':'Barrière de Glace','Icejade':'Jade de Glace','Ignister':'Ignister',
  'Impcantation':'Diablocantatoire','Infernity':'Infernité','Infernoid':'Inferno',
  'Invoked':'Invoqué','Inzektor':'Inzecteur','Jinzo':'Jinzo','Junk':'Ferraille',
  'Kaiju':'Kaiju','Kashtira':'Kashtira','Knightmare':'Cauchemar du Chevalier',
  'Krawler':'Rampant','Kuriboh':'Kuriboh','Labrynth':'Labyrinthe','Laval':'Laval',
  'Lightsworn':'Seigneur Lumière','Lunalight':'Clair de Lune','Lyrilusc':'Lyrilusque',
  'Machina':'Machin','Madolche':'Madolché','Magician':'Magicien','Majespecter':'Majespecteur',
  'Malefic':'Corrompu','Marincess':'Marinesse','Mathmech':'Mathméca','Megalith':'Mégalithe',
  'Melffy':'Peluchimal','Melodious':'Mélodieux','Memento':'Mémento','Mermail':'Aquamer',
  'Metalfoes':'Métalfeu','Millennium':'Millénaire','Mist Valley':'Vallée de Brume',
  'Monarch':'Monarque','Myutant':'Myutant','Naturia':'Naturie','Nekroz':'Nékroz',
  'Neo-Spacian':'Néo-Spatial','Neos':'Néos','Nephthys':'Nephtys',
  'Noble Knight':'Noble Chevalier','Number':'Numéro','Numeron':'Numéron',
  'Ojama':'Ojama','Orcust':'Orcuste','P.U.N.K.':'P.U.N.K.','Paleozoic':'Paléozoïque',
  'Pendulum':'Pendule','Penguin':'Pingouin','Performapal':'Saltimbanque',
  'Performage':'Performeur','Phantom Beast':'Bête Fantôme',
  'Phantom Knights':'Chevaliers Fantômes','Photon':'Photon',
  'Plunder Patroll':'Patrouille de Pillards','Predaplant':'Prédaplante',
  'Prank-Kids':'Bambins Facétieux','Prophecy':'Prophétie','Purrely':'Purrely',
  'Raidraptor':'Raidraptor','Red Dragon Archfiend':'Dragon Rouge Archdémon',
  'Red-Eyes':'Yeux Rouges','Relinquished':'Le Renoncé','Rikka':'Rikka',
  'Ritual Beast':'Bête Rituelle','Rokket':'Rokket','Rose Dragon':'Dragon Rose',
  'S-Force':'Force-S','Salamangreat':'Salamangreat','Satellarknight':'Satellachevalier',
  'Scareclaw':'Griffempouvantail','Shaddoll':'Ombre-Poupée',
  'Silent Magician':'Magicien Silencieux','Silent Swordsman':'Spadassin Silencieux',
  'Six Samurai':'Six Samouraïs','Sky Striker':'Assaut de l\'Air',
  'Skull Servant':'Serviteur Crâne','SPYRAL':'ESPION-AL','Speedroid':'Speedroïd',
  'Spellbook':'Livre de Magie','Spright':'Lutin','Springans':'Springans',
  'Stardust':'Poussière d\'Étoiles','Subterror':'Souterrain',
  'Superheavy Samurai':'Samouraï Superpesant','Supreme King':'Roi Suprême',
  'Swordsoul':'Âme-Épée','Synchron':'Synchron','T.G.':'T.G.',
  'Tellarknight':'Tellarchevalier','Tenyi':'Tenyi','The Agent':'Agent',
  'The Weather':'Le Temps','Thunder Dragon':'Dragon du Tonnerre','Tindangle':'Tindangle','Trap Hole':'Trappe',
  'Toon':'Toon','Tri-Brigade':'Tri-Brigade','Troymare':'Cauchemar Troyen',
  'True Draco':'Vrai Draco','True King':'Vrai Roi','Twilightsworn':'Porteur du Crépuscule',
  'U.A.':'U.A.','Unchained':'Déchaîné','Utopia':'Utopie','V-HERO':'V-HÉROS',
  'Vampire':'Vampire','Vehicroid':'Véhicroid','Vendread':'Vendread','Venom':'Venin',
  'Virtual World':'Monde Virtuel','Vision HERO':'Vision HÉROS','Vylon':'Vylon',
  'Watt':'Électro-','Winged Kuriboh':'Kuriboh Ailé','Witchcrafter':'Artisane des Sorcières',
  'Wind-Up':'Remontoir','World Chalice':'Calice du Monde','World Legacy':'Héritage du Monde',
  'X-Saber':'X-Sabre','Xtra HERO':'Xtra HÉROS','Yang Zing':'Yang Zing',
  'Yosenju':'Yosenju','Yubel':'Yubel','Zefra':'Zefra','Zombie':'Zombi',
  'Zombie World':'Monde Zombi','Zoodiac':'Zodiarque',
};

function normArchetype(a) {
  if (!a) return '—';
  return ARCHETYPE_FR[a] ?? a;
}

function normalize(raw) {
  const misc    = raw.misc || [];
  const miscObj = misc[0] || {};
  const formats = normFormats(misc);

  return {
    id:          raw.id,
    name:        raw.name,
    frameType:   normFrame(raw.frameType),
    race:        normRace(raw.race),
    attribute:   normAttr(raw.attribute),
    level:       raw.level ?? 0,
    linkval:     raw.linkval ?? 0,
    atk:         raw.atk ?? -1,
    def:         raw.def ?? -1,
    archetype:   normArchetype(raw.archetype),
    ban:         normBan(raw.banlist_info),
    img:         raw.card_images?.[0]?.image_url_small || '',
    scale:       raw.scale ?? -1,
    linkmarkers: normLinkMarkers(raw),
    hasEffect:   miscObj.has_effect ?? -1,
    tcgYear:     normYear(miscObj.tcg_date),
    epoch:       normEpoch(miscObj.tcg_date),
    formats,
    mdRarity:    miscObj.md_rarity || '—',
    views:       miscObj.views ?? 0,
    priceTier:   normPriceTier(raw.card_prices),
    priceRaw:    raw.card_prices?.[0] ? parseFloat(raw.card_prices[0].cardmarket_price) || 0 : 0,
    nbArtworks:  raw.card_images ? raw.card_images.length : 1,
  };
}

// ══════════════════════════════════════════════════════════
//  CHARGEMENT
// ══════════════════════════════════════════════════════════

let ALL_CARDS  = [];
let yugiLoaded = false;

// ── BLOC 3 : variables globales intervalles ───────────────
let NAME_INTERVALS  = [];
let NAME2_INTERVALS = [];
let ARCH_INTERVALS  = [];

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
//  GÉNÉRATEUR D'INTERVALLES ALÉATOIRES (BLOC 3)
// ══════════════════════════════════════════════════════════

function randomIntervals() {
  const intervals = [];
  let i = 0;
  while (i < 26) {
    const size = 7 + Math.floor(Math.random() * 4);
    const end = Math.min(i + size - 1, 25);
    intervals.push({ a: String.fromCharCode(65+i), z: String.fromCharCode(65+end) });
    i = end + 1;
  }
  return intervals;
}

// ══════════════════════════════════════════════════════════
//  GÉNÉRATEUR DE QUESTIONS
// ══════════════════════════════════════════════════════════

const ATK_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000, 3500];
const DEF_THRESHOLDS = [500, 1000, 1500, 2000, 2500, 3000];
const LVL_THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12];
const YEAR_CUTS      = [2004, 2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024];

function poolContext(pool) {
  const total    = pool.length;
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
  if (ctx === 'spell')   return `Est-ce une carte Magie de type "${v}" ?`;
  if (ctx === 'trap')    return `Est-ce une carte Piège de type "${v}" ?`;
  if (SPELL_RACES.has(v)) return `Est-ce une carte Magie/Piège de sous-type "${v}" ?`;
  return `Est-ce un monstre de type "${v}" ?`;
}

function buildQuestions(pool) {
  const qs  = [];
  const ctx = poolContext(pool);

  const attrs      = [...new Set(pool.map(c => c.attribute))].filter(v => v && v !== '—');
  const races      = [...new Set(pool.map(c => c.race))].filter(v => v && v !== '—');
  const bans       = [...new Set(pool.map(c => c.ban))];
  const archetypes = [...new Set(pool.map(c => c.archetype))].filter(v => v && v !== '—');

  const hasArchPool = pool.filter(c => c.archetype !== '—').length;
  const noArchPool  = pool.length - hasArchPool;

  // ── 1. Catégorie Monstre / Magie / Piège ─────────────
  const nMonsters = pool.filter(c => MONSTER_FRAMES.has(c.frameType)).length;
  const nSpells   = pool.filter(c => SPELL_FRAMES.has(c.frameType)).length;
  const nTraps    = pool.filter(c => TRAP_FRAMES.has(c.frameType)).length;
  if (nMonsters > 0 && (nSpells > 0 || nTraps > 0))
    qs.push({ label: pickVariant('cat_monster', 'Est-ce un monstre ?'), key:'cat_monster', test:c=>MONSTER_FRAMES.has(c.frameType), group:'cardcat' });
  if (nSpells > 0 && (nMonsters > 0 || nTraps > 0))
    qs.push({ label: pickVariant('cat_spell', 'Est-ce une carte Magie ?'), key:'cat_spell', test:c=>SPELL_FRAMES.has(c.frameType), group:'cardcat' });
  if (nTraps > 0 && (nMonsters > 0 || nSpells > 0))
    qs.push({ label: pickVariant('cat_trap', 'Est-ce une carte Piège ?'), key:'cat_trap', test:c=>TRAP_FRAMES.has(c.frameType), group:'cardcat' });

  // ── 2. Extra Deck vs Main Deck ───────────────────────
  const nExtra = pool.filter(c => EXTRA_DECK.has(c.frameType)).length;
  const nMain  = pool.filter(c => MAIN_DECK.has(c.frameType)).length;
  if (nExtra > 0 && nMain > 0)
    qs.push({ label: pickVariant('cat_extra', "Est-ce un monstre de l'Extra Deck (Fusion, Synchro, Xyz ou Link) ?"), key:'cat_extra', test:c=>EXTRA_DECK.has(c.frameType), group:'deckzone' });

  // ── 3. Monstre Normal vs Effet ────────────────────────
  const nNormal = pool.filter(c => c.frameType === 'Normal').length;
  const nEffet  = pool.filter(c => c.frameType === 'Effet').length;
  if (nNormal > 0 && nEffet > 0)
    qs.push({ label: pickVariant('frame_normal', 'Est-ce un monstre Normal (sans effet, cadre jaune) ?'), key:'frame_normal', test:c=>c.frameType==='Normal', group:'frameType' });

  // ── 4. has_effect ────────────────────────────────────
  const hasEffectCards = pool.filter(c => c.hasEffect === 1);
  const noEffectCards  = pool.filter(c => c.hasEffect === 0);
  if (hasEffectCards.length > 0 && noEffectCards.length > 0)
    qs.push({
      label: pickVariant('has_effect_1', 'Est-ce que la carte possède un vrai effet de jeu (pas juste un texte de lore) ?'),
      key: 'has_effect_1',
      test: c => c.hasEffect === 1,
      group: 'has_effect',
    });

  // ── 5. Détail types Extra Deck ───────────────────────
  ['Fusion','Synchro','XYZ','Link'].forEach(v =>
    qs.push({ label:`Est-ce une carte ${v} ?`, key:'frameType_eq_'+v, test:c=>c.frameType===v, group:'frameType' })
  );
  ['Rituel','Pendule'].forEach(v =>
    qs.push({ label:`Est-ce une carte ${v} ?`, key:'frameType_eq_'+v, test:c=>c.frameType===v, group:'frameType' })
  );

  // ── 6. Attribut ──────────────────────────────────────
  attrs.forEach(v => qs.push({
    label: `Est-ce que l'attribut est "${v}" ?`,
    key: 'attr_eq_'+v,
    test: c => c.attribute===v,
    group: 'attribute',
  }));

  // ── 7. Race / sous-type ──────────────────────────────
  races.forEach(v => qs.push({
    label: raceLabel(v, ctx),
    key: 'race_eq_'+v,
    test: c => c.race===v,
    group: 'race',
  }));

  // ── 8. Archétype ────────────────────────────────────
  if (hasArchPool > 0 && noArchPool > 0)
    qs.push({ label: pickVariant('has_archetype', 'Est-ce que la carte appartient à un archétype ?'), key:'has_archetype', test:c=>c.archetype!=='—', group:'has_archetype' });

  if (archetypes.length > 0) {
    const archInRange = (c, a, z) => {
      const l = (c.archetype[0]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase();
      return c.archetype !== '—' && l >= a && l <= z;
    };
    ARCH_INTERVALS.forEach(({a, z}) => qs.push({
      label: `L'archétype commence-t-il par une lettre entre ${a} et ${z} ?`,
      key: `arch_range_${a}${z}`,
      test: c => archInRange(c, a, z),
      group: `arch_range_${a}${z}`,
    }));
    if (pool.length <= 300) {
      'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach(l => qs.push({
        label: `L'archétype commence-t-il par la lettre "${l}" ?`,
        key: 'arch_letter_'+l,
        test: c => c.archetype!=='—' && (c.archetype[0]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase()===l,
        group: 'arch_letter',
      }));
    }
    if (archetypes.length <= 20) {
      archetypes.forEach(v => qs.push({
        label: `Est-ce une carte de l'archétype "${v}" ?`,
        key: 'arch_eq_'+v,
        test: c => c.archetype===v,
        group: 'archetype',
      }));
    }
  }

  // ── 9. Banlist ───────────────────────────────────────
  if (bans.length > 1) {
    bans.forEach(v => qs.push({
      label: `Est-ce que la carte est "${v}" sur la Banlist TCG ?`,
      key: 'ban_eq_'+v,
      test: c => c.ban===v,
      group: 'ban',
    }));
  }

  // ── 10. Seuils ATK / DEF / Niveau ────────────────────
  const hasAtk = pool.some(c => c.atk >= 0);
  const hasDef = pool.some(c => c.def >= 0);
  const hasLvl = pool.some(c => c.level > 0);

  if (hasAtk) ATK_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que l'ATK est ≥ ${t} ?`,
    key: 'atk_gte_'+t, test: c=>c.atk>=0&&c.atk>=t, group:'atk',
  }));
  if (hasDef) DEF_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que la DEF est ≥ ${t} ?`,
    key: 'def_gte_'+t, test: c=>c.def>=0&&c.def>=t, group:'def',
  }));
  if (hasLvl) LVL_THRESHOLDS.forEach(t => qs.push({
    label: `Est-ce que le Niveau / Rang est ≥ ${t} ?`,
    key: 'lvl_gte_'+t, test: c=>c.level>=t, group:'level',
  }));

  if (hasLvl && pool.length <= 400) {
    [1,2,3,4,5,6,7,8,10,12].forEach(n => qs.push({
      label: `Est-ce que le Niveau / Rang est exactement ${n} ?`,
      key: 'lvl_eq_'+n, test: c=>c.level===n, group:'level_exact',
    }));
  }
  if (hasAtk && pool.length <= 120) {
    [...new Set(pool.map(c=>c.atk).filter(v=>v>=0))].forEach(v => qs.push({
      label: `Est-ce que l'ATK est exactement ${v} ?`,
      key: 'atk_eq_'+v, test: c=>c.atk===v, group:'atk_exact',
    }));
  }
  if (pool.some(c => c.atk>=0&&c.def>=0)) {
    qs.push({ label:"Est-ce que l'ATK est supérieure à la DEF ?", key:'atk_gt_def', test:c=>c.atk>=0&&c.def>=0&&c.atk>c.def, group:'atk_vs_def' });
  }

  // ── 11. Valeur de Lien exacte ─────────────────────────
  const linkCards = pool.filter(c => c.frameType === 'Link' && c.linkval > 0);
  if (linkCards.length > 0) {
    [1,2,3,4,5,6].forEach(n => {
      if (linkCards.some(c => c.linkval === n))
        qs.push({ label:`Est-ce un monstre Lien-${n} ?`, key:'linkval_eq_'+n, test:c=>c.linkval===n, group:'linkval' });
    });
    [2,3,4].forEach(t => qs.push({
      label: `Est-ce que la valeur de Lien est ≥ ${t} ?`,
      key: 'linkval_gte_'+t, test:c=>c.linkval>=t, group:'linkval_gte',
    }));
  }

  // ── 12. Marqueurs de Lien ────────────────────────────
  const allMarkers = [...new Set(pool.flatMap(c => c.linkmarkers))].filter(Boolean);
  allMarkers.forEach(m => {
    const cnt = pool.filter(c => c.linkmarkers.includes(m)).length;
    if (cnt > 0 && cnt < pool.length)
      qs.push({ label:`Est-ce que la carte a un marqueur de Lien vers le "${m}" ?`, key:'lm_'+m, test:c=>c.linkmarkers.includes(m), group:'linkmarkers' });
  });

  // ── 13. Échelle Pendule ──────────────────────────────
  const pendCards = pool.filter(c => c.scale >= 0 && c.frameType === 'Pendule');
  if (pendCards.length > 0) {
    [1,3,5,7,9].forEach(t => qs.push({
      label: `Est-ce que l'échelle Pendule est ≥ ${t} ?`,
      key: 'scale_gte_'+t, test:c=>c.scale>=t, group:'scale',
    }));
    [1,2,3,4,5,6,7,8,9,10].forEach(n => {
      if (pendCards.some(c => c.scale === n))
        qs.push({ label:`Est-ce que l'échelle Pendule est exactement ${n} ?`, key:'scale_eq_'+n, test:c=>c.scale===n, group:'scale_exact' });
    });
  }

  // ── 14. Formats ──────────────────────────────────────
  const FORMAT_LABELS = {
    'master duel':  'Master Duel',
    'duel links':   'Duel Links',
    'speed duel':   'Speed Duel',
    'rush duel':    'Rush Duel',
    'ocg':          'OCG (Japon)',
    'tcg':          'TCG',
    'goat':         'Format Goat',
  };
  Object.entries(FORMAT_LABELS).forEach(([fkey, flabel]) => {
    const inFormat = pool.filter(c => c.formats.has(fkey)).length;
    if (inFormat > 0 && inFormat < pool.length)
      qs.push({
        label: `Est-ce que la carte est disponible en ${flabel} ?`,
        key: 'format_'+fkey.replace(/ /g,'_'),
        test: c => c.formats.has(fkey),
        group: 'format',
      });
  });

  // ── 15. Époque de sortie TCG ─────────────────────────
  const cardsWithDate = pool.filter(c => c.tcgYear !== null);
  if (cardsWithDate.length > 0) {
    YEAR_CUTS.forEach(y => {
      const before = cardsWithDate.filter(c => c.tcgYear < y).length;
      if (before > 0 && before < cardsWithDate.length)
        qs.push({
          label: `Est-ce que la carte est sortie avant ${y} (TCG) ?`,
          key: 'year_lt_'+y,
          test: c => c.tcgYear !== null && c.tcgYear < y,
          group: 'epoch',
        });
    });
    [2000,2005,2010,2015,2020].forEach(decade => {
      const inDecade = cardsWithDate.filter(c => c.tcgYear >= decade && c.tcgYear < decade+5).length;
      if (inDecade > 0 && inDecade < cardsWithDate.length)
        qs.push({
          label: `Est-ce que la carte est sortie entre ${decade} et ${decade+4} (TCG) ?`,
          key: 'decade_'+decade,
          test: c => c.tcgYear !== null && c.tcgYear >= decade && c.tcgYear < decade+5,
          group: 'epoch_decade',
        });
    });
  }

  // ── 19. Questions sur le nom ──────────────────────────
  const ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  const nameInRange  = (c, a, z) => { const l=(c.name[0]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase(); return l>=a&&l<=z; };
  const nameInRange2 = (c, a, z) => { const l=(c.name[1]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase(); return l>=a&&l<=z; };

  NAME_INTERVALS.forEach(({a, z}) => qs.push({
    label: `Le nom de ta carte commence-t-il par une lettre entre ${a} et ${z} ?`,
    key: `name_range_${a}${z}`,
    test: c => nameInRange(c, a, z),
    group: `name_range_${a}${z}`,
  }));

  if (pool.length <= 500) {
    ALPHA.forEach(l => qs.push({
      label: `Le nom de ta carte commence-t-il par la lettre "${l}" ?`,
      key: 'name_letter_'+l, test:c=>(c.name[0]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase()===l, group:'name_letter',
    }));
  }

  if (pool.length <= 800) {
    NAME2_INTERVALS.forEach(({a, z}) => qs.push({
      label: `La deuxième lettre du nom de ta carte est-elle entre ${a} et ${z} ?`,
      key: `name2_range_${a}${z}`,
      test: c => nameInRange2(c, a, z),
      group: `name2_range_${a}${z}`,
    }));
    if (pool.length <= 300) {
      ALPHA.forEach(l => qs.push({
        label: `La deuxième lettre du nom de ta carte est-elle "${l}" ?`,
        key: 'name_letter2_'+l, test:c=>(c.name[1]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase()===l, group:'name_letter2',
      }));
    }
  }

  [1,2,3,4,5].forEach(t=>qs.push({
    label: `Le nom contient-il plus de ${t} mot${t>1?'s':''} ?`,
    key: 'name_words_'+t, test:c=>c.name.trim().split(/\s+/).length>t, group:'name_words',
  }));

  if (pool.length > 6) {
    const STOP = new Set(['de','du','des','le','la','les','un','une','et','en','a','au','aux','par','sur','dans','pour','avec','sans','que','qui','ou','the','of','to','an','and','in','on','for','with','from']);
    const freq = {};
    pool.forEach(c => {
      c.name.split(/[\s\-\/''!?,.:]+/).forEach(w => {
        const wl = w.toLowerCase().replace(/[^a-z\u00c0-\u024f]/gi,'');
        if (wl.length >= 3 && !STOP.has(wl)) freq[wl]=(freq[wl]||0)+1;
      });
    });
    const total = pool.length;
    Object.entries(freq)
      .filter(([,cnt])=>cnt>=total*0.1&&cnt<=total*0.9)
      .sort((a,b)=>Math.abs(a[1]/total-0.5)-Math.abs(b[1]/total-0.5))
      .slice(0,60)
      .forEach(([w])=>qs.push({ label:`Le nom contient-il le mot "${w}" ?`, key:'name_word_'+w, test:c=>c.name.toLowerCase().includes(w), group:'name_word' }));
  }

  return qs;
}

// ══════════════════════════════════════════════════════════
//  SCORE D'ENTROPIE
// ══════════════════════════════════════════════════════════

function bestQuestion(pool, askedKeys, resolvedGroups) {
  const qs = buildQuestions(pool).filter(q =>
    !askedKeys.has(q.key) && !resolvedGroups.has(q.group)
  );

  const scoreQ = (q, aggressive) => {
    const yes = pool.filter(q.test).length;
    const no  = pool.length - yes;
    if (yes === 0 || no === 0) return -1;
    const ratio = yes / pool.length;
    const base  = 1 - Math.abs(ratio - 0.5) * 2;
    // En mode agressif (gros pool) : peu de bruit, on veut vraiment 50/50
    // En mode souple (petit pool) : plus de bruit, on laisse les groupes jouer
    const noise = aggressive ? 0.03 : 0.12;
    return base + (Math.random() * noise * 2 - noise);
  };

  // ── Q1 : toujours monstre/magie/piège ────────────────
  if (!resolvedGroups.has('cardcat')) {
    const cats = qs.filter(q => q.group === 'cardcat');
    if (cats.length > 0) {
      let best = null, bestScore = -1;
      for (const q of cats) { const s = scoreQ(q, false); if (s > bestScore) { bestScore = s; best = q; } }
      if (best) return best;
    }
  }

  const n = pool.length;

  // ── GROS POOL (>800) : priorité entropie pure ────────
  if (n > 800) {
    let best = null, bestScore = -1;
    for (const q of qs) {
      const s = scoreQ(q, true);
      if (s > bestScore) { bestScore = s; best = q; }
    }
    return best;
  }

  // ── POOL MOYEN (300-800) : entropie + quelques groupes clés ──
  if (n > 300) {
    // Forcer 1 question d'intervalle de lettre si pas encore posée
    const nameRangeCandidates = qs.filter(q =>
      q.group.startsWith('name_range_') || q.group.startsWith('arch_range_')
    );
    if (nameRangeCandidates.length > 0 && Math.random() < 0.35) {
      let best = null, bestScore = -1;
      for (const q of nameRangeCandidates) {
        const s = scoreQ(q, true);
        if (s > bestScore) { bestScore = s; best = q; }
      }
      if (best) return best;
    }

    // Sinon : meilleure entropie globale
    let best = null, bestScore = -1;
    for (const q of qs) {
      const s = scoreQ(q, true);
      if (s > bestScore) { bestScore = s; best = q; }
    }
    return best;
  }

  // ── PETIT POOL (<300) : groupes sémantiques prioritaires ──
  // Ici on veut des questions intéressantes, pas juste ATK ≥ X
  const PRIORITY_SEMANTIC = [
    'cardcat', 'deckzone', 'frameType', 'has_effect',
    'attribute', 'race', 'has_archetype', 'archetype',
    'arch_letter', 'name_letter', 'name_letter2', 'name_word',
    'ban', 'format',
  ];
  const PRIORITY_NUMERIC = [
    'level', 'level_exact', 'atk', 'atk_exact', 'atk_vs_def',
    'def', 'linkval', 'linkval_gte', 'linkmarkers', 'scale', 'scale_exact',
    'epoch', 'epoch_decade', 'name_words',
  ];

  // 1 question d'intervalle de lettre garantie si pool ≤ 500 et pas encore posée
  const nameRangeDone = [...askedKeys].some(k => k.startsWith('name_range_') || k.startsWith('name2_range_'));
  if (!nameRangeDone && n <= 500) {
    const rangeCandidates = qs.filter(q =>
      q.group.startsWith('name_range_') || q.group.startsWith('name2_range_')
    );
    if (rangeCandidates.length > 0) {
      let best = null, bestScore = -1;
      for (const q of rangeCandidates) {
        const s = scoreQ(q, true);
        if (s > bestScore) { bestScore = s; best = q; }
      }
      if (best) return best;
    }
  }

  const PRIORITY = [...PRIORITY_SEMANTIC, ...PRIORITY_NUMERIC];
  const topCandidates = [];
  for (const grp of PRIORITY) {
    if (resolvedGroups.has(grp)) continue;
    const candidates = qs.filter(q => q.group === grp);
    if (candidates.length === 0) continue;
    let best = null, bestScore = -1;
    for (const q of candidates) {
      const s = scoreQ(q, false);
      if (s >= 0.10 && s > bestScore) { bestScore = s; best = q; }
    }
    if (best) {
      topCandidates.push({ q: best, score: bestScore });
      if (topCandidates.length >= 5) break;
    }
  }

  if (topCandidates.length > 0) {
    const first      = topCandidates[0];
    const globalBest = topCandidates.reduce((a, b) => b.score > a.score ? b : a);
    return (first.score >= globalBest.score * 0.70) ? first.q : globalBest.q;
  }

  // Fallback absolu
  let best = null, bestScore = -1;
  for (const q of qs) {
    const s = scoreQ(q, false);
    if (s > bestScore) { bestScore = s; best = q; }
  }
  return best;
}


// ══════════════════════════════════════════════════════════
//  ÉTAT DU JEU
// ══════════════════════════════════════════════════════════

let yPool           = [];
let yAsked          = new Set();
let yResolved       = new Set();
let yHistory        = [];
let yHistory_states = [];
let yGuessIdx       = 0;
let yGameOver       = false;
let yCurQ           = null;
let yThinking       = false;
let yQCount         = 0;
let ySortedPool     = [];

function yugiInit() {
  yPool=[]; yAsked=new Set(); yResolved=new Set();
  yHistory=[]; yHistory_states=[]; yGuessIdx=0;
  yGameOver=false; yCurQ=null; yThinking=false; yQCount=0; ySortedPool=[];
  yPool = ALL_CARDS.slice();

  document.getElementById('yResult').className = 'y-result';
  document.getElementById('yRestart').classList.remove('on');
  const rimg = document.getElementById('yRimg');
  if (rimg) { rimg.src=''; rimg.style.display='none'; }

  renderHistory();
  updatePoolInfo();

  // ── BLOC 3 : générer les intervalles au début de chaque partie
  NAME_INTERVALS  = randomIntervals();
  NAME2_INTERVALS = randomIntervals();
  ARCH_INTERVALS  = randomIntervals();

  nextStep();
}

function nextStep() {
  if (yGameOver) return;
  if (yPool.length===0) { showGiveUp(); return; }
  if (yPool.length<=1)  { enterGuessPhase(); return; }
  const q = bestQuestion(yPool, yAsked, yResolved);
  if (!q) { enterGuessPhase(); return; }
  yCurQ = q;
  showQuestion(q);
}

const QNUM_PHRASES = [
  q => `QUESTION ${q}`,
  q => `INDICE ${q}`,
  q => `SONDE N°${q}`,
  q => `DÉDUCTION ${q}`,
  q => `ANALYSE ${q}`,
  q => `INTUITION ${q}`,
  q => `RÉFLEXION ${q}`,
  q => q === 1 ? `PREMIÈRE QUESTION` : `QUESTION ${q}`,
  q => q > 8  ? `PRESQUE… (${q})` : `QUESTION ${q}`,
  q => q > 5  ? `JE SENS QUELQUE CHOSE… (${q})` : `SONDE ${q}`,
  q => q > 6  ? `LE VOILE SE LÈVE… (${q})` : `QUESTION ${q}`,
  q => q > 10 ? `PATIENCE… (${q})` : `ANALYSE ${q}`,
  q => `🧠 CERVEAU EN MARCHE — Q.${q}`,
  q => `💭 PENSÉE ${q}`,
  q => q === 1 ? `PAR OÙ COMMENCER…` : `QUESTION ${q}`,
  q => `〔${q}〕`,
];


// Commentaires contextuels affichés parfois sous la question
const Q_CONTEXT_COMMENTS = [
  "Chaque réponse m'éclaire un peu plus…",
  "Je réduis le champ…",
  "Le brouillard se dissipe.",
  "Intéressant.",
  "Hmm… noté.",
  "Ça m'aide déjà beaucoup.",
  "Je commence à voir quelque chose.",
  "Mon instinct s'affûte.",
  "Les pièces s'assemblent.",
  "Je n'ai plus beaucoup de questions à poser.",
];
 
function showQuestion(q) {
  yThinking = false;
  setUI('question');
  const phraseFn = QNUM_PHRASES[Math.floor(Math.random() * QNUM_PHRASES.length)];
  document.getElementById('yQnum').textContent = phraseFn(yQCount + 1);
 
  // 25% de chance d'ajouter un commentaire contextuel après la question
  let label = q.label;
  if (yQCount >= 3 && Math.random() < 0.25) {
    const comment = Q_CONTEXT_COMMENTS[Math.floor(Math.random() * Q_CONTEXT_COMMENTS.length)];
    label = label + '  —  ' + comment;
  }
  document.getElementById('yQtext').textContent = label;
  updateProgress();
}


function updateProgress() {
  const pct = Math.round(Math.max(5,Math.min(95,(1-yPool.length/ALL_CARDS.length)*100)));
  document.getElementById('yConf').textContent = pct+'%';
  document.getElementById('yProgFill').style.width = pct+'%';
}

function yugiUndo() {
  if (yHistory_states.length===0||yGameOver) return;
  const snap = yHistory_states.pop();
  yPool=snap.pool; yAsked=snap.asked; yResolved=snap.resolved;
  yHistory=snap.history; yQCount=snap.qCount; yCurQ=snap.curQ;
  yGuessIdx=0; yThinking=false; ySortedPool=[];
  renderHistory(); updatePoolInfo(); showQuestion(yCurQ);
}

// ── BLOC 4 : applyAnswer corrigé ─────────────────────────
function applyAnswer(pool, q, ans) {
  if (ans==='oui') { const f=pool.filter(q.test); return f.length>0?f:pool; }
  if (ans==='non') { const f=pool.filter(c=>!q.test(c)); return f.length>0?f:pool; }
  const MINORITY_RATIO = 0.12;
  if (ans==='plutot_oui') {
    const yes=pool.filter(q.test), no=pool.filter(c=>!q.test(c));
    const kept=no.slice(0, Math.max(1, Math.round(no.length*MINORITY_RATIO)));
    const m=[...yes,...kept]; return m.length>0?m:pool;
  }
  if (ans==='plutot_non') {
    const yes=pool.filter(q.test), no=pool.filter(c=>!q.test(c));
    const kept=yes.slice(0, Math.max(1, Math.round(yes.length*MINORITY_RATIO)));
    const m=[...no,...kept]; return m.length>0?m:pool;
  }
  return pool;
}

function yugiAnswer(ans) {
  if (yThinking||yGameOver||!yCurQ) return;
  const q=yCurQ;
  yHistory_states.push({ pool:yPool.slice(), asked:new Set(yAsked), resolved:new Set(yResolved), history:yHistory.slice(), qCount:yQCount, curQ:yCurQ });
  yAsked.add(q.key);
  yQCount++;
  yPool=applyAnswer(yPool,q,ans);

  // DEBUG temporaire
  const exodiaCards = yPool.filter(c => c.name.toLowerCase().includes('exodia') || c.name.toLowerCase().includes('necross'));
  if (exodiaCards.length > 0) console.log('[DEBUG] Exodia restants:', exodiaCards.map(c => c.name + ' | ban:' + c.ban + ' | frame:' + c.frameType + ' | arch:' + c.archetype));
  else console.log('[DEBUG] Plus aucune carte Exodia dans le pool après:', q.label, '→', ans);

  // Résolution de groupes
  if (ans==='oui'&&q.key.includes('_eq_')) yResolved.add(q.group);
  if (q.group==='cardcat' && ans==='oui') yResolved.add('cardcat');

  // ── BLOC 7 : résolution archétype corrigée ────────────
  if (q.key==='has_archetype') {
    yResolved.add('has_archetype');
    if (ans==='non'||ans==='plutot_non'||ans==='ne_sais_pas') {
      yResolved.add('archetype'); yResolved.add('arch_letter');
      ARCH_INTERVALS.forEach(({a,z}) => yResolved.add(`arch_range_${a}${z}`));
    }
  }

  if (q.group==='format'&&ans==='oui') yResolved.add('format');

  const ansLabel={oui:'OUI',non:'NON',plutot_oui:'~OUI',plutot_non:'~NON',ne_sais_pas:'?'};
  yHistory.push({label:q.label,ans:ansLabel[ans]||ans,pool:yPool.length});
  renderHistory(); updatePoolInfo();

  yThinking=true; setUI('thinking');
  setTimeout(()=>nextStep(),500);
}

// ── BLOC 5 : enterGuessPhase corrigé ─────────────────────
function enterGuessPhase() {
  ySortedPool = yPool.slice().sort((a, b) => {
    const aM = MONSTER_FRAMES.has(a.frameType) ? 1 : 0;
    const bM = MONSTER_FRAMES.has(b.frameType) ? 1 : 0;
    if (aM !== bM) return bM - aM;
    const sa = (a.atk>0?a.atk:0) + (a.level>0?a.level*50:0);
    const sb = (b.atk>0?b.atk:0) + (b.level>0?b.level*50:0);
    if (sa !== sb) return sb - sa;
    return a.name.localeCompare(b.name, 'fr');
  });
  yGuessIdx = 0;
  showGuessStep();
}

const GUESS_INTROS = [
  "Est-ce que vous pensez à… ",
  "Le voile se lève… S'agit-il de ",
  "Je vois… je vois… serait-ce ",
  "Ma vision se précise — ",
  "Les esprits murmurent : ",
  "Le génie affirme : votre carte est ",
  "L'œil du destin révèle… ",
  "Les runes désignent… ",
  "Ah ! Ça y est, je le sens — ",
  "Hmm hmm hmm… ",
  "Mon cristal s'emballe — serait-ce ",
  "Vous pensez à ",
  "Confidence pour confidence : c'est ",
  "Je parie tout sur ",
  "Quelque chose me dit que c'est ",
  "Mon intuition crie : ",
  "Un flash ! C'est ",
  "Dix mille cartes, et je suis presque sûr — ",
];


function showGuessStep() {
  if (yGuessIdx >= ySortedPool.length) { showGiveUp(); return; }
  const card = ySortedPool[yGuessIdx]; yGuessIdx++;
  setUI('guess');
 
  // Numéro de révélation avec variations de texte
  const REVELATION_LABELS = [
    '🎯 RÉVÉLATION',
    '🔮 MA PROPOSITION',
    '⚡ HYPOTHÈSE',
    '👁 JE VOIS…',
    '🃏 MON CHOIX',
    '💡 ILLUMINATION',
  ];
  const rLabel = REVELATION_LABELS[Math.floor(Math.random() * REVELATION_LABELS.length)];
 
  const intro = GUESS_INTROS[Math.floor(Math.random() * GUESS_INTROS.length)];
  document.getElementById('yQnum').textContent = rLabel + ' ' + yGuessIdx;
  document.getElementById('yQtext').textContent = intro + card.name + ' ?';
  const pct = Math.min(99, 65 + yQCount * 3);
  document.getElementById('yConf').textContent = pct + '%';
  document.getElementById('yProgFill').style.width = pct + '%';
  document.getElementById('yAnswers').dataset.guessCard = card.name;
  document.getElementById('yAnswers').dataset.guessImg = card.img || '';
}


function yugiConfirmGuess(ok) {
  const name=document.getElementById('yAnswers').dataset.guessCard;
  const img=document.getElementById('yAnswers').dataset.guessImg;
  if (ok) { yGameOver=true; setUI('none'); showResult(true,name,img); return; }
  yPool=yPool.filter(c=>c.name!==name);
  ySortedPool=ySortedPool.filter(c=>c.name!==name);
  yHistory.push({label:'Est-ce '+name+' ?',ans:'NON',pool:yPool.length});
  renderHistory(); updatePoolInfo();
  yThinking=true; setUI('thinking');
  setTimeout(() => {
      if (yPool.length === 0) {
        yGameOver = true; setUI('none'); showResult(false, null, null); return;
      }
      if (ySortedPool.length === 0) { enterGuessPhase(); return; }
      showGuessStep();
    }, 400);
  }  // ← cette accolade ferme yugiConfirmGuess
  
  function showGiveUp() {
    if (yPool.length > 0) {
      enterGuessPhase();
      return;
    }
    yGameOver = true;
    setUI('none');
    showResult(false, null, null);
  }

function showResult(won,name,img) {
  const r=document.getElementById('yResult');
  r.className='y-result on '+(won?'win':'def');
  document.getElementById('yRttl').textContent=won?'🃏 TROUVÉ EN '+yQCount+' QUESTION'+(yQCount>1?'S':''):'☠ LE YUGINATOR S\'INCLINE';
  document.getElementById('yRcard').textContent=won?name:'???';
  const rimg=document.getElementById('yRimg');
  if (rimg) { if (won&&img){rimg.src=img;rimg.style.display='block';}else{rimg.style.display='none';} }
  document.getElementById('yRdesc').textContent=won
    ?'Le Yuginator a percé le voile en '+yQCount+' réponse'+(yQCount>1?'s':'')+' sur '+ALL_CARDS.length.toLocaleString('fr')+' cartes.'
    :'Votre carte a résisté à l\'analyse. '+yPool.length+' candidate'+(yPool.length>1?'s':'')+' restai'+(yPool.length>1?'ent':'t')+'. Quelle était-elle ?';
  if (!won&&yPool.length>0&&yPool.length<=20) {
    const extra=document.createElement('div');
    extra.style.cssText='font-size:.78rem;color:var(--color-text-secondary);margin-top:.5rem;font-style:italic;';
    extra.textContent='Candidats restants : '+yPool.slice(0,8).map(c=>c.name).join(', ')+(yPool.length>8?'…':'');
    document.getElementById('yResult').appendChild(extra);
  }
  document.getElementById('yRestart').classList.add('on');
}

// ── UI HELPERS ────────────────────────────────────────────

function setUI(mode) {
  const ans=document.getElementById('yAnswers');
  const orb=document.getElementById('yOrb');
  if (mode==='thinking') {
    orb.classList.add('thinking'); orb.textContent='⚡';
    document.getElementById('yQnum').textContent='ANALYSE EN COURS…';
    document.getElementById('yQtext').textContent='…';
    ans.style.display='none'; return;
  }
  orb.classList.remove('thinking');
  orb.textContent=mode==='guess'?'🎯':'🔮';
  if (mode==='none') { ans.style.display='none'; return; }
  ans.style.display='flex';
  if (mode==='question') {
    ans.innerHTML=`
      <button class="y-btn yes"     onclick="yugiAnswer('oui')">✅ OUI</button>
      <button class="y-btn pyesbtn" onclick="yugiAnswer('plutot_oui')">🟡 PLUTÔT OUI</button>
      <button class="y-btn pnobtn"  onclick="yugiAnswer('plutot_non')">🟠 PLUTÔT NON</button>
      <button class="y-btn no"      onclick="yugiAnswer('non')">❌ NON</button>
      <button class="y-btn idk"     onclick="yugiAnswer('ne_sais_pas')">🤷 JE NE SAIS PAS</button>`;
  } else if (mode==='guess') {
    ans.innerHTML=`
      <button class="y-btn yes" onclick="yugiConfirmGuess(true)">✅ OUI, C'EST ÇA !</button>
      <button class="y-btn no"  onclick="yugiConfirmGuess(false)">❌ NON, CE N'EST PAS ÇA</button>`;
  }
  if (yHistory_states.length>0) {
    const u=document.createElement('button');
    u.className='y-btn undo'; u.textContent='↩ RETOUR'; u.onclick=yugiUndo;
    ans.appendChild(u);
  }
}

function updatePoolInfo() {
  const el=document.getElementById('yPoolInfo');
  if (!el) return;
  const n=yPool.length;
  el.textContent=n.toLocaleString('fr')+' carte'+(n>1?'s':'')+' restante'+(n>1?'s':'');
}

function renderHistory() {
  const list=document.getElementById('yHist');
  if (!list) return;
  list.innerHTML='';
  yHistory.forEach(h=>{
    const item=document.createElement('div'); item.className='y-hi';
    const clsMap={'OUI':'yes','NON':'no','~OUI':'pyesbtn','~NON':'pnobtn','?':'idk'};
    const cls=clsMap[h.ans]||'idk';
    item.innerHTML=`<span class="hq">${h.label}</span><span class="ha ${cls}">${h.ans}</span>`;
    if (h.pool!==undefined) {
      const pi=document.createElement('span'); pi.className='hpool'; pi.textContent=h.pool.toLocaleString('fr'); item.appendChild(pi);
    }
    list.appendChild(item);
  });
  list.scrollTop=list.scrollHeight;
}

function yugiRestart() {
  document.getElementById('yOrb').textContent='🔮';
  document.getElementById('yOrb').className='y-orb';
  document.getElementById('yHist').innerHTML='';
  document.getElementById('yProgFill').style.width='0%';
  document.getElementById('yConf').textContent='0%';
  yugiInit();
}

// ── BOOTSTRAP : startGame() → yugiLoadCards() → yugiInit()
