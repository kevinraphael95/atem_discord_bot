// ── CONFIGURATION ─────────────────────────────────────────
const COLS = [
    {k:'frameType', lb:'TYPE'},
    {k:'race',      lb:'RACE'},
    {k:'attribute', lb:'ATTR.'},
    {k:'level',     lb:'NIV.'},
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

// ── TRADUCTIONS (Optimisées) ──────────────────────────────
const MAPS = {
    frame: {
        normal:'Normal', effect:'Effet', ritual:'Rituel', fusion:'Fusion', synchro:'Synchro', xyz:'XYZ',
        link:'Link', spell:'Magie', trap:'Piège', token:'Jeton', skill:'Skill',
        normal_pendulum:'Pendule', effect_pendulum:'Pendule', ritual_pendulum:'Pendule', 
        fusion_pendulum:'Pendule', synchro_pendulum:'Pendule', xyz_pendulum:'Pendule'
    },
    race: {
        'Spellcaster':'Magicien','Warrior':'Guerrier','Dragon':'Dragon','Beast':'Bête',
        'Beast-Warrior':'Bête-Guerrier','Fiend':'Démon','Fairy':'Elfe','Insect':'Insecte',
        'Dinosaur':'Dinosaure','Reptile':'Reptile','Fish':'Poisson','Sea Serpent':'Serpent marin',
        'Aqua':'Aqua','Pyro':'Pyro','Thunder':'Tonnerre','Machine':'Machine','Rock':'Rocher',
        'Plant':'Plante','Zombie':'Zombi','Psychic':'Psychique','Divine-Beast':'Divinité',
        'Cyberse':'Cyberse','Wyrm':'Wyrm','Creator-God':'Dieu créateur','Normal':'Normal',
        'Continuous':'Continu','Counter':'Contre', 'Quick-Play':'Jeu rapide','Equip':'Équipement',
        'Field':'Terrain','Ritual':'Rituel'
    },
    attr: { 'DARK':'TÉNÈBRES','LIGHT':'LUMIÈRE','WATER':'EAU','FIRE':'FEU','EARTH':'TERRE','WIND':'VENT','DIVINE':'DIVIN' },
    ban: { 'Banned':'Interdit','Limited':'Limité','Semi-Limited':'Semi-Limité' }
};

const normFrame = f => MAPS.frame[(f || '').toLowerCase()] || f || '—';
const normRace = r => MAPS.race[r] || r || '—';
const normAttr = a => MAPS.attr[a] || a || '—';
const normBan = info => info?.ban_tcg ? (MAPS.ban[info.ban_tcg] || info.ban_tcg) : 'Autorisé';
const normFormat = misc => {
    const f = misc?.formats || [];
    return f.includes('tcg') ? 'TCG' : f.includes('ocg') ? 'OCG' : (f[0] || 'TCG').toUpperCase();
};

function normalize(raw) {
    return {
        id: raw.id,
        name: raw.name,
        frameType: normFrame(raw.frameType),
        race: normRace(raw.race),
        attribute: normAttr(raw.attribute),
        level: raw.level ?? raw.linkval ?? 0,
        atk: raw.atk ?? -1,
        def: raw.def ?? -1,
        archetype: raw.archetype || '—',
        ban: normBan(raw.banlist_info),
        format: normFormat(raw.misc_info?.[0]),
        img: raw.card_images?.[0]?.image_url_small || ''
    };
}

// ── CHARGEMENT ───────────────────────────────────────────
async function loadCards() {
    const bar = $('loadBar');
    bar.classList.remove('hidden');
    bar.textContent = '⏳ Initialisation...';

    try {
        const resp = await fetch('https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes&language=fr');
        if (!resp.ok) throw new Error(`Erreur HTTP ${resp.status}`);
        
        const json = await resp.json();
        const raw = json.data || [];
        const seen = new Set();
        
        for (let i = 0; i < raw.length; i++) {
            if (!seen.has(raw[i].id)) {
                seen.add(raw[i].id);
                CARDS.push(normalize(raw[i]));
            }
        }

        loaded = true;
        bar.textContent = `✅ ${CARDS.length.toLocaleString('fr')} cartes chargées !`;
        setTimeout(() => bar.classList.add('hidden'), 1500);
        
        $('gi').disabled = false;
        $('gbtn').disabled = false;
        $('gi').placeholder = "Entrez le nom d'une carte...";
        initGame();
    } catch(e) {
        bar.textContent = '❌ Erreur réseau. Rechargez la page.';
        console.error(e);
    }
}

// ── LOGIQUE DE JEU ────────────────────────────────────────
let mode = 'daily', tgt, dG = [], dOver = false, dSel = -1;
let sStr = 0, sBst = 0, sKil = 0, sQ = [], sQi = 0, sCur = null, sG = [], sSel = -1, sOver = false, sRec = 0;

const seededShuffle = (arr, seed) => {
    let a = [...arr], s = seed >>> 0;
    for (let i = a.length - 1; i > 0; i--) {
        s = Math.imul(s, 1664525) + 1013904223 >>> 0;
        let j = s % (i + 1);
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
};

const dayNum = () => Math.floor((new Date().setHours(0,0,0,0) - new Date('2025-01-01')) / 86400000);
const todayKey = () => new Date().toISOString().split('T')[0];

function cmp(m, t) {
    const diff = (a, b) => Math.abs((a < 0 ? 0 : a) - (b < 0 ? 0 : b));
    return [
        { v: m.frameType, s: m.frameType === t.frameType ? 'correct' : 'wrong' },
        { v: m.race,      s: m.race === t.race ? 'correct' : 'wrong' },
        { v: m.attribute, s: m.attribute === t.attribute ? 'correct' : 'wrong' },
        { v: m.level || '—', s: m.level === t.level ? 'correct' : Math.abs(m.level-t.level) <= 1 ? 'close' : 'wrong', a: m.level < t.level ? '▲' : m.level > t.level ? '▼' : '' },
        { v: m.atk < 0 ? '—' : m.atk, s: m.atk === t.atk ? 'correct' : diff(m.atk, t.atk) <= 500 ? 'close' : 'wrong', a: m.atk < t.atk ? '▲' : m.atk > t.atk ? '▼' : '' },
        { v: m.def < 0 ? '—' : m.def, s: m.def === t.def ? 'correct' : diff(m.def, t.def) <= 500 ? 'close' : 'wrong', a: m.def < t.def ? '▲' : m.def > t.def ? '▼' : '' },
        { v: m.archetype, s: m.archetype === t.archetype ? 'correct' : 'wrong' },
        { v: m.ban,       s: m.ban === t.ban ? 'correct' : 'wrong' },
        { v: m.format,    s: m.format === t.format ? 'correct' : 'wrong' }
    ];
}

// ── RENDU ─────────────────────────────────────────────────
function mkRow(m, f, tgt) {
    const row = document.createElement('div');
    row.className = 'row';
    const cells = f.map(x => `<div class="cell ${x.s}">${x.v}${x.a ? `<span style="font-size:7px;margin-left:2px">${x.a}</span>` : ''}</div>`).join('');
    row.innerHTML = `<div class="cell ${m.name === tgt.name ? 'correct' : 'wrong'}">${m.name}</div>${cells}`;
    $('gr').prepend(row);
}

function mkCard(m, f, tgt) {
    const isWin = m.name === tgt.name;
    const card = document.createElement('div');
    card.className = `card ${isWin ? 'ok' : 'ko'}`;
    
    let grid = f.map((x, i) => `
        <div class="cc ${x.s}">
            <div class="cl">${COLS[i].lb}</div>
            <div class="cv">${x.v}${x.a ? `<span style="font-size:.5rem;opacity:.8"> ${x.a}</span>` : ''}</div>
        </div>`).join('');

    card.innerHTML = `
        <div class="ctop">
            <div class="cname ${isWin ? 'correct' : 'wrong'}">${m.name}</div>
            <div class="cbadge">${m.frameType}<br>${m.attribute !== '—' ? m.attribute : m.race}</div>
        </div>
        <div class="cgrid">${grid}</div>`;
    $('gc').prepend(card);
}

// ── ACTIONS & UI ──────────────────────────────────────────
function sub() {
    const inp = $('gi');
    const val = inp.value.trim().toLowerCase();
    if (!val || !loaded || (mode === 'daily' ? dOver : sOver)) return;

    const card = CARDS.find(c => c.name.toLowerCase() === val);
    if (!card) return shake(inp, 'Carte introuvable...');
    
    const guesses = mode === 'daily' ? dG : sG;
    if (guesses.some(g => g.m.name === card.name)) return shake(inp, 'Déjà essayée !');

    const result = cmp(card, mode === 'daily' ? tgt : sCur);
    guesses.push({ m: card, f: result });
    
    mkRow(card, result, mode === 'daily' ? tgt : sCur);
    mkCard(card, result, mode === 'daily' ? tgt : sCur);
    
    inp.value = '';
    $('acl').innerHTML = '';
    
    if (mode === 'daily') {
        updDots();
        const won = card.name === tgt.name;
        if (won || dG.length >= MAX) { dOver = true; setTimeout(() => showDRes(won), 400); }
        saveD(won);
    } else {
        updSUI();
        if (card.name === sCur.name) sCorrect();
        else if (sG.length >= MAX) sGameOver(sCur.name);
    }
}

function onIn() {
    const v = $('gi').value.toLowerCase().trim();
    const l = $('acl'); l.innerHTML = '';
    if (!v || !loaded) return;

    const guesses = mode === 'daily' ? dG : sG;
    const done = new Set(guesses.map(g => g.m.name));
    
    // Filtrage optimisé
    let res = [];
    for (let i = 0; i < CARDS.length && res.length < 10; i++) {
        if (CARDS[i].name.toLowerCase().includes(v) && !done.has(CARDS[i].name)) {
            res.push(CARDS[i]);
        }
    }

    res.forEach(c => {
        const div = document.createElement('div');
        div.className = 'aci';
        div.innerHTML = `${c.name}<span class="acb">${c.frameType} · ${c.attribute !== '—' ? c.attribute : c.race}</span>`;
        div.onclick = () => { $('gi').value = c.name; l.innerHTML = ''; sub(); };
        l.appendChild(div);
    });
}

function shake(inp, msg) {
    inp.style.borderColor = 'var(--ko-bd)';
    inp.placeholder = msg;
    inp.animate([{transform:'translateX(-4px)'},{transform:'translateX(4px)'},{transform:'translateX(0)'}], 240);
    setTimeout(() => { inp.style.borderColor = ''; inp.placeholder = "Entrez le nom d'une carte..."; }, 1500);
}

// ── INITIALISATION ────────────────────────────────────────
const initGame = () => {
    tgt = seededShuffle(CARDS, dayNum() ^ 0xA7E)[dayNum() % CARDS.length];
    loadD();
    loadRec();
    if (!dOver) $('gi').focus();
};

document.addEventListener('keydown', e => {
    if (e.key === 'Enter') sub();
    if (e.key === 'Escape') $('acl').innerHTML = '';
});

loadCards();
