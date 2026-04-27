// ── STATE ─────────────────────────────────────────────────
let hist = [], qCount = 0, gameOver = false, thinking = false;

// ── QUESTIONS ─────────────────────────────────────────────
// Arbre de questions statique (pas d'IA)
const QUESTIONS = [
  { q: "Est-ce un monstre ?", reason: "Type de carte fondamental." },
  { q: "Est-ce une carte Magie ?", reason: "Distingue Magie des Pièges." },
  { q: "Est-ce un monstre de Type Dragon ?", reason: "Type le plus iconique." },
  { q: "Est-ce un monstre de Niveau 7 ou plus (haut niveau) ?", reason: "Sépare les boss monsters." },
  { q: "Est-ce une carte appartenant à l'archétype des Yeux Bleus (Blue-Eyes) ?", reason: "Archétype très populaire." },
  { q: "Est-ce une Carte de Fusion ?", reason: "Mode d'invocation spécial." },
  { q: "Est-ce une Carte Synchro ?", reason: "Mode d'invocation introduit dans GX/5D's." },
  { q: "Est-ce une Carte Xyz ?", reason: "Mode d'invocation introduit dans Zexal." },
  { q: "Est-ce une Carte de Lien ?", reason: "Mode d'invocation récent." },
  { q: "Est-ce que la carte apparaît souvent dans l'anime (serie principale) ?", reason: "Popularité médiatique." },
  { q: "Est-ce un monstre de Type Guerrier ?", reason: "Type très répandu." },
  { q: "Est-ce que cette carte est interdite ou limitée sur la banlist officielle ?", reason: "Impact compétitif." },
  { q: "Est-ce que cette carte a un effet qui détruit d'autres cartes ?", reason: "Effet de destruction direct." },
  { q: "Est-ce que le nom de la carte contient un mot japonais ou japonisant ?", reason: "Origine du nom." },
  { q: "Est-ce que cette carte est un monstre de l'Attribut LUMIÈRE ou TÉNÈBRES ?", reason: "Attributs les plus communs." },
  { q: "Est-ce que cette carte peut s'invoquer depuis le Deck directement ?", reason: "Effet d'invocation spéciale depuis le Deck." },
  { q: "Est-ce que cette carte est associée au personnage Yugi Muto dans l'anime ?", reason: "Lien avec le protagoniste." },
  { q: "Est-ce que cette carte est une Carte Piège Continue ou à Contre ?", reason: "Sous-type de Piège." },
  { q: "Est-ce que cette carte est connue pour être utilisée dans des Decks compétitifs de haut niveau ?", reason: "Usage en tournoi." },
  { q: "Est-ce que cette carte a plus de 3000 ATK ?", reason: "Puissance offensive." },
];

// Pool de devinettes basiques (fallback non-IA)
const GUESSES = [
  "Magicien des Ténèbres (Dark Magician)",
  "Dragon Blanc aux Yeux Bleus (Blue-Eyes White Dragon)",
  "Exodia le Défendu",
  "Pot de Cupidité (Pot of Greed)",
  "Tour Sombre (Dark Hole)",
  "Dragon Stardust",
  "Numéro 39 : Utopia",
  "Chevalier Sincère (Buster Blader)",
  "Trappe Sans Fond (Bottomless Trap Hole)",
  "Revendication du Phénix (Monster Reborn)",
];

let qIndex = 0;
let guessIndex = 0;

const $ = id => document.getElementById(id);

// ── START ─────────────────────────────────────────────────
function startGame() {
  $('yStart').style.display = 'none';
  const g = $('yGame'); g.style.display = 'flex';
  showNextQuestion();
}

// ── ANSWER ───────────────────────────────────────────────
function answer(ans) {
  if (thinking || gameOver) return;
  const labels = { oui:'OUI', plutot_oui:'PLUTÔT OUI', plutot_non:'PLUTÔT NON', non:'NON', ne_sais_pas:'JE NE SAIS PAS' };
  const cls    = { oui:'yes', plutot_oui:'pyesbtn', plutot_non:'pnobtn', non:'no', ne_sais_pas:'idk' };
  const curQ   = $('yQtext').textContent;
  hist.push({ q: curQ, a: ans, lbl: labels[ans], cls: cls[ans] });
  addHist(curQ, labels[ans], cls[ans]);
  $('ySep').style.display = '';
  qCount++;

  // Tenter une devinette après 5 questions ou à intervalles de 5
  if (qCount >= 5 && qCount % 5 === 0 && guessIndex < GUESSES.length) {
    showGuess(GUESSES[guessIndex]);
    guessIndex++;
  } else {
    showNextQuestion();
  }
}

// ── QUESTION SUIVANTE ─────────────────────────────────────
function showNextQuestion() {
  if (qIndex >= QUESTIONS.length) {
    // Plus de questions : devinette forcée
    if (guessIndex < GUESSES.length) {
      showGuess(GUESSES[guessIndex++]);
    } else {
      showGiveUp();
    }
    return;
  }

  thinking = true;
  setAnswers('none');

  // Petit délai visuel pour simuler la "réflexion"
  setThinkingUI(true);
  setTimeout(() => {
    setThinkingUI(false);
    thinking = false;
    const entry = QUESTIONS[qIndex++];
    const conf  = Math.min(95, 5 + qCount * 5);
    showQuestion(entry.q, entry.reason, conf);
  }, 600);
}

