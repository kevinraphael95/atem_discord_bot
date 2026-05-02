let deckData = {};

fetch("data/deck_data.json")
  .then(res => res.json())
  .then(data => {
    deckData = data;
    initSaisons();
  });

const saisonSelect = document.getElementById("saisonSelect");
const duellisteSelect = document.getElementById("duellisteSelect");
const display = document.getElementById("deckDisplay");

/* ───── SAISONS ───── */

function initSaisons() {
  Object.keys(deckData).forEach(s => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    saisonSelect.appendChild(opt);
  });
}

/* ───── DROPDOWNS ───── */

saisonSelect.addEventListener("change", () => {
  const s = saisonSelect.value;

  duellisteSelect.innerHTML = `<option value="">👤 Duelliste</option>`;
  duellisteSelect.disabled = true;

  if (!s) return;

  Object.keys(deckData[s]).forEach(d => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    duellisteSelect.appendChild(opt);
  });

  duellisteSelect.disabled = false;
});

duellisteSelect.addEventListener("change", () => {
  const s = saisonSelect.value;
  const d = duellisteSelect.value;
  if (!d) return;
  renderDeck(d, s, deckData[s][d].deck);
});

/* ───── SEARCH ───── */

const input = document.getElementById("searchInput");
const suggestions = document.getElementById("suggestions");

input.addEventListener("input", () => {
  const q = input.value.toLowerCase();
  suggestions.innerHTML = "";
  if (!q) return;

  let results = [];
  for (const s in deckData) {
    for (const d in deckData[s]) {
      if (d.toLowerCase().includes(q)) results.push({ s, d });
    }
  }

  results.slice(0, 6).forEach(r => {
    const div = document.createElement("div");
    div.className = "suggestion";
    div.textContent = `${r.d} (${r.s})`;
    div.onclick = () => {
      input.value = r.d;
      suggestions.innerHTML = "";
      renderDeck(r.d, r.s, deckData[r.s][r.d].deck);
    };
    suggestions.appendChild(div);
  });
});

/* ───── IMAGE API ───── */

async function getCardImage(name) {
  try {
    const res = await fetch(`https://db.ygoprodeck.com/api/v7/cardinfo.php?name=${encodeURIComponent(name)}`);
    const json = await res.json();
    return json.data?.[0]?.card_images?.[0]?.image_url || null;
  } catch {
    return null;
  }
}

/* ───── RENDER ───── */

function renderDeck(name, saison, deck) {
  let html = `
    <h2 class="deck-title">${name}</h2>
    <p class="deck-saison">${saison}</p>
  `;

  for (const lvl in deck) {
    const content = deck[lvl];

    html += `<div class="deck-section">`;
    html += `<div class="deck-section-label">${lvl}</div>`;

    if (typeof content === "string") {
      html += `<p>${content}</p>`;
    } else {
      html += `<div class="deck-btn-row">`;
      for (const label in content) {
        const url = content[label];
        html += `<a class="deck-btn" href="${url}" target="_blank">${label}</a>`;
      }
      html += `</div>`;
    }

    html += `</div>`;
  }

  display.innerHTML = html;
}
