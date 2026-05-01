let good = 0, bad = 0, streak = 0;
let isStaple = false;

let staplePool = [];
let randomPool = [];
let nextCardData = null;

const RANDOM_BUFFER = 6;
const TOTAL_RANDOM = 10000;

const frCache = new Map();

async function fetchWithTimeout(url, ms = 8000) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    clearTimeout(id);
    return res.json();
  } catch (e) {
    clearTimeout(id);
    throw e;
  }
}

async function loadStaplePool() {
  if (staplePool.length) return;
  const data = await fetchWithTimeout(
    'https://db.ygoprodeck.com/api/v7/cardinfo.php?staple=yes'
  );
  staplePool = data.data || [];
}

async function fetchCardFR(nameEN) {
  if (frCache.has(nameEN)) return frCache.get(nameEN);
  try {
    const data = await fetchWithTimeout(
      `https://db.ygoprodeck.com/api/v7/cardinfo.php?name=${encodeURIComponent(nameEN)}&language=fr`
    );
    const card = data.data?.[0] || null;
    frCache.set(nameEN, card);
    return card;
  } catch {
    frCache.set(nameEN, null);
    return null;
  }
}

function renderHUD() {
  document.getElementById('hGood').textContent = good;
  document.getElementById('hBad').textContent = bad;
  document.getElementById('hStreak').textContent = streak;
}

function showFlash(type, msg) {
  const f = document.getElementById('sp-flash');
  f.className = 'sp-flash on ' + type;
  f.textContent = msg;
}

function guess(val) {
  document.getElementById('btn-staple').disabled = true;
  document.getElementById('btn-not').disabled = true;

  const correct = val === isStaple;

  if (correct) {
    good++; streak++;
    showFlash('ok', 'Bonne réponse');
  } else {
    bad++; streak = 0;
    showFlash('ko', 'Raté');
  }

  renderHUD();
  setTimeout(nextCard, 1000);
}

async function nextCard() {
  document.getElementById('card-box').style.display = 'none';
  document.getElementById('sp-load').style.display = 'block';

  if (!nextCardData) await prefetchNext();

  const { card, staple } = nextCardData;
  nextCardData = null;
  isStaple = staple;

  document.getElementById('card-name').textContent = card.name;
  document.getElementById('card-type').textContent = card.type;
  document.getElementById('card-desc').textContent = card.desc;

  const img = document.getElementById('card-thumb');
  img.src = card.card_images?.[0]?.image_url;

  document.getElementById('sp-load').style.display = 'none';
  document.getElementById('card-box').style.display = 'flex';

  prefetchNext();
}

async function prefetchNext() {
  const willBeStaple = Math.random() < 0.5;

  if (willBeStaple) {
    await loadStaplePool();
    const card = staplePool[Math.floor(Math.random() * staplePool.length)];
    nextCardData = { card, staple: true };
  } else {
    nextCardData = {
      card: {
        name: "Random",
        type: "",
        desc: "",
        card_images: [{ image_url: "" }]
      },
      staple: false
    };
  }
}

Promise.all([loadStaplePool()]).then(nextCard);
