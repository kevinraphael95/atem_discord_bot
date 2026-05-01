let good = 0;
let bad = 0;
let streak = 0;
let isStaple = false;

let staplePool = [];
let randomPool = [];
let nextCardData = null;

const RANDOM_BUFFER = 6;
const frCache = new Map();

async function fetchWithTimeout(url) {
  const res = await fetch(url);
  return res.json();
}

async function loadStaplePool() {
  if (staplePool.length) return;
  const data = await fetchWithTimeout(
    'https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes'
  );
  staplePool = data.data || [];
}

async function fetchCardFR(name) {
  if (frCache.has(name)) return frCache.get(name);

  try {
    const data = await fetchWithTimeout(
      `https://db.ygoprodeck.com/api/v7/cardinfo.php?name=${encodeURIComponent(name)}&language=fr`
    );
    const card = data.data?.[0] || null;
    frCache.set(name, card);
    return card;
  } catch {
    frCache.set(name, null);
    return null;
  }
}

async function fillRandomBuffer() {
  const data = await fetchWithTimeout(
    'https://db.ygoprodeck.com/api/v7/cardinfo.php?num=10&offset=' +
    Math.floor(Math.random() * 5000) +
    '&language=fr'
  );
  randomPool.push(...(data.data || []));
}

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

async function prefetchNext() {
  const staple = Math.random() < 0.5;

  if (staple) {
    await loadStaplePool();
    const base = pick(staplePool);
    const fr = await fetchCardFR(base.name);

    nextCardData = {
      card: fr ? { ...base, name: fr.name, desc: fr.desc } : base,
      staple: true
    };
  } else {
    await fillRandomBuffer();
    nextCardData = { card: randomPool.shift(), staple: false };
  }
}

function renderHUD() {
  hGood.textContent = good;
  hBad.textContent = bad;
  hStreak.textContent = streak;
}

function show(msg, type) {
  const f = document.getElementById('sp-flash');
  f.className = 'sp-flash on ' + type;
  f.textContent = msg;
}

function display(card) {
  card_name.textContent = card.name;
  card_type.textContent = card.type;
  card_desc.textContent = card.desc;
}

async function nextCard() {
  if (!nextCardData) await prefetchNext();

  const { card, staple } = nextCardData;
  nextCardData = null;
  isStaple = staple;

  display(card);

  card_box.style.display = 'flex';
  guess_btns.style.display = 'flex';

  prefetchNext();
}

window.guess = function (val) {
  const correct = val === isStaple;

  if (correct) {
    good++; streak++;
    show("Bonne réponse", "ok");
  } else {
    bad++; streak = 0;
    show("Raté", "ko");
  }

  renderHUD();
  setTimeout(nextCard, 1000);
};

Promise.all([loadStaplePool(), fillRandomBuffer()]).then(nextCard);
