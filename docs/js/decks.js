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

/* ───────────── INIT SAISONS ───────────── */

function initSaisons() {
  for (const s in deckData) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    saisonSelect.appendChild(opt);
  }
}

/* ───────────── DROPDOWNS ───────────── */

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

  renderDeck(d, s, deckData[s][d].deck);
});

/* ───────────── SEARCH ───────────── */

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
        results.push({ s, d });
      }
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

/* ───────────── YGO IMAGE API ───────────── */

async function getCardImage(name) {
  try {
    const res = await fetch(`https://db.ygoprodeck.com/api/v7/cardinfo.php?name=${encodeURIComponent(name)}`);
    const json = await res.json();
    return json.data?.[0]?.card_images?.[0]?.image_url || null;
  } catch {
    return null;
  }
}

/* ───────────── RENDER CARDS ───────────── */

async function renderDeck(name, saison, deck) {
  let html = `
    <h2>${name}</h2>
    <p>Saison : ${saison}</p>
    <div class="deck-grid">
  `;

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

        const img = await getCardImage(sub);
        if (img) {
          html += `<img class="ygo-img" src="${img}">`;
        }
      }
    }

    html += `</div>`;
  }

  html += `</div>`;
  display.innerHTML = html;
}

/* ───────────── FAVORIS ───────────── */

function addFav(url) {
  let favs = JSON.parse(localStorage.getItem("deckFavs") || "[]");

  if (favs.includes(url)) {
    favs = favs.filter(f => f !== url);
  } else {
    favs.push(url);
  }

  localStorage.setItem("deckFavs", JSON.stringify(favs));
}

/* ───────────── FAVORIS VIEW ───────────── */

document.getElementById("showFavs").onclick = () => {
  let favs = JSON.parse(localStorage.getItem("deckFavs") || "[]");

  let html = `<h2>⭐ Favoris</h2><div class="deck-grid">`;

  favs.forEach(f => {
    html += `
      <div class="deck-card">
        <a href="${f}" target="_blank">${f}</a>
      </div>
    `;
  });

  html += `</div>`;
  display.innerHTML = html;
};
