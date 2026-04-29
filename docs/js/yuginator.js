// ══════════════════════════════════════════════════════════
//  YUGINATOR — Moteur Entropique Ultra-Optimisé v2.0
//  Zéro IA — Logique Pure — Compatible YGOPRODeck
// ══════════════════════════════════════════════════════════

// ── CONFIGURATION & CONSTANTES ────────────────────────────

const MONSTER_FRAMES = new Set(['Normal','Effet','Rituel','Fusion','Synchro','XYZ','Link','Pendule','Jeton','Skill']);
const SPELL_RACES = new Set(['Normal','Continu','Contre','Jeu rapide','Équipement','Terrain','Rituel']);
const ATK_THRESHOLDS = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500];
const LVL_THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12];

// ── NORMALISATION ─────────────────────────────────────────

function normFrame(f) {
    const map = {
        normal:'Normal', effect:'Effet', ritual:'Rituel', fusion:'Fusion', 
        synchro:'Synchro', xyz:'XYZ', link:'Link', spell:'Magie', trap:'Piège',
        token:'Jeton', skill:'Skill', normal_pendulum:'Pendule', 
        effect_pendulum:'Pendule', ritual_pendulum:'Pendule', 
        fusion_pendulum:'Pendule', synchro_pendulum:'Pendule', xyz_pendulum:'Pendule',
    };
    return map[(f || '').toLowerCase()] || f || '—';
}

function normRace(r) {
    const map = {
        'Spellcaster':'Magicien','Warrior':'Guerrier','Dragon':'Dragon','Beast':'Bête',
        'Beast-Warrior':'Bête-Guerrier','Winged Beast':'Bête Ailée','Fiend':'Démon',
        'Fairy':'Elfe','Insect':'Insecte','Dinosaur':'Dinosaure','Reptile':'Reptile',
        'Fish':'Poisson','Sea Serpent':'Serpent marin','Aqua':'Aqua','Pyro':'Pyro',
        'Thunder':'Tonnerre','Machine':'Machine','Rock':'Rocher','Plant':'Plante',
        'Zombie':'Zombi','Psychic':'Psychique','Divine-Beast':'Divinité',
        'Cyberse':'Cyberse','Wyrm':'Wyrm','Creator-God':'Dieu créateur',
        'Continuous':'Continu','Counter':'Contre','Quick-Play':'Jeu rapide','Equip':'Équipement','Field':'Terrain'
    };
    return map[r] || r || '—';
}

function normAttr(a) {
    const map = { 'DARK':'TÉNÈBRES','LIGHT':'LUMIÈRE','WATER':'EAU','FIRE':'FEU','EARTH':'TERRE','WIND':'VENT','DIVINE':'DIVIN' };
    return map[a] || a || '—';
}

function normalize(raw) {
    return {
        id: raw.id,
        name: raw.name, // Nom anglais
        nameFR: raw.name_fr || raw.name, // Nom français
        frameType: normFrame(raw.frameType),
        race: normRace(raw.race),
        attribute: normAttr(raw.attribute),
        level: raw.level ?? raw.linkval ?? 0,
        atk: raw.atk ?? -1,
        def: raw.def ?? -1,
        archetype: raw.archetype || '—',
        ban: raw.banlist_info?.ban_tcg || 'Autorisé',
        img: raw.card_images?.[0]?.image_url_small || ''
    };
}

// ── ÉTAT GLOBAL ───────────────────────────────────────────

let ALL_CARDS = [];
let yPool = [], yAsked = new Set(), yResolved = new Set(), yHistory = [], yHistory_states = [];
let yQCount = 0, yGameOver = false, yCurQ = null, yThinking = false, ySortedPool = [];

// ── CHARGEMENT ────────────────────────────────────────────

async function yugiLoadCards() {
    const bar = document.getElementById('yLoadBar');
    if (bar) { bar.style.display = 'flex'; bar.textContent = '⚡ Initialisation du Duel Disk...'; }
    try {
        const resp = await fetch('https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes&language=fr');
        const json = await resp.json();
        ALL_CARDS = json.data.map(normalize);
        if (bar) {
            bar.textContent = `✅ ${ALL_CARDS.length.toLocaleString('fr')} cartes chargées`;
            setTimeout(() => bar.style.display = 'none', 1200);
        }
        yugiInit();
    } catch(e) {
        if (bar) bar.textContent = '❌ Erreur de connexion à la base';
    }
}

// ── MOTEUR DE QUESTIONS (LOGIQUE ENTROPIQUE) ──────────────

