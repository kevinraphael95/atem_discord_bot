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

/* ───── RENDER CLEAN ───── */

async function renderDeck(name, saison, deck) {
  let html = `
    <h2 style="font-family:Shippori Mincho;color:var(--gold-lt)">${name}</h2>
    <p style="opacity:.7">${saison}</p>
    <div class="deck-grid">
  `;

  for (const lvl in deck) {
    html += `<div class="deck-card"><h3>${lvl}</h3>`;

    const content = deck[lvl];

    if (typeof content === "string") {
      html += `<p>${content}</p>`;
    } else {
      for (const card in content) {
        const url = content[card];

        html += `
          <div class="card-line">
            <span>${card}</span>
            <a href="${url}" target="_blank">Deck</a>
            <button onclick="addFav('${url}')">⭐</button>
          </div>
        `;

        const img = await getCardImage(card);
        if (img) html += `<img class="ygo-img" src="${img}">`;
      }
    }

    html += `</div>`;
  }

  html += `</div>`;
  display.innerHTML = html;
}

/* ───── FAVORIS ───── */

function addFav(url) {
  let favs = JSON.parse(localStorage.getItem("deckFavs") || "[]");

  if (favs.includes(url)) {
    favs = favs.filter(f => f !== url);
  } else {
    favs.push(url);
  }

  localStorage.setItem("deckFavs", JSON.stringify(favs));
}

/* ───── VIEW FAVORIS ───── */

document.getElementById("showFavs").onclick = () => {
  let favs = JSON.parse(localStorage.getItem("deckFavs") || "[]");

  let html = `<h2 style="color:var(--gold-lt)">⭐ Favoris</h2><div class="deck-grid">`;

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