// ── SHOW QUESTION ─────────────────────────────────────────
function showQuestion(q, reason, conf) {
  $('yQnum').textContent = `QUESTION ${qCount + 1}`;
  $('yQtext').textContent = q;
  const r = $('yQreason');
  if (reason) { r.textContent = reason; r.style.display = ''; } else r.style.display = 'none';
  updProg(qCount, conf);
  setAnswers('normal');
  animBubble();
}

// ── SHOW GUESS ────────────────────────────────────────────
function showGuess(card) {
  thinking = true;
  setThinkingUI(true);
  setTimeout(() => {
    setThinkingUI(false);
    thinking = false;
    const conf = Math.min(95, 50 + qCount * 3);
    $('yQnum').textContent = '🎯 MA DEVINETTE';
    $('yQtext').textContent = `Est-ce que tu penses à… ${card} ?`;
    $('yQreason').style.display = 'none';
    updProg(qCount, conf);
    setAnswers('guess', card);
    animBubble();
  }, 900);
}

// ── CONFIRM GUESS ─────────────────────────────────────────
function confirmGuess(ok, card) {
  if (ok) {
    $('yOrb').classList.add('found'); $('yOrb').textContent = '✨';
    setAnswers('none');
    const r = $('yResult');
    r.className = 'y-result on win';
    $('yRttl').textContent = `🃏 TROUVÉ EN ${qCount} QUESTION${qCount > 1 ? 'S' : ''}`;
    $('yRcard').textContent = card;
    $('yRdesc').textContent = `Le Yuginator a percé le voile et deviné votre carte. La sagesse du génie est sans limite…`;
    $('yRestart').classList.add('on');
    gameOver = true;
  } else {
    hist.push({ q: `Est-ce ${card} ?`, a: 'non', lbl: 'NON (mauvaise)', cls: 'no' });
    addHist(`Est-ce ${card} ?`, 'NON ❌', 'no');
    qCount++;
    if (qCount >= 20 || guessIndex >= GUESSES.length) {
      showGiveUp();
    } else {
      showNextQuestion();
    }
  }
}

function showGiveUp() {
  setAnswers('none'); gameOver = true;
  const r = $('yResult');
  r.className = 'y-result on def';
  $('yRttl').textContent = '☠ LE YUGINATOR S\'INCLINE';
  $('yRcard').textContent = '???';
  $('yRdesc').textContent = 'Votre carte a résisté à la sagesse du génie. Quelle était-elle ? Il apprendra de cette défaite…';
  $('yRestart').classList.add('on');
}

// ── HELPERS ───────────────────────────────────────────────
function setThinkingUI(on) {
  const orb = $('yOrb');
  if (on) {
    orb.classList.add('thinking'); orb.textContent = '⚡';
    $('yQnum').textContent = 'LE GÉNIE RÉFLÉCHIT…';
    $('yQtext').innerHTML = '<span class="y-dots"><span></span><span></span><span></span></span>';
    $('yQreason').style.display = 'none';
  } else {
    orb.classList.remove('thinking'); orb.textContent = '🔮';
  }
}

function setAnswers(mode, card) {
  const el = $('yAnswers');
  if (mode === 'none') { el.style.display = 'none'; return; }
  el.style.display = 'flex';
  if (mode === 'normal') {
    el.innerHTML = `
      <button class="y-btn yes"     onclick="answer('oui')">✅ OUI</button>
      <button class="y-btn pyesbtn" onclick="answer('plutot_oui')">🟡 PLUTÔT OUI</button>
      <button class="y-btn pnobtn"  onclick="answer('plutot_non')">🟠 PLUTÔT NON</button>
      <button class="y-btn no"      onclick="answer('non')">❌ NON</button>
      <button class="y-btn idk"     onclick="answer('ne_sais_pas')">🤷 JE NE SAIS PAS</button>`;
  } else if (mode === 'guess') {
    const safe = (card || '').replace(/'/g, "\\'");
    el.innerHTML = `
      <button class="y-btn yes" onclick="confirmGuess(true,'${safe}')">✅ OUI, C'EST ÇA !</button>
      <button class="y-btn no"  onclick="confirmGuess(false,'${safe}')">❌ NON, CE N'EST PAS ÇA</button>`;
  }
}

function updProg(q, conf) {
  const pct = Math.min(100, conf || 0);
  $('yProgFill').style.width = pct + '%';
  $('yProgLabel').textContent = `Question ${q + 1}`;
  $('yConf').textContent = `Conf. ${pct}%`;
}

function addHist(question, ans, cls) {
  const list = $('yHist');
  const item = document.createElement('div'); item.className = 'y-hi';
  item.innerHTML = `<span class="hq">${question}</span><span class="ha ${cls}">${ans}</span>`;
  list.prepend(item);
}

function animBubble() {
  const b = $('yBubble');
  b.style.animation = 'none'; b.offsetHeight; b.style.animation = '';
}

function restart() {
  hist = []; qCount = 0; gameOver = false; thinking = false;
  qIndex = 0; guessIndex = 0;
  $('yOrb').textContent = '🔮'; $('yOrb').className = 'y-orb';
  $('yHist').innerHTML = '';
  $('yResult').className = 'y-result';
  $('yRestart').classList.remove('on');
  $('yProgFill').style.width = '0%';
  $('yConf').textContent = 'Conf. 0%';
  $('ySep').style.display = 'none';
  $('yFlash').className = 'flash';
  showNextQuestion();
}