function buildQuestions(pool) {
    const qs = [];
    const size = pool.length;

    // Helper : Calcule si une question est utile
    const pushQ = (label, key, test, group) => {
        const yes = pool.filter(test).length;
        if (yes > 0 && yes < size) {
            const ratio = yes / size;
            const entropy = 1 - Math.abs(ratio - 0.5) * 2; // 1.0 = parfait (50/50)
            qs.push({ label, key, test, group, entropy });
        }
    };

    // 1. Types de cartes
    pushQ("Est-ce un monstre ?", 'cat_m', c => MONSTER_FRAMES.has(c.frameType), 'cardcat');
    pushQ("Est-ce une carte Magie ?", 'cat_s', c => c.frameType === 'Magie', 'cardcat');
    pushQ("Est-ce une carte Piège ?", 'cat_t', c => c.frameType === 'Piège', 'cardcat');

    // 2. Propriétés (Attributs, Frames, Races)
    if (size > 1) {
        const attrs = [...new Set(pool.map(c => c.attribute))].filter(v => v !== '—');
        attrs.forEach(v => pushQ(`L'attribut est-il "${v}" ?`, `attr_${v}`, c => c.attribute === v, 'attribute'));

        const frames = [...new Set(pool.map(c => c.frameType))];
        frames.forEach(v => pushQ(`Est-ce une carte "${v}" ?`, `frame_${v}`, c => c.frameType === v, 'frameType'));

        const races = [...new Set(pool.map(c => c.race))].filter(v => v !== '—');
        races.forEach(v => pushQ(`Le type est-il "${v}" ?`, `race_${v}`, c => c.race === v, 'race'));
    }

    // 3. Stats & Niveau (Uniquement si pertinent)
    if (pool.some(c => c.atk >= 0)) {
        ATK_THRESHOLDS.forEach(t => pushQ(`L'ATK est-elle ≥ ${t} ?`, `atk_${t}`, c => c.atk >= t, 'atk'));
    }
    if (pool.some(c => c.level > 0)) {
        LVL_THRESHOLDS.forEach(t => pushQ(`Le Niveau/Rang est-il ≥ ${t} ?`, `lvl_${t}`, c => c.level >= t, 'level'));
    }

    // 4. Mots-clés (Si pool réduit pour optimiser le CPU)
    if (size <= 500) {
        const words = ['Dragon', 'Magicien', 'Guerrier', 'HÉROS', 'Yeux Bleus', 'Sombre', 'Lumière', 'Cyber'];
        words.forEach(w => pushQ(`Le nom contient-il "${w}" ?`, `word_${w}`, 
            c => c.nameFR.includes(w) || c.name.includes(w), 'name_word'));
    }

    return qs;
}

function bestQuestion(pool, askedKeys, resolvedGroups) {
    const candidates = buildQuestions(pool).filter(q => !askedKeys.has(q.key) && !resolvedGroups.has(q.group));
    if (candidates.length === 0) return null;
    // On trie par entropie descendante (les meilleures questions d'abord)
    return candidates.sort((a, b) => b.entropy - a.entropy)[0];
}

// ── RÉPONSES ET FILTRAGE ──────────────────────────────────

function yugiAnswer(ans) {
    if (yThinking || yGameOver || !yCurQ) return;

    // Sauvegarde pour le Undo
    yHistory_states.push({
        poolIDs: yPool.map(c => c.id),
        asked: new Set(yAsked),
        resolved: new Set(yResolved),
        history: [...yHistory],
        qCount: yQCount,
        curQ: yCurQ
    });

    const q = yCurQ;
    yAsked.add(q.key);
    yQCount++;

    if (ans === 'oui') yPool = yPool.filter(q.test);
    else if (ans === 'non') yPool = yPool.filter(c => !q.test(c));
    else if (ans === 'plutot_oui') {
        const yes = yPool.filter(q.test);
        const noSafe = yPool.filter(c => !q.test(c)).filter((_,i) => i % 10 === 0);
        yPool = [...yes, ...noSafe];
    } else if (ans === 'plutot_non') {
        const no = yPool.filter(c => !q.test(c));
        const yesSafe = yPool.filter(q.test).filter((_,i) => i % 10 === 0);
        yPool = [...no, ...yesSafe];
    }

    yHistory.push({ label: q.label, ans: ans.toUpperCase().replace('_', ' '), pool: yPool.length });
    renderHistory();
    updatePoolInfo();

    yThinking = true;
    setUI('thinking');
    setTimeout(nextStep, 500);
}

// ── PROGRESSION DU JEU ────────────────────────────────────

function nextStep() {
    yThinking = false;
    if (yPool.length <= 1) return enterGuessPhase();

    const q = bestQuestion(yPool, yAsked, yResolved);
    if (!q || yQCount >= 35) return enterGuessPhase();

    yCurQ = q;
    showQuestion(q);
}

