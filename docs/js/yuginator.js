// ══════════════════════════════════════════════════════════
//  YUGINATOR — moteur entropique pur JS, zéro IA
//  Branché sur YGOPRODeck (même normalize() que guesser.js)
// ══════════════════════════════════════════════════════════

// ── NORMALISATION ─────────────────────────────────────────

const MONSTER_FRAMES = new Set(['Normal','Effet','Rituel','Fusion','Synchro','XYZ','Link','Pendule','Jeton','Skill']);
const SPELL_FRAMES   = new Set(['Magie']);
const TRAP_FRAMES    = new Set(['Piège']);

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
    'Banned':'Interdit', 'Forbidden':'Interdit',
    'Limited':'Limité',
    'Semi-Limited':'Semi-Limité',
  };
  return map[b] || 'Autorisé';
}

// ══════════════════════════════════════════════════════════
//  ARCHÉTYPES — map EN→FR + fallback automatique
//  Sources : Wiki Yu-Gi-Oh! FR / Yugipedia / noms officiels TCG FR
// ══════════════════════════════════════════════════════════

const ARCHETYPE_FR = {
  // A
  'Abyss Actor':                  'Acteur des Abîmes',
  'Abyss Playhouse':              'Salle de Jeu des Abîmes',
  'Adamancipator':                'Adamancipateur',
  'Aesir':                        'Ases',
  'Agido':                        'Agido',
  'Alien':                        'Alien',
  'Alligator':                    'Alligator',
  'Altergeist':                   'Altergiste',
  'Amazoness':                    'Amazonesse',
  'Amorphage':                    'Amorphage',
  'Ancient Gear':                 'Rouages Ancients',
  'Ancient Warriors':             'Guerriers Antiques',
  'Antitopian':                   'Antitopien',
  'Aquaactress':                  'Aquactrice',
  'Archfiend':                    'Archdémon',
  'Aroma':                        'Arôme',
  'Artifact':                     'Artéfact',
  'Assault Mode':                 'Mode Assaut',
  'Atlantean':                    'Atlante',
  'Avian':                        'Aviaire',
  // B
  'B.E.S.':                       'B.E.S.',
  'Baby Dragon':                  'Bébé Dragon',
  'Barrier Statue':               'Statue Barrière',
  'Batteryman':                   'des Gardes',
  'Battlin\' Boxer':              'Boxeur de Combat',
  'Beaststrike Wall':             'Mur Bête de Frappe',
  'Black Luster Soldier':         'Soldat du Lustre Noir',
  'Blackwing':                    'Aile Noire',
  'Blaze Accelerator':            'Accélérateur de Flammes',
  'Blue-Eyes':                    'Yeux Bleus',
  'Blue-Eyes White Dragon':       'Dragon Blanc aux Yeux Bleus',
  'Brotherhood of the Fire Fist': 'Fraternité du Poing de Feu',
  'Burning Abyss':                'Abîme Ardent',
  'Buster Blader':                'Buster Blader',
  'Butterspy':                    'Espion Papillon',
  // C
  'Celtic Guard':                 'Celt',
  'Chronomaly':                   'Chronomalie',
  'Cipher':                       'Cipher',
  'Code Talker':                  'Codeur',
  'Constellar':                   'Constellaire',
  'Crystal Beast':                'Bête de Cristal',
  'Crystron':                     'Cryston',
  'Cubic':                        'Cubique',
  'Cyber':                        'Cyber',
  'Cyber Angel':                  'Ange Cyber',
  'Cyber Dragon':                 'Cyber Dragon',
  'Cyberdark':                    'Cybersombre',
  'Cybernetic':                   'Cybernétique',
  'Cyberse':                      'Cyberse',
  // D
  'D.D.':                         'D.D.',
  'D/D':                          'D/D',
  'D/D/D':                        'D/D/D',
  'Dark Magician':                'Magicien Sombre',
  'Dark Scorpion':                'Scorpion Noir',
  'Dark World':                   'Monde Ténébreux',
  'Darklord':                     'Ange Déchu',
  'Deskbot':                      'Burobot',
  'Destiny HERO':                 'HÉROS du Destin',
  'Dinomist':                     'Dinomiste',
  'Dinomorphia':                  'Dinomorphia',
  'Dogmatika':                    'Dogmatika',
  'Dragunity':                    'Dragunité',
  'Dragonmaid':                   'Servante Dragon',
  'Dragon Ruler':                 'Seigneur Dragon',
  'Drytron':                      'Drytron',
  'Dual Avatar':                  'Avatar Dual',
  // E
  'Earthbound':                   'Esprit de la Terre',
  'Edge Imp':                     'Lutin Lame',
  'Eldlich':                      'Eldlich',
  'Elemental HERO':               'HÉROS Élémentaire',
  'Endymion':                     'Endymion',
  'Evilswarm':                    'Verminpeste',
  'Evil HERO':                    'HÉROS du Mal',
  'Evil Eye':                     'Mauvais Œil',
  'Evolsaur':                     'Évolosaure',
  'Evoltile':                     'Évoreptile',
  'Exodia':                       'Éxodia',
  'Exosister':                    'Exosœur',
  // F
  'F.A.':                         'F.A.',
  'Fabled':                       'Légendaire',
  'Fairy Tail':                   'Conte de Fées',
  'Fallen of Albaz':              'Chute d\'Albaz',
  'Floowandereeze':               'Floowandereeze',
  'Fluffal':                      'Peluche',
  'Fortune Lady':                 'Dame Fortune',
  'Fossil':                       'Fossile',
  'Frog':                         'Grenouille',
  'Fur Hire':                     'En Service',
  // G
  'G Golem':                      'Golem G',
  'Gagaga':                       'Gagaga',
  'Gaia The Fierce Knight':       'Gaïa le Chevalier Implacable',
  'Gaia the Dragon Champion':     'Gaïa le Dragon Champion',
  'Galaxy':                       'Galaxie',
  'Galaxy-Eyes':                  'Yeux Galaxie',
  'Gate Guardian':                'Gardien de la Porte',
  'Gem-Knight':                   'Chevalier Gemme',
  'Generaider':                   'Généraider',
  'Ghostrick':                    'Fantôruse',
  'Gimmick Puppet':               'Marionnette Gadget',
  'Gishki':                       'Gishki',
  'Goblin':                       'Gobelin',
  'Gouki':                        'Gouki',
  'Gravekeeper\'s':               'Protecteurs du Tombeau',
  'Guardian':                     'Gardien',
  'Gusto':                        'Gusto',
  // H
  'HERO':                         'HÉROS',
  'Harpie':                       'Harpie',
  'Heraldic Beast':               'Bête Héraldique',
  'Hi-Speedroid':                 'Hi-Speedroïd',
  'Hieratic':                     'Hiératique',
  'Horus':                        'Horus',
  'Horus the Black Flame Dragon': 'Horus Dragon de la Flamme Noire',
  // I
  'Ice Barrier':                  'Barrière de Glace',
  'Icejade':                      'Jade de Glace',
  'Igknight':                     'Chevalier Ignis',
  'Ignister':                     'Ignister',
  'Impcantation':                 'Diablocantatoire',
  'Infernity':                    'Infernité',
  'Infernoid':                    'Inferno',
  'Invoked':                      'Invoqué',
  'Inzektor':                     'Inzecteur',
  // J
  'Jackpot 7':                    'Jackpot 7',
  'Jinzo':                        'Jinzo',
  'Junk':                         'Ferraille',
  // K
  'Kaiju':                        'Kaiju',
  'Kashtira':                     'Kashtira',
  'Knightmare':                   'Cauchemar du Chevalier',
  'Krawler':                      'Rampant',
  'Kuriboh':                      'Kuriboh',
  // L
  'Labrynth':                     'Labyrinthe',
  'Laval':                        'Laval',
  'Legendary Dragon':             'Dragon Légendaire',
  'Lightray':                     'Rayon de Lumière',
  'Lightsworn':                   'Seigneur Lumière',
  'Lunalight':                    'Clair de Lune',
  'Lyrilusc':                     'Lyrilusque',
  'Lswarm':                       'Essaim-L',
  // M
  'M-X-Saber':                    'M-X-Sabre',
  'Machina':                      'Machin',
  'Madolche':                     'Madolché',
  'Magician':                     'Magicien',
  'Majespecter':                  'Majespecteur',
  'Malefic':                      'Corrompu',
  'Marincess':                    'Marinesse',
  'Mathmech':                     'Mathméca',
  'Megalith':                     'Mégalithe',
  'Melffy':                       'Peluchimal',
  'Melodious':                    'Mélodieux',
  'Memento':                      'Mémento',
  'Mermail':                      'Aquamer',
  'Metalfoes':                    'Métalfeu',
  'Metamorph':                    'Métalmorphe',
  'Millennium':                   'Millénaire',
  'Mist Valley':                  'Vallée de Brume',
  'Monarch':                      'Monarque',
  'Myutant':                      'Myutant',
  // N
  'Naturia':                      'Naturie',
  'Nekroz':                       'Nékroz',
  'Neo Space':                    'Néo-Espace',
  'Neo-Spacian':                  'Néo-Spatial',
  'Neos':                         'Néos',
  'Nephthys':                     'Nephtys',
  'Noble Knight':                 'Noble Chevalier',
  'Number':                       'Numéro',
  'Numeron':                      'Numéron',
  // O
  'Ojama':                        'Ojama',
  'Orcust':                       'Orcuste',
  // P
  'P.U.N.K.':                     'P.U.N.K.',
  'Paleozoic':                    'Paléozoïque',
  'Pendulum':                     'Pendule',
  'Penguin':                      'Pingouin',
  'Performapal':                  'Saltimbanque',
  'Performage':                   'Performeur',
  'Phantom Beast':                'Bête Fantôme',
  'Phantom Knights':              'Chevaliers Fantômes',
  'Photon':                       'Photon',
  'Plunder Patroll':              'Patrouille de Pillards',
  'Predaplant':                   'Prédaplante',
  'Prediction Princess':          'Princesse de Prédiction',
  'Prank-Kids':                   'Bambins Facétieux',
  'Prophecy':                     'Prophétie',
  'Purrely':                      'Purrely',
  // R
  'R-Genex':                      'R-Genex',
  'Raidraptor':                   'Raidraptor',
  'Rank-Up-Magic':                'Magie Montée en Rang',
  'Red Dragon Archfiend':         'Dragon Rouge Archdémon',
  'Red-Eyes':                     'Yeux Rouges',
  'Relinquished':                 'Le Renoncé',
  'Rikka':                        'Rikka',
  'Ritual Beast':                 'Bête Rituelle',
  'Roid':                         'roid',
  'Rokket':                       'Rokket',
  'Rose Dragon':                  'Dragon Rose',
  // S
  'S-Force':                      'Force-S',
  'Saber':                        'Sabre',
  'Salamangreat':                 'Salamangreat',
  'Satellarknight':               'Satellachevalier',
  'Scareclaw':                    'Griffempouvantail',
  'Scrap':                        'Ferraille',
  'Shaddoll':                     'Ombre-Poupée',
  'Silent Magician':              'Magicien Silencieux',
  'Silent Swordsman':             'Spadassin Silencieux',
  'Six Samurai':                  'Six Samouraïs',
  'Sky Striker':                  'Assaut de l\'Air',
  'Skull Servant':                'Serviteur Crâne',
  'Skyscraper':                   'Gratte-Ciel',
  'Slime':                        'Gélatine',
  'SPYRAL':                       'ESPION-AL',
  'Speedroid':                    'Speedroïd',
  'Spellbook':                    'Livre de Magie',
  'Spright':                      'Lutin',
  'Springans':                    'Springans',
  'Star Seraph':                  'Séraphin Étoile',
  'Stardust':                     'Poussière d\'Étoiles',
  'Starry Knight':                'Chevalier Étoilé',
  'Subterror':                    'Souterrain',
  'Sunavalon':                    'Sunavalone',
  'Superheavy Samurai':           'Samouraï Superpesant',
  'Supreme King':                 'Roi Suprême',
  'Swordsoul':                    'Âme-Épée',
  'Synchron':                     'Synchron',
  // T
  'T.G.':                         'T.G.',
  'Tellarknight':                 'Tellarchevalier',
  'Tenyi':                        'Tenyi',
  'The Agent':                    'Agent',
  'The Phantom Knights':          'Chevaliers Fantômes',
  'The Weather':                  'Le Temps',
  'The Winged Dragon of Ra':      'Le Dragon Ailé de Râ',
  'Thunder Dragon':               'Dragon du Tonnerre',
  'Tindangle':                    'Tindangle',
  'Toon':                         'Toon',
  'Tri-Brigade':                  'Tri-Brigade',
  'Troymare':                     'Cauchemar Troyen',
  'True Draco':                   'Vrai Draco',
  'True King':                    'Vrai Roi',
  'Twilightsworn':                'Porteur du Crépuscule',
  // U
  'U.A.':                         'U.A.',
  'Unchained':                    'Déchaîné',
  'Utopia':                       'Utopie',
  // V
  'V-HERO':                       'V-HÉROS',
  'Vampire':                      'Vampire',
  'Vehicroid':                    'Véhicroid',
  'Vendread':                     'Vendread',
  'Venom':                        'Venin',
  'Virtual World':                'Monde Virtuel',
  'Vision HERO':                  'Vision HÉROS',
  'Vylon':                        'Vylon',
  // W
  'Watt':                         'Électro-',
  'Winged Kuriboh':               'Kuriboh Ailé',
  'Witchcrafter':                 'Artisane des Sorcières',
  'Wind-Up':                      'Remontoir',
  'World Chalice':                'Calice du Monde',
  'World Legacy':                 'Héritage du Monde',
  // X
  'X-Saber':                      'X-Sabre',
  'Xtra HERO':                    'Xtra HÉROS',
  // Y
  'Yang Zing':                    'Yang Zing',
  'Yosenju':                      'Yosenju',
  'Yubel':                        'Yubel',
  // Z
  'Zefra':                        'Zefra',
  'Zombie':                       'Zombi',
  'Zombie World':                 'Monde Zombi',
  'Zoodiac':                      'Zodiarque',
};

