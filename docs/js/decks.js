let deckData = {};

fetch("data/deck_data.json")
  .then(res => res.text())
  .then(text => {
    deckData = JSON.parse(text);
    initSaisons();
  });

const saisonSelect = document.getElementById("saisonSelect");
const duellisteSelect = document.getElementById("duellisteSelect");
const display = document.getElementById("deckDisplay");

/* ─────────────────────────────
   📅 saisons
───────────────────────────── */

function initSaisons() {
  for (const s in deckData) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    saisonSelect.appendChild(opt);
  }
}

/* ─────────────────────────────
   👤 duellistes dropdown
───────────────────────────── */

saisonSelect.addEventListener("change", () => {
  const s = saisonSelect.value;

  duellisteSelect.innerHTML = `<option value="">Duelliste</option>`;
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

  const data = deckData[s][d];
  renderDeck(d, s, data.deck);
});

/* ─────────────────────────────
   🔍 SEARCH + AUTOCOMPLETE
───────────────────────────── */

const input = document.getElementById("searchInput");
const suggestions = document.getElementById("suggestions");

input.addEventListener("input", () => {
  const q = input.value.toLowerCase();
  suggestions.innerHTML = "";

  if (!q) return;

  let results = [];

  for (const s in deckData) {
    for (const d in deckData[s]) {
      if (d.toLowerCase().includes(q)) {
        results.push({ saison: s, duelliste: d });
      }
    }
  }

  results.slice(0, 6).forEach(r => {
    const div = document.createElement("div");
    div.className = "suggestion";
    div.textContent = `${r.duelliste} (${r.saison})`;

    div.onclick = () => {
      input.value = r.duelliste;
      suggestions.innerHTML = "";

      const data = deckData[r.saison][r.duelliste];
      renderDeck(r.duelliste, r.saison, data.deck);
    };

    suggestions.appendChild(div);
  });
});

/* ─────────────────────────────
   🎴 RENDER + YGO IMAGES
───────────────────────────── */

async function fetchCardImage(name) {
  try {
    const res = await fetch(`https://db.ygoprodeck.com/api/v7/cardinfo.php?name=${encodeURIComponent(name)}`);
    const data = await res.json();
    return data.data?.[0]?.card_images?.[0]?.image_url || null;
  } catch {
    return null;
  }
}

async function renderDeck(name, saison, deck) {
  let html = `
    <h2>${name}</h2>
    <p>Saison : ${saison}</p>
    <div class="deck-grid">
  `;

  if (typeof deck === "string") {
    html += `<div class="deck-card"><p>${deck}</p></div>`;
  } else {
    for (const lvl in deck) {
      html += `<div class="deck-card"><h3>${lvl}</h3>`;

      const content = deck[lvl];

      if (typeof content === "string") {
        html += `<p>${content}</p>`;
      } else {
        for (const sub in content) {

          const url = content[sub];

          html += `
            <div class="card-line">
              <span>${sub}</span>
              <a href="${url}" target="_blank">Deck</a>
              <button onclick="addFav('${url}')">⭐</button>
            </div>
          `;

          // 🧠 tentative image YGO (nom = sub)
          const img = await fetchCardImage(sub);

          if (img) {
            html += `<img class="ygo-card" src="${img}">`;
          }
        }
      }

      html += `</div>`;
    }
  }

  html += `</div>`;
  display.innerHTML = html;
}

/* ─────────────────────────────
   ⭐ FAVORIS
───────────────────────────── */

function addFav(url) {
  let favs = JSON.parse(localStorage.getItem("deckFavs") || "[]");

  if (!favs.includes(url)) favs.push(url);
  else favs = favs.filter(f => f !== url);

  localStorage.setItem("deckFavs", JSON.stringify(favs));
}