function enterGuessPhase() {
    if (yPool.length === 0) return showResult(false);
    ySortedPool = [...yPool].sort((a, b) => (b.atk + b.level * 100) - (a.atk + a.level * 100));
    showGuessStep();
}

function showGuessStep() {
    if (ySortedPool.length === 0) return showResult(false);
    const card = ySortedPool[0];
    setUI('guess');
    document.getElementById('yQtext').innerHTML = `Est-ce que vous pensez à :<br><strong>${card.nameFR}</strong>`;
    document.getElementById('yAnswers').dataset.guessId = card.id;
    updateProgress(99);
}

function yugiConfirmGuess(ok) {
    const id = document.getElementById('yAnswers').dataset.guessId;
    const card = ALL_CARDS.find(c => c.id == id);
    if (ok) {
        yGameOver = true;
        showResult(true, card.nameFR, card.img);
    } else {
        yPool = yPool.filter(c => c.id != id);
        ySortedPool = ySortedPool.filter(c => c.id != id);
        yThinking = true;
        setUI('thinking');
        setTimeout(nextStep, 400);
    }
}

// ── FONCTIONS D'INTERFACE (UI) ────────────────────────────

function yugiInit() {
    yPool = [...ALL_CARDS];
    yAsked = new Set(); yResolved = new Set();
    yHistory = []; yHistory_states = [];
    yQCount = 0; yGameOver = false;
    document.getElementById('yResult').classList.remove('on');
    updatePoolInfo();
    nextStep();
}

function showQuestion(q) {
    setUI('question');
    document.getElementById('yQnum').textContent = `QUESTION ${yQCount + 1}`;
    document.getElementById('yQtext').textContent = q.label;
    updateProgress();
}

function updateProgress(force) {
    const pct = force || Math.round(Math.max(5, (1 - yPool.length / ALL_CARDS.length) * 100));
    document.getElementById('yConf').textContent = pct + '%';
    document.getElementById('yProgFill').style.width = pct + '%';
}

function setUI(mode) {
    const ans = document.getElementById('yAnswers');
    const orb = document.getElementById('yOrb');
    if (mode === 'thinking') {
        orb.classList.add('thinking');
        ans.style.display = 'none';
    } else {
        orb.classList.remove('thinking');
        ans.style.display = 'flex';
        if (mode === 'question') {
            ans.innerHTML = `
                <button class="y-btn yes" onclick="yugiAnswer('oui')">OUI</button>
                <button class="y-btn pyes" onclick="yugiAnswer('plutot_oui')">PROBABLE</button>
                <button class="y-btn no" onclick="yugiAnswer('non')">NON</button>
                <button class="y-btn idk" onclick="yugiAnswer('ne_sais_pas')">IDK</button>
                ${yHistory_states.length > 0 ? '<button class="y-btn undo" onclick="yugiUndo()">↩</button>' : ''}
            `;
        } else if (mode === 'guess') {
            ans.innerHTML = `
                <button class="y-btn yes" onclick="yugiConfirmGuess(true)">OUI !</button>
                <button class="y-btn no" onclick="yugiConfirmGuess(false)">NON</button>
            `;
        }
    }
}

function showResult(won, name, img) {
    const r = document.getElementById('yResult');
    r.classList.add('on', won ? 'win' : 'def');
    document.getElementById('yRttl').textContent = won ? "TROUVÉ !" : "ABANDON...";
    document.getElementById('yRcard').textContent = won ? name : "La carte était trop puissante.";
    const rimg = document.getElementById('yRimg');
    if (won && img) { rimg.src = img; rimg.style.display = 'block'; }
    document.getElementById('yRestart').classList.add('on');
}

function renderHistory() {
    const hist = document.getElementById('yHist');
    if (!hist) return;
    hist.innerHTML = yHistory.map(h => `
        <div class="y-hi">
            <span class="hq">${h.label}</span>
            <span class="ha">${h.ans}</span>
        </div>
    `).join('');
    hist.scrollTop = hist.scrollHeight;
}

function updatePoolInfo() {
    const el = document.getElementById('yPoolInfo');
    if (el) el.textContent = `${yPool.length.toLocaleString('fr')} cartes restantes`;
}

function yugiUndo() {
    if (yHistory_states.length === 0) return;
    const last = yHistory_states.pop();
    yPool = ALL_CARDS.filter(c => last.poolIDs.includes(c.id));
    yAsked = last.asked;
    yResolved = last.resolved;
    yHistory = last.history;
    yQCount = last.qCount;
    yCurQ = last.curQ;
    renderHistory();
    updatePoolInfo();
    showQuestion(yCurQ);
}

// ── BOOT ──────────────────────────────────────────────────
yugiLoadCards();