function normArchetype(a) {
  if (!a) return '—';
  return ARCHETYPE_FR[a] ?? a;
}

// Fallback intelligent : retourne la traduction FR si dispo,
// sinon le nom anglais tel quel (le joueur FR connaît souvent le nom EN)
function normArchetype(a) {
  if (!a) return '—';
  return ARCHETYPE_FR[a] ?? a;
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
    archetype: normArchetype(raw.archetype),
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

// ── Nom affiché : FR si disponible, sinon EN ──────────────
// (le vrai nom anglais), car c'est ce que le joueur connaît
// quand la carte n'a pas de traduction officielle.
// Pour l'affichage dans la question on montre le nom FR.

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

  // ── Catégorie synthétique monstre / magie / piège
  const nMonsters = pool.filter(c => MONSTER_FRAMES.has(c.frameType)).length;
  const nSpells   = pool.filter(c => SPELL_FRAMES.has(c.frameType)).length;
  const nTraps    = pool.filter(c => TRAP_FRAMES.has(c.frameType)).length;
  if (nMonsters > 0 && (nSpells > 0 || nTraps > 0)) {
    qs.push({ label: "Est-ce un monstre ?", key: 'cat_monster', test: c => MONSTER_FRAMES.has(c.frameType), group: 'cardcat' });
  }
  if (nSpells > 0 && (nMonsters > 0 || nTraps > 0)) {
    qs.push({ label: "Est-ce une carte Magie ?", key: 'cat_spell', test: c => SPELL_FRAMES.has(c.frameType), group: 'cardcat' });
  }
  if (nTraps > 0 && (nMonsters > 0 || nSpells > 0)) {
    qs.push({ label: "Est-ce une carte Piège ?", key: 'cat_trap', test: c => TRAP_FRAMES.has(c.frameType), group: 'cardcat' });
  }

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

  // ── Archétype (has_archetype)
  if (hasArchPool > 0 && noArchPool > 0) {
    qs.push({
      label: `Est-ce que la carte appartient à un archétype ?`,
      key: 'has_archetype',
      test: c => c.archetype !== '—',
      group: 'has_archetype',
    });
  }

  // ── Archétypes : dichotomie par lettre puis nom exact si pool réduit
  if (archetypes.length > 0) {
    const archInRange = (c, a, z) => {
      const l = (c.archetype[0] || '').toUpperCase();
      return c.archetype !== '—' && l >= a && l <= z;
    };
    [
      { label: "L'archétype commence-t-il par A–M ?", key: 'arch_AM', test: c => archInRange(c,'A','M') },
      { label: "L'archétype commence-t-il par N–Z ?", key: 'arch_NZ', test: c => archInRange(c,'N','Z') },
    ].forEach(q => qs.push({ ...q, group: 'arch_alpha' }));
    [
      { label: "L'archétype commence-t-il par A–F ?", key: 'arch_AF', test: c => archInRange(c,'A','F') },
      { label: "L'archétype commence-t-il par G–M ?", key: 'arch_GM', test: c => archInRange(c,'G','M') },
      { label: "L'archétype commence-t-il par N–S ?", key: 'arch_NS', test: c => archInRange(c,'N','S') },
      { label: "L'archétype commence-t-il par T–Z ?", key: 'arch_TZ', test: c => archInRange(c,'T','Z') },
    ].forEach(q => qs.push({ ...q, group: 'arch_alpha2' }));
    if (pool.length <= 300) {
      const letters2 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').sort(() => Math.random() - 0.5);
      letters2.forEach(l => qs.push({
        label: `L'archétype commence-t-il par la lettre "${l}" ?`,
        key: 'arch_letter_' + l,
        test: c => c.archetype !== '—' && (c.archetype[0] || '').toUpperCase() === l,
        group: 'arch_letter',
      }));
    }
    if (archetypes.length <= 20) {
      archetypes.forEach(v => qs.push({
        label: `Est-ce une carte de l'archétype "${v}" ?`,
        key: 'arch_eq_' + v,
        test: c => c.archetype === v,
        group: 'archetype',
      }));
    }
  }

  // ── Banlist
  if (bans.length > 1) {
    bans.forEach(v => qs.push({
      label: `Est-ce que la carte est "${v}" sur la Banlist TCG ?`,
      key: 'ban_eq_' + v,
      test: c => c.ban === v,
      group: 'ban',
    }));
  }
  
  // ── Catégorie Extra Deck / Main Deck
  const EXTRA_DECK = new Set(['Fusion','Synchro','XYZ','Link']);
  const MAIN_DECK  = new Set(['Normal','Effet','Rituel','Pendule']);
  
  const nExtra = pool.filter(c => EXTRA_DECK.has(c.frameType)).length;
  const nMain  = pool.filter(c => MAIN_DECK.has(c.frameType)).length;
  
  if (nExtra > 0 && nMain > 0) {
    qs.push({
      label: "Est-ce un monstre de l'Extra Deck (Fusion, Synchro, Xyz ou Link) ?",
      key: 'cat_extra',
      test: c => EXTRA_DECK.has(c.frameType),
      group: 'deckzone',
    });
  }
  
  // ── Monstre Normal (sans effet) vs Effet
  const nNormal = pool.filter(c => c.frameType === 'Normal').length;
  const nEffet  = pool.filter(c => c.frameType === 'Effet').length;
  if (nNormal > 0 && nEffet > 0) {
    qs.push({
      label: "Est-ce un monstre Normal (sans effet, cadre jaune) ?",
      key: 'frame_normal',
      test: c => c.frameType === 'Normal',
      group: 'frameType',
    });
  }
  
  // ── Détail Extra Deck (seulement si pool déjà filtré Extra)
  ['Fusion','Synchro','XYZ','Link'].forEach(v => qs.push({
    label: `Est-ce une carte ${v} ?`,
    key: 'frameType_eq_' + v,
    test: c => c.frameType === v,
    group: 'frameType',
  }));
  
  
  // ── Rituel / Pendule
  ['Rituel','Pendule'].forEach(v => qs.push({
    label: `Est-ce une carte ${v} ?`,
    key: 'frameType_eq_' + v,
    test: c => c.frameType === v,
    group: 'frameType',
  }));  

  // ── Seuils ATK / DEF / Niveau
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

  // ── Niveau EXACT (pool réduit)
  if (hasLvl && pool.length <= 400) {
    [1,2,3,4,5,6,7,8,10,12].forEach(n => qs.push({
      label: `Est-ce que le Niveau / Rang est exactement ${n} ?`,
      key: 'lvl_eq_' + n,
      test: c => c.level === n,
      group: 'level_exact',
    }));
  }

  // ── ATK exact (pool très réduit)
  if (hasAtk && pool.length <= 120) {
    const atkVals = [...new Set(pool.map(c => c.atk).filter(v => v >= 0))];
    atkVals.forEach(v => qs.push({
      label: `Est-ce que l'ATK est exactement ${v} ?`,
      key: 'atk_eq_' + v,
      test: c => c.atk === v,
      group: 'atk_exact',
    }));
  }

  // ── ATK > DEF ?
  if (pool.some(c => c.atk >= 0 && c.def >= 0)) {
    qs.push({
      label: "Est-ce que l'ATK est supérieure à la DEF ?",
      key: 'atk_gt_def',
      test: c => c.atk >= 0 && c.def >= 0 && c.atk > c.def,
      group: 'atk_vs_def',
    });
  }

  // ── Questions sur le nom ──────────────────────────────
  // car c'est le nom que le joueur a en tête (anglais pour les cartes non traduites)
  // Mais on affiche aussi "(nom FR)" dans la question si différent.
  const NAME_POOL_THRESHOLD = 1500;

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
      // Mélange aleatoire pour varier l'ordre de proposition des lettres
      const letters1 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').sort(() => Math.random() - 0.5);
      letters1.forEach(l => qs.push({
        label: `Le nom commence-t-il par la lettre "${l}" ?`,
        key: 'name_letter_' + l,
        test: c => (c.name[0] || '').toUpperCase() === l,
        group: 'name_letter',
      }));
    }

    const wordCount = c => c.name.trim().split(/\s+/).length;
    [1, 2, 3, 4, 5].forEach(t => qs.push({
      label: `Le nom contient-il plus de ${t} mot${t > 1 ? 's' : ''} ?`,
      key: 'name_words_' + t,
      test: c => wordCount(c) > t,
      group: 'name_words',
    }));
  }

  if (pool.length > 6 && pool.length <= NAME_POOL_THRESHOLD) {
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
// FIX : suppression complète de MAX_CONSEC_ARCH et du blocage des archétypes
// Le moteur choisit toujours la meilleure question entropique sans restriction

function bestQuestion(pool, askedKeys, resolvedGroups) {
  const qs = buildQuestions(pool).filter(q =>
    !askedKeys.has(q.key) && !resolvedGroups.has(q.group)
  );

  // Score entropique + petit bruit aleatoire pour varier les parties
  const scoreQ = q => {
    const yes = pool.filter(q.test).length;
    const no  = pool.length - yes;
    if (yes === 0 || no === 0) return -1;
    const ratio = yes / pool.length;
    const base = 1 - Math.abs(ratio - 0.5) * 2;
    return base + (Math.random() * 0.08 - 0.04); // +/- 4% bruit
  };

  const PRIORITY = [
    'cardcat', 'deckzone', 'attribute', 'race', 'has_archetype',
    'arch_alpha', 'arch_alpha2', 'arch_letter', 'archetype',
    'atk_vs_def', 'name_alpha', 'name_alpha2', 'name_letter', 'name_words', 'name_word',
    'atk', 'def', 'level', 'level_exact', 'atk_exact', 'ban',
  ];

  // Seuil minimal : question doit eliminer au moins 10% du pool
  // sinon ignoree dans la passe prioritaire (tombera en fallback)
  const MIN_SCORE = 0.10;

  for (const grp of PRIORITY) {
    if (resolvedGroups.has(grp)) continue;
    const candidates = qs.filter(q => q.group === grp);
    if (candidates.length === 0) continue;
    let best = null, bestScore = -1;
    for (const q of candidates) {
      const s = scoreQ(q);
      if (s >= MIN_SCORE && s > bestScore) { bestScore = s; best = q; }
    }
    if (best) return best;
  }

  // Fallback global sans seuil minimum (on pose ce qu'on peut)
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

const GUESS_THRESHOLD = 1;

// ── INIT ──────────────────────────────────────────────────

function yugiInit() {
  yPool           = ALL_CARDS.slice();
  yAsked          = new Set();
  yResolved       = new Set();
  yHistory        = [];
  yHistory_states = [];
  yGuessIdx       = 0;
  yGameOver       = false;
  yCurQ           = null;
  yThinking       = false;
  yQCount         = 0;
  ySortedPool     = [];

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

  // Aucun candidat → vrai abandon
  if (yPool.length === 0) {
    showGiveUp();
    return;
  }

  // 🔥 Si très peu de cartes → on devine directement
  if (yPool.length <= 5) {
    enterGuessPhase();
    return;
  }

  // On cherche la meilleure question
  const q = bestQuestion(yPool, yAsked, yResolved);

  // 🔥 Plus de questions pertinentes → devinette
  if (!q) {
    enterGuessPhase();
    return;
  }

  // Sinon → question normale
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

// ── RETOUR ARRIÈRE ────────────────────────────────────────

function yugiUndo() {
  if (yHistory_states.length === 0 || yGameOver) return;

  const snap = yHistory_states.pop();
  yPool     = snap.pool;
  yAsked    = snap.asked;
  yResolved = snap.resolved;
  yHistory  = snap.history;
  yQCount   = snap.qCount;
  yCurQ     = snap.curQ;
  yGuessIdx = 0;
  yThinking = false;
  ySortedPool = [];

  renderHistory();
  updatePoolInfo();
  showQuestion(yCurQ);
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
  return pool;
}

function yugiAnswer(ans) {
  if (yThinking || yGameOver || !yCurQ) return;

  const q = yCurQ;

  // Sauvegarde état avant modification
  yHistory_states.push({
    pool:     yPool.slice(),
    asked:    new Set(yAsked),
    resolved: new Set(yResolved),
    history:  yHistory.slice(),
    qCount:   yQCount,
    curQ:     yCurQ,
  });

  yAsked.add(q.key);
  yQCount++;

  const newPool = applyAnswer(yPool, q, ans);
  yPool = newPool;

  if (ans === 'oui' && q.key.includes('_eq_')) {
    yResolved.add(q.group);
  }
  if (q.group === 'cardcat' && (ans === 'oui' || ans === 'non')) {
    yResolved.add('cardcat');
  }
  if (q.key === 'has_archetype') {
    yResolved.add('has_archetype');
    if (ans === 'non' || ans === 'plutot_non' || ans === 'ne_sais_pas') {
      yResolved.add('archetype');
      yResolved.add('arch_alpha');
      yResolved.add('arch_alpha2');
      yResolved.add('arch_letter');
    }
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
  // Tri : cartes avec stats en premier, puis alphabétique
  ySortedPool = yPool.slice().sort((a, b) => {
    const sa = (a.atk > 0 ? a.atk : 0) + (a.level > 0 ? a.level * 50 : 0);
    const sb = (b.atk > 0 ? b.atk : 0) + (b.level > 0 ? b.level * 50 : 0);
    if (sa !== sb) return sb - sa;
    return a.name.localeCompare(b.name, 'fr');
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
    yPool       = yPool.filter(c => c.name !== name);
    ySortedPool = ySortedPool.filter(c => c.name !== name);

    yHistory.push({ label: 'Est-ce ' + name + ' ?', ans: 'NON', pool: yPool.length });
    renderHistory();
    updatePoolInfo();

    yThinking = true;
    setUI('thinking');
    setTimeout(() => {
      // Jamais d'abandon : si plus de cartes dans ySortedPool mais yPool non vide,
      // relancer nextStep pour poser de nouvelles questions
      if (ySortedPool.length === 0) {
        if (yPool.length === 0) { showGiveUp(); return; }
        nextStep();
        return;
      }
      showGuessStep();
    }, 400);
  }
}

function showGiveUp() {
  // 🔥 NE JAMAIS abandonner s'il reste des cartes
  if (yPool.length > 0) {
    enterGuessPhase();
    return;
  }

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

  if (!won && yPool.length > 0 && yPool.length <= 20) {
    const extra = document.createElement('div');
    extra.style.cssText = 'font-family:"DM Sans",sans-serif;font-size:.78rem;color:var(--dim);margin-top:.5rem;font-style:italic;';
    extra.textContent = 'Candidats restants : ' + yPool.slice(0, 8).map(c => c.name).join(', ') + (yPool.length > 8 ? '…' : '');
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

  if (yHistory_states.length > 0) {
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
  if (el) {
    const n = yPool.length;
    el.textContent = n.toLocaleString('fr') + ' carte' + (n > 1 ? 's' : '') + ' restante' + (n > 1 ? 's' : '');
  }
}

function renderHistory() {
  const list = document.getElementById('yHist');
  if (!list) return;
  list.innerHTML = '';
  yHistory.forEach(h => {
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
