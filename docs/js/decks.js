let deckData = {};

fetch("data/deck_data.json")
  .then(res => res.text())
  .then(text => {
    deckData = JSON.parse(text);
  })
  .catch(err => console.error(err));

const input = document.getElementById("searchInput");
const suggestions = document.getElementById("suggestions");
const display = document.getElementById("deckDisplay");

/* ─────────────────────────────
   🔍 AUTOCOMPLETE
───────────────────────────── */

input.addEventListener("input", () => {
  const q = input.value.toLowerCase();
  suggestions.innerHTML = "";

  if (!q) return;

  let results = [];

  for (const saison in deckData) {
    for (const d in deckData[saison]) {
      if (d.toLowerCase().includes(q)) {
        results.push({ saison, duelliste: d });
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
   🎴 RENDER CARDS
───────────────────────────── */

function renderDeck(name, saison, deck) {
  let html = `
    <h2 class="deck-title">${name}</h2>
    <p class="deck-season">Saison : ${saison}</p>
    <div class="deck-grid">
  `;

  if (typeof deck === "string") {
    html += `<div class="deck-card"><p>${deck}</p></div>`;
  } else {
    for (const niveau in deck) {
      html += `<div class="deck-card"><h3>${niveau}</h3>`;

      const content = deck[niveau];

      if (typeof content === "string") {
        html += `<p>${content}</p>`;
      } else {
        for (const sub in content) {
          html += `
            <div class="card-line">
              <span>${sub}</span>
              <a href="${content[sub]}" target="_blank">Ouvrir</a>
              <button onclick="toggleFav('${content[sub]}')">⭐</button>
            </div>
          `;
        }
      }

      html += `</div>`;
    }
  }

  html += `</div>`;
  display.innerHTML = html;
}

/* ─────────────────────────────
   ⭐ FAVORIS (toggle)
───────────────────────────── */

function toggleFav(url) {
  let favs = JSON.parse(localStorage.getItem("deckFavs") || "[]");

  if (favs.includes(url)) {
    favs = favs.filter(f => f !== url);
  } else {
    favs.push(url);
  }

  localStorage.setItem("deckFavs", JSON.stringify(favs));
}

/* ─────────────────────────────
   ⭐ AFFICHER FAVORIS
───────────────────────────── */

document.getElementById("showFavs").onclick = () => {
  let favs = JSON.parse(localStorage.getItem("deckFavs") || "[]");

  let html = `<h2>⭐ Mes favoris</h2><div class="deck-grid">`;

  favs.forEach(url => {
    html += `
      <div class="deck-card">
        <a href="${url}" target="_blank">${url}</a>
      </div>
    `;
  });

  html += `</div>`;
  display.innerHTML = html;
};
