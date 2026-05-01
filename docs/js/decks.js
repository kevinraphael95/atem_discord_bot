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

function initSaisons() {
  for (const saison in deckData) {
    const opt = document.createElement("option");
    opt.value = saison;
    opt.textContent = saison;
    saisonSelect.appendChild(opt);
  }
}

saisonSelect.addEventListener("change", () => {
  const saison = saisonSelect.value;

  duellisteSelect.innerHTML = `<option value="">👤 Choisir un duelliste</option>`;
  duellisteSelect.disabled = true;

  if (!saison) return;

  const duellistes = Object.keys(deckData[saison]);

  duellistes.forEach(d => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    duellisteSelect.appendChild(opt);
  });

  duellisteSelect.disabled = false;
});

duellisteSelect.addEventListener("change", () => {
  const saison = saisonSelect.value;
  const duelliste = duellisteSelect.value;

  if (!duelliste) return;

  const data = deckData[saison][duelliste];
  renderDeck(duelliste, saison, data.deck);
});

function renderDeck(name, saison, deck) {
  let html = `<h2>${name}</h2>`;
  html += `<p class="saison">Saison : ${saison}</p>`;

  if (typeof deck === "string") {
    html += `<p>${deck}</p>`;
  } else {
    for (const niveau in deck) {
      html += `<h3>${niveau}</h3>`;

      if (typeof deck[niveau] === "string") {
        html += `<p>${deck[niveau]}</p>`;
      } else {
        html += `<ul>`;
        for (const sub in deck[niveau]) {
          html += `<li><b>${sub}</b> : <a href="${deck[niveau][sub]}" target="_blank">Voir deck</a></li>`;
        }
        html += `</ul>`;
      }
    }
  }

  display.innerHTML = html;
}
