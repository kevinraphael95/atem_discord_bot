// ══════════════════════════════════════════════════════════
//  YUGINATOR v2 — moteur entropique pur JS, zéro IA
//  Branché sur YGOPRODeck API v7 (misc=yes)
//  Nouveautés v2 :
//    • has_effect (monstre à vrai effet vs Normal de facto)
//    • tcg_date  → époque de sortie (tranches de 5 ans)
//    • formats   → Master Duel, Duel Links, Rush Duel, Speed Duel
//    • scale     → échelle Pendule
//    • linkval   → valeur de Lien exacte
//    • linkmarkers → marqueurs de Lien (Top, Bottom, Left…)
//    • card_prices → tranche de prix Cardmarket (€)
//    • nb_artworks → nombre d'artworks alternatifs
// ══════════════════════════════════════════════════════════

// ── SETS DE CLASSIFICATION ────────────────────────────────

const MONSTER_FRAMES = new Set(['Normal','Effet','Rituel','Fusion','Synchro','XYZ','Link','Pendule','Jeton','Skill']);
const SPELL_FRAMES   = new Set(['Magie']);
const TRAP_FRAMES    = new Set(['Piège']);
const EXTRA_DECK     = new Set(['Fusion','Synchro','XYZ','Link']);
const MAIN_DECK      = new Set(['Normal','Effet','Rituel','Pendule']);
const SPELL_RACES    = new Set(['Normal','Continu','Contre','Jeu rapide','Équipement','Terrain','Rituel']);

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

// ── Époque de sortie TCG ──────────────────────────────────
// Retourne une tranche de 5 ans ex. "2002-2006", ou '—' si inconnue.
function normEpoch(tcgDate) {
  if (!tcgDate) return '—';
  const year = parseInt(tcgDate.slice(0, 4), 10);
  if (isNaN(year)) return '—';
  const start = Math.floor((year - 2002) / 5) * 5 + 2002;
  return `${start}-${start + 4}`;
}

// Retourne l'année brute (pour questions "avant X")
function normYear(tcgDate) {
  if (!tcgDate) return null;
  const y = parseInt(tcgDate.slice(0, 4), 10);
  return isNaN(y) ? null : y;
}

// ── Prix Cardmarket → tranche ─────────────────────────────
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

// ── Formats ───────────────────────────────────────────────
// misc=yes retourne raw.misc[0].formats (tableau de strings)
// On le normalise en Set pour tester rapidement.
function normFormats(misc) {
  if (!misc || !misc[0] || !misc[0].formats) return new Set();
  return new Set(misc[0].formats.map(f => f.toLowerCase()));
}

// ── Marqueurs de Lien ─────────────────────────────────────
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

// ── NORMALIZE PRINCIPAL ───────────────────────────────────

function normalize(raw) {
  const misc    = raw.misc || [];
  const miscObj = misc[0] || {};
  const formats = normFormats(misc);

  return {
    // Champs de base
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

    // Échelle Pendule
    scale:       raw.scale ?? -1,

    // Marqueurs de Lien
    linkmarkers: normLinkMarkers(raw),

    // ── Nouvelles données misc=yes ────────────────────────
    // has_effect : 1 = vrai effet, 0 = Monstre Normal de facto
    hasEffect:   miscObj.has_effect ?? -1,

    // Époque / année de sortie TCG
    tcgYear:     normYear(miscObj.tcg_date),
    epoch:       normEpoch(miscObj.tcg_date),

    // Formats disponibles (Set de strings lowercase)
    formats,

    // Rarité Master Duel
    mdRarity:    miscObj.md_rarity || '—',

    // Popularité (vues totales sur le site)
    views:       miscObj.views ?? 0,

    // Prix Cardmarket → tranche
    priceTier:   normPriceTier(raw.card_prices),
    priceRaw:    raw.card_prices?.[0] ? parseFloat(raw.card_prices[0].cardmarket_price) || 0 : 0,

    // Nombre d'artworks alternatifs
    nbArtworks:  raw.card_images ? raw.card_images.length : 1,
  };
}

