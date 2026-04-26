window.addEventListener("load", () => {
  const intro = document.getElementById("intro");
  const sound = document.getElementById("summonSound");

  // 🔊 son invocation (optionnel)
  if (sound) {
    sound.volume = 0.6;
    sound.play().catch(() => {});
  }

  // ⏱ fin intro
  setTimeout(() => {
    intro.classList.add("hide");
  }, 2400);
});
