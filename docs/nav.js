/* ── NAV CENTRALISÉE — ATEM ──────────────────────────── */
(function () {
  const pages = [
    { href: 'index.html',     label: 'Accueil' },
    { href: 'commandes.html', label: 'Commandes' },
    { href: 'vaact.html',     label: 'VAACT' },
    { href: 'minijeux.html',  label: 'Mini-jeux' },
    { href: 'ygoguesser.html', label: 'YGO Guesser' },
    { href: 'install.html',   label: 'Installation' },
  ];

  const current = location.pathname.split('/').pop() || 'index.html';

  const navLinks = pages.map(p => {
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<li><a href="${p.href}"${active}>${p.label}</a></li>`;
  }).join('\n    ');

  const drawerLinks = pages.map(p => {
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<a href="${p.href}"${active} onclick="closeNav()">${p.label}</a>`;
  }).join('\n  ');

  document.body.insertAdjacentHTML('afterbegin', `
<nav>
  <a class="nav-logo" href="index.html">𓂀 ATEM</a>
  <ul class="nav-links">
    ${navLinks}
  </ul>
  <button class="ham" id="ham" onclick="toggleNav()"><span></span><span></span><span></span></button>
</nav>

<div class="drawer" id="drawer">
  ${drawerLinks}
</div>
`);

  window.toggleNav = function () {
    document.getElementById('ham').classList.toggle('open');
    document.getElementById('drawer').classList.toggle('open');
  };
  window.closeNav = function () {
    document.getElementById('ham').classList.remove('open');
    document.getElementById('drawer').classList.remove('open');
  };
})();
