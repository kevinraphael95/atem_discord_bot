(function () {
  const pages = [
    { href: 'commandes.html',  label: 'Commandes' },
    { href: 'vaact.html',      label: 'VAACT' },
    { href: 'minijeux.html',   label: 'Mini-jeux' },
    { href: 'install.html',    label: 'Installation' },
  ];
  const themes = [
    { id: 'shinigami', label: 'Royaumes des Ombres', icon: '👤' },
    { id: 'quincy',    label: 'Dragon Blanc',        icon: '🐲' }
  ];

  // ── CALCUL DU PRÉFIXE ─────────────────────────────────
  // Détecte la profondeur dans l'arborescence et remonte si besoin
  const parts = location.pathname.split('/').filter(Boolean);
  // On cherche si on est dans un sous-dossier connu
  const SUB_DIRS = ['minijeux']; // ajoute ici d'autres sous-dossiers si besoin
  const inSub = parts.length >= 2 && SUB_DIRS.includes(parts[parts.length - 2]);
  const prefix = inSub ? '../' : '';

  const current = parts[parts.length - 1] || 'index.html';

  const savedTheme = localStorage.getItem('atem-theme') || 'shinigami';
  document.documentElement.setAttribute('data-theme', savedTheme);

  // Détection page active : on compare juste le nom de fichier
  function isActive(href) {
    const hrefFile = href.split('/').pop();
    return current === hrefFile || (current === '' && hrefFile === 'index.html');
  }

  const navLinks = pages.map(p => {
    const active = isActive(p.href) ? ' class="active"' : '';
    return `<li><a href="${prefix}${p.href}"${active}>${p.label}</a></li>`;
  }).join('\n    ');

  const drawerLinks = pages.map(p => {
    const active = isActive(p.href) ? ' class="active"' : '';
    return `<a href="${prefix}${p.href}"${active} onclick="closeNav()">${p.label}</a>`;
  }).join('\n  ');

  const themeOptions = themes.map(t =>
    `<button class="theme-opt" data-theme="${t.id}" title="${t.label}">${t.icon} ${t.label}</button>`
  ).join('');

  const drawerThemeOptions = themes.map(t =>
    `<button class="drawer-theme-opt" data-theme="${t.id}">${t.icon} ${t.label}</button>`
  ).join('');

  const activeTheme = themes.find(t => t.id === savedTheme) || themes[0];

  document.body.insertAdjacentHTML('afterbegin', `
<nav>
  <a class="nav-logo" href="${prefix}index.html">⚡ Atem <span>Bot</span></a>
  <ul class="nav-links">
    ${navLinks}
  </ul>
  <div class="nav-right">
    <div class="theme-switcher" id="themeSwitcher">
      <button class="theme-toggle" id="themeToggle">${activeTheme.icon} ${activeTheme.label}</button>
      <div class="theme-menu" id="themeMenu">
        <div class="theme-menu-title">Thème</div>
        ${themeOptions}
      </div>
    </div>
    <button class="ham" id="ham" onclick="toggleNav()"><span></span><span></span><span></span></button>
  </div>
</nav>
<div class="drawer" id="drawer">
  ${drawerLinks}
  <div class="drawer-theme-section">
    <div class="drawer-theme-label">Thème visuel</div>
    <div class="drawer-theme-btns">
      ${drawerThemeOptions}
    </div>
  </div>
</div>
`);

  document.getElementById('themeToggle').addEventListener('click', function (e) {
    e.stopPropagation();
    document.getElementById('themeMenu').classList.toggle('open');
  });

  function updateThemeButtons(themeId) {
    document.querySelectorAll('.theme-opt, .drawer-theme-opt').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === themeId);
    });
    const active = themes.find(t => t.id === themeId);
    if (active) {
      document.getElementById('themeToggle').textContent = `${active.icon} ${active.label}`;
    }
  }

  updateThemeButtons(savedTheme);

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-theme]');
    if (btn) {
      const t = btn.dataset.theme;
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('atem-theme', t);
      updateThemeButtons(t);
      document.getElementById('themeMenu').classList.remove('open');
    }
    if (!e.target.closest('#themeSwitcher')) {
      const m = document.getElementById('themeMenu');
      if (m) m.classList.remove('open');
    }
  });

  window.toggleNav = function () {
    document.getElementById('ham').classList.toggle('open');
    document.getElementById('drawer').classList.toggle('open');
  };
  window.closeNav = function () {
    document.getElementById('ham').classList.remove('open');
    document.getElementById('drawer').classList.remove('open');
  };
})();