// ══════════════════════════════════════════════════════════
//  CHARGEMENT
// ══════════════════════════════════════════════════════════

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
    qs.push({ label:'Est-ce un monstre ?', key:'cat_monster', test:c=>MONSTER_FRAMES.has(c.frameType), group:'cardcat' });
  if (nSpells > 0 && (nMonsters > 0 || nTraps > 0))
    qs.push({ label:'Est-ce une carte Magie ?', key:'cat_spell', test:c=>SPELL_FRAMES.has(c.frameType), group:'cardcat' });
  if (nTraps > 0 && (nMonsters > 0 || nSpells > 0))
    qs.push({ label:'Est-ce une carte Piège ?', key:'cat_trap', test:c=>TRAP_FRAMES.has(c.frameType), group:'cardcat' });

  // ── 2. Extra Deck vs Main Deck ───────────────────────
  const nExtra = pool.filter(c => EXTRA_DECK.has(c.frameType)).length;
  const nMain  = pool.filter(c => MAIN_DECK.has(c.frameType)).length;
  if (nExtra > 0 && nMain > 0)
    qs.push({ label:"Est-ce un monstre de l'Extra Deck (Fusion, Synchro, Xyz ou Link) ?", key:'cat_extra', test:c=>EXTRA_DECK.has(c.frameType), group:'deckzone' });

  // ── 3. Monstre Normal (cadre jaune) vs Effet ─────────
  const nNormal = pool.filter(c => c.frameType === 'Normal').length;
  const nEffet  = pool.filter(c => c.frameType === 'Effet').length;
  if (nNormal > 0 && nEffet > 0)
    qs.push({ label:'Est-ce un monstre Normal (sans effet, cadre jaune) ?', key:'frame_normal', test:c=>c.frameType==='Normal', group:'frameType' });

  // ── 4. has_effect (différent du frameType Normal !) ──
  // Un monstre "Normal" selon l'API peut quand même avoir un effet de lore.
  // has_effect=1 signifie qu'il a un VRAI effet de jeu.
  const hasEffectCards = pool.filter(c => c.hasEffect === 1);
  const noEffectCards  = pool.filter(c => c.hasEffect === 0);
  if (hasEffectCards.length > 0 && noEffectCards.length > 0)
    qs.push({
      label: 'Est-ce que la carte possède un vrai effet de jeu (pas juste un texte de lore) ?',
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

  // ── 8. Archétype ─────────────────────────────────────
  if (hasArchPool > 0 && noArchPool > 0)
    qs.push({ label:'Est-ce que la carte appartient à un archétype ?', key:'has_archetype', test:c=>c.archetype!=='—', group:'has_archetype' });

  if (archetypes.length > 0) {
    const archInRange = (c, a, z) => { const l=(c.archetype[0]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase(); return c.archetype!=='—'&&l>=a&&l<=z; };
    [
      { label:"L'archétype commence-t-il par A–M ?", key:'arch_AM', test:c=>archInRange(c,'A','M') },
      { label:"L'archétype commence-t-il par N–Z ?", key:'arch_NZ', test:c=>archInRange(c,'N','Z') },
    ].forEach(q => qs.push({ ...q, group:'arch_alpha' }));
    [
      { label:"L'archétype commence-t-il par A–F ?", key:'arch_AF', test:c=>archInRange(c,'A','F') },
      { label:"L'archétype commence-t-il par G–M ?", key:'arch_GM', test:c=>archInRange(c,'G','M') },
      { label:"L'archétype commence-t-il par N–S ?", key:'arch_NS', test:c=>archInRange(c,'N','S') },
      { label:"L'archétype commence-t-il par T–Z ?", key:'arch_TZ', test:c=>archInRange(c,'T','Z') },
    ].forEach(q => qs.push({ ...q, group:'arch_alpha2' }));
    if (pool.length <= 300) {
      'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').sort(()=>Math.random()-0.5).forEach(l => qs.push({
        label: `L'archétype commence-t-il par la lettre "${l}" ?`,
        key: 'arch_letter_'+l,
        test: c => c.archetype!=='—'&&(c.archetype[0]||'').toUpperCase()===l,
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
      if (linkCards.some(c => c.linkval === n)) {
        qs.push({ label:`Est-ce un monstre Lien-${n} ?`, key:'linkval_eq_'+n, test:c=>c.linkval===n, group:'linkval' });
      }
    });
    // Seuil
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
  // Questions posées seulement si au moins 10% et 90% des cartes du pool les ont
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
    // Décennie exacte
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


// questions de merde    
/*

  // ── 16. Rarité Master Duel ────────────────────────────
  const mdRarities = [...new Set(pool.map(c=>c.mdRarity))].filter(v=>v&&v!=='—');
  if (mdRarities.length > 1) {
    ['UR','SR','R','N'].forEach(r => {
      if (mdRarities.includes(r))
        qs.push({
          label: `Est-ce que la carte est "${r}" (rarité) dans Master Duel ?`,
          key: 'mdrar_'+r,
          test: c => c.mdRarity===r,
          group: 'mdRarity',
        });
    });
    // Rareté ≥ SR
    qs.push({
      label: 'Est-ce que la carte est de rang SR ou UR dans Master Duel ?',
      key: 'mdrar_gte_SR',
      test: c => c.mdRarity==='SR'||c.mdRarity==='UR',
      group: 'mdRarity_tier',
    });
  }

  // ── 17. Prix Cardmarket (tranches) ───────────────────
  const priceTiers = [...new Set(pool.map(c=>c.priceTier))].filter(v=>v&&v!=='—');
  if (priceTiers.length > 1) {
    priceTiers.forEach(tier => qs.push({
      label: `Est-ce que la carte vaut "${tier}" sur Cardmarket ?`,
      key: 'price_tier_'+tier,
      test: c => c.priceTier===tier,
      group: 'priceTier',
    }));
    // Seuils numériques (plus discriminants)
    [0.5, 2, 10, 30].forEach(t => {
      const above = pool.filter(c=>c.priceRaw>t).length;
      if (above > 0 && above < pool.length)
        qs.push({
          label: `Est-ce que la carte coûte plus de ${t}€ sur Cardmarket ?`,
          key: 'price_gt_'+t,
          test: c => c.priceRaw > t,
          group: 'priceNum',
        });
    });
  }

  // ── 18. Nombre d'artworks alternatifs ────────────────
  const multiArt = pool.filter(c => c.nbArtworks > 1).length;
  const monoArt  = pool.filter(c => c.nbArtworks === 1).length;
  if (multiArt > 0 && monoArt > 0)
    qs.push({
      label: 'Est-ce que la carte possède plusieurs artworks officiels ?',
      key: 'multi_art',
      test: c => c.nbArtworks > 1,
      group: 'artworks',
    });

*/
// fin des questions de merde 


  // ── 19. Questions sur le nom (alphabétique + mots) ───
    const ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  
    // Génère des intervalles aléatoires de 7-10 lettres couvrant tout l'alphabet
    function randomIntervals() {
      const letters = [...ALPHA];
      const intervals = [];
      let i = 0;
      while (i < letters.length) {
        const size = 7 + Math.floor(Math.random() * 4); // 7 à 10
        const end = Math.min(i + size - 1, 25);
        intervals.push({ a: letters[i], z: letters[end] });
        i = end + 1;
      }
      return intervals;
    }
  
    const nameInRange = (c, a, z) => { const l = (c.name[0]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase(); return l >= a && l <= z; };
  
    // Intervalles larges fixes (A-M / N-Z)
    [
      { label:'Le nom commence-t-il par une lettre entre A et M ?', key:'name_AM', test:c=>nameInRange(c,'A','M') },
      { label:'Le nom commence-t-il par une lettre entre N et Z ?', key:'name_NZ', test:c=>nameInRange(c,'N','Z') },
    ].forEach(q=>qs.push({...q, group:'name_alpha'}));
  
    // Intervalles aléatoires de 7-10 lettres
    randomIntervals().forEach(({a, z}) => qs.push({
      label: `Le nom commence-t-il par une lettre entre ${a} et ${z} ?`,
      key: `name_range_${a}${z}`,
      test: c => nameInRange(c, a, z),
      group: `name_range_${a}${z}`,
    }));
  
    // Lettre exacte (1ère) si pool raisonnable
    if (pool.length <= 500) {
      ALPHA.sort(()=>Math.random()-0.5).forEach(l=>qs.push({
        label: `Le nom commence-t-il par la lettre "${l}" ?`,
        key: 'name_letter_'+l, test:c=>(c.name[0]||'').toUpperCase()===l, group:'name_letter',
      }));
    }
  
    // Deuxième lettre si pool encore grand
    if (pool.length <= 800) {
      // Intervalles aléatoires sur la 2ème lettre aussi
      const nameInRange2 = (c, a, z) => { const l = (c.name[1]||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase(); return l >= a && l <= z; };
      randomIntervals().forEach(({a, z}) => qs.push({
        label: `La deuxième lettre du nom est-elle entre ${a} et ${z} ?`,
        key: `name2_range_${a}${z}`,
        test: c => nameInRange2(c, a, z),
        group: `name2_range_${a}${z}`,
      }));
      if (pool.length <= 300) {
        ALPHA.sort(()=>Math.random()-0.5).forEach(l=>qs.push({
          label: `La deuxième lettre du nom est-elle "${l}" ?`,
          key: 'name_letter2_'+l, test:c=>(c.name[1]||'').toUpperCase()===l, group:'name_letter2',
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

// ── SCORE D'ENTROPIE ──────────────────────────────────────

function bestQuestion(pool, askedKeys, resolvedGroups) {
  const qs = buildQuestions(pool).filter(q =>
    !askedKeys.has(q.key) && !resolvedGroups.has(q.group)
  );

  const scoreQ = q => {
    const yes = pool.filter(q.test).length;
    const no  = pool.length - yes;
    if (yes===0||no===0) return -1;
    const ratio = yes/pool.length;
    const base = 1 - Math.abs(ratio-0.5)*2;
    return base + (Math.random()*0.08-0.04);
  };

  // Ordre de priorité des groupes
  const PRIORITY = [
      'cardcat', 'deckzone', 'has_effect', 'attribute', 'race',
      'has_archetype', 'arch_alpha', 'arch_alpha2', 'arch_letter', 'archetype',
      'frameType', 'format', 'epoch', 'epoch_decade', 'ban',
      'name_alpha', 'name_letter', 'name_letter2', 'name_words', 'name_word',
      'atk_vs_def', 'atk', 'def', 'level', 'level_exact', 'atk_exact',
      'linkval', 'linkval_gte', 'linkmarkers', 'scale', 'scale_exact',
    ];

  const MIN_SCORE = 0.10;

  for (const grp of PRIORITY) {
    if (resolvedGroups.has(grp)) continue;
    const candidates = qs.filter(q=>q.group===grp);
    if (candidates.length===0) continue;
    let best=null, bestScore=-1;
    for (const q of candidates) {
      const s=scoreQ(q);
      if (s>=MIN_SCORE&&s>bestScore) { bestScore=s; best=q; }
    }
    if (best) return best;
  }

  // Intervalles dynamiques (1ère et 2ème lettre)
    for (const prefix of ['name_range_', 'name2_range_']) {
      const candidates = qs.filter(q => q.group.startsWith(prefix));
      let best=null, bestScore=-1;
      for (const q of candidates) {
        const s=scoreQ(q);
        if (s>=MIN_SCORE&&s>bestScore) { bestScore=s; best=q; }
      }
      if (best) return best;
    }
  
    // Fallback global
    let best=null, bestScore=-1;
    for (const q of qs) {
      const s=scoreQ(q);
      if (s>bestScore) { bestScore=s; best=q; }
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
  nextStep();
}

function nextStep() {
  if (yGameOver) return;
  if (yPool.length===0) { showGiveUp(); return; }
  if (yPool.length<=3)  { enterGuessPhase(); return; }
  const q = bestQuestion(yPool, yAsked, yResolved);
  if (!q) { enterGuessPhase(); return; }
  yCurQ = q;
  showQuestion(q);
}


function showQuestion(q) {
  yThinking=false;
  setUI('question');
  document.getElementById('yQnum').textContent = 'QUESTION '+(yQCount+1);
  document.getElementById('yQtext').textContent = q.label;
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

function applyAnswer(pool, q, ans) {
  if (ans==='oui') { const f=pool.filter(q.test); return f.length>0?f:pool; }
  if (ans==='non') { const f=pool.filter(c=>!q.test(c)); return f.length>0?f:pool; }
  if (ans==='plutot_oui') {
    const yes=pool.filter(q.test), no=pool.filter(c=>!q.test(c));
    const kept=no.filter((_,i)=>i%7===0);
    const m=[...yes,...kept]; return m.length>0?m:pool;
  }
  if (ans==='plutot_non') {
    const yes=pool.filter(q.test), no=pool.filter(c=>!q.test(c));
    const kept=yes.filter((_,i)=>i%7===0);
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

  // Résolution de groupes
  if (ans==='oui'&&q.key.includes('_eq_')) yResolved.add(q.group);
  if (q.group==='cardcat' && ans==='oui') yResolved.add('cardcat');
  if (q.key==='has_archetype') {
    yResolved.add('has_archetype');
    if (ans==='non'||ans==='plutot_non'||ans==='ne_sais_pas') {
      yResolved.add('archetype'); yResolved.add('arch_alpha'); yResolved.add('arch_alpha2'); yResolved.add('arch_letter');
    }
  }
  // Si la carte n'est pas dans un format, inutile de redemander les autres formats
  if (q.group==='format'&&ans==='oui') yResolved.add('format');

  const ansLabel={oui:'OUI',non:'NON',plutot_oui:'~OUI',plutot_non:'~NON',ne_sais_pas:'?'};
  yHistory.push({label:q.label,ans:ansLabel[ans]||ans,pool:yPool.length});
  renderHistory(); updatePoolInfo();

  yThinking=true; setUI('thinking');
  setTimeout(()=>nextStep(),500);
}

function enterGuessPhase() {
  ySortedPool=yPool.slice().sort((a,b)=>{
    const sa=(a.atk>0?a.atk:0)+(a.level>0?a.level*50:0);
    const sb=(b.atk>0?b.atk:0)+(b.level>0?b.level*50:0);
    if (sa!==sb) return sb-sa;
    return a.name.localeCompare(b.name,'fr');
  });
  yGuessIdx=0; showGuessStep();
}

function showGuessStep() {
  if (yGuessIdx>=ySortedPool.length) { showGiveUp(); return; }
  const card=ySortedPool[yGuessIdx]; yGuessIdx++;
  setUI('guess');
  document.getElementById('yQnum').textContent='🎯 DEVINETTE '+yGuessIdx;
  document.getElementById('yQtext').textContent='Est-ce que vous pensez à… '+card.name+' ?';
  const pct=Math.min(99,65+yQCount*3);
  document.getElementById('yConf').textContent=pct+'%';
  document.getElementById('yProgFill').style.width=pct+'%';
  document.getElementById('yAnswers').dataset.guessCard=card.name;
  document.getElementById('yAnswers').dataset.guessImg=card.img||'';
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
  setTimeout(()=>{ if (ySortedPool.length===0) { if (yPool.length===0){showGiveUp();return;} nextStep(); return; } showGuessStep(); },400);
}

function showGiveUp() {
  if (yPool.length>0) { enterGuessPhase(); return; }
  yGameOver=true; setUI('none'); showResult(false,null,null);
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
