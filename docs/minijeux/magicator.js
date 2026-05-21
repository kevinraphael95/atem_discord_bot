let allCards = [];
let possibleCards = [];

let currentQuestion = 0;

let history = [];

const questions = [

  {
    q: "La carte est-elle une créature ?",
    test: c => c.type_line?.includes("Creature")
  },

  {
    q: "La carte est-elle légendaire ?",
    test: c => c.type_line?.includes("Legendary")
  },

  {
    q: "La carte est-elle multicolore ?",
    test: c => c.colors && c.colors.length > 1
  },

  {
    q: "La carte est-elle noire ?",
    test: c => c.colors?.includes("B")
  },

  {
    q: "La carte est-elle bleue ?",
    test: c => c.colors?.includes("U")
  },

  {
    q: "La carte est-elle rouge ?",
    test: c => c.colors?.includes("R")
  },

  {
    q: "La carte est-elle verte ?",
    test: c => c.colors?.includes("G")
  },

  {
    q: "La carte est-elle blanche ?",
    test: c => c.colors?.includes("W")
  },

  {
    q: "La carte coûte-t-elle 5 manas ou plus ?",
    test: c => c.cmc >= 5
  },

  {
    q: "Est-ce un planeswalker ?",
    test: c => c.type_line?.includes("Planeswalker")
  },

  {
    q: "La carte est-elle un terrain ?",
    test: c => c.type_line?.includes("Land")
  },

  {
    q: "La carte est-elle un artefact ?",
    test: c => c.type_line?.includes("Artifact")
  },

  {
    q: "La carte est-elle mythique ?",
    test: c => c.rarity === "mythic"
  },

  {
    q: "La carte possède-t-elle du texte ?",
    test: c => c.oracle_text && c.oracle_text.length > 20
  }

];

async function magicLoadCards() {

  document.getElementById("yLoadBar").style.display = "block";

  try {

    const res = await fetch(
      "https://api.scryfall.com/cards/search?q=game:paper&unique=cards"
    );

    const data = await res.json();

    allCards = data.data.filter(c =>
      c.image_uris &&
      c.name &&
      c.type_line
    );

    possibleCards = [...allCards];

    document.getElementById("yLoadBar").style.display = "none";

    renderQuestion();

  } catch (err) {

    console.error(err);

    document.getElementById("yLoadBar").innerHTML =
      "Erreur lors du chargement des cartes.";

  }
}

function renderQuestion() {

  if (currentQuestion >= questions.length || possibleCards.length <= 1) {
    makeGuess();
    return;
  }

  const q = questions[currentQuestion];

  document.getElementById("yQnum").innerText =
    `QUESTION ${currentQuestion + 1}`;

  document.getElementById("yQtext").innerText = q.q;

  document.getElementById("yProgLabel").innerText =
    `Question ${currentQuestion + 1}`;

  document.getElementById("yProgFill").style.width =
    `${(currentQuestion / questions.length) * 100}%`;

  document.getElementById("yConf").innerText =
    `${possibleCards.length} cartes`;

  const answers = document.getElementById("yAnswers");

  answers.innerHTML = `
    <button class="y-btn yes" onclick="answer('yes')">Oui</button>
    <button class="y-btn no" onclick="answer('no')">Non</button>
    <button class="y-btn idk" onclick="answer('idk')">Je ne sais pas</button>
  `;
}

function magicAnswer(ans) {

  const q = questions[currentQuestion];

  history.push({
    question: q.q,
    answer: ans
  });

  if (ans !== "idk") {

    possibleCards = possibleCards.filter(card => {

      const result = q.test(card);

      return ans === "yes" ? result : !result;

    });
  }

  updateHistory();

  currentQuestion++;

  renderQuestion();
}

function updateHistory() {

  const hist = document.getElementById("yHist");

  hist.innerHTML = "";

  history.forEach(h => {

    hist.innerHTML += `
      <div class="y-hi">
        <div class="hq">${h.question}</div>
        <div class="ha">${h.answer}</div>
      </div>
    `;

  });
}

function makeGuess() {

  const guess =
    possibleCards[Math.floor(Math.random() * possibleCards.length)];

  const result = document.getElementById("yResult");

  result.classList.add("on");
  result.classList.add("win");

  document.getElementById("yRttl").innerText =
    "🧙 Le Magicator pense avoir trouvé !";

  document.getElementById("yRcard").innerText =
    guess.name;

  document.getElementById("yRdesc").innerText =
    guess.type_line;

  const img = document.getElementById("yRimg");

  if (guess.image_uris?.normal) {

    img.src = guess.image_uris.normal;
    img.style.display = "block";

  }

  document.getElementById("yRestart")
    .classList.add("on");

  document.getElementById("yAnswers")
    .style.display = "none";

  document.getElementById("yBubble")
    .style.display = "none";
}

function magicRestart() {

  possibleCards = [...allCards];

  currentQuestion = 0;

  history = [];

  document.getElementById("yResult")
    .className = "y-result";

  document.getElementById("yRestart")
    .classList.remove("on");

  document.getElementById("yAnswers")
    .style.display = "flex";

  document.getElementById("yBubble")
    .style.display = "block";

  document.getElementById("yHist").innerHTML = "";

  renderQuestion();
}
