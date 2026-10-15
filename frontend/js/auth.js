/* ============================================
   ESTACIÓN DEL FUTURO G500 — NAVEGACIÓN
   ============================================
   Riel lateral con selector de rol y segundo nivel
   de píldoras. Se carga ANTES que cualquier otro
   script de página.
   ============================================ */

/* ════════════════════════════════════════════
   SIDEBAR — una sola fuente de verdad
   ════════════════════════════════════════════ */
const NAV = [
  { page: 'ejecutivo',     icon: 'layout-dashboard', label: 'Centro de mando',      href: 'ejecutivo.html' },
  {
    page: 'bombas', icon: 'fuel', label: 'Estación',
    href: 'bombas.html',
    sub: [
      { href: 'bombas.html',       page: 'bombas',       label: 'Vista del gerente', icon: 'fuel' },
      { href: 'despachador.html',  page: 'despachador',  label: 'Despachador',       icon: 'tablet-smartphone' },
      { href: 'mantenimiento.html', page: 'mantenimiento', label: 'Mantenimiento',   icon: 'wrench' },
    ],
  },
  { page: 'seguridad',  icon: 'shield-alert', label: 'Seguridad',  href: 'seguridad.html' },
  { page: 'energia',    icon: 'sun',          label: 'Energía',    href: 'energia.html' },
  { page: 'comercial',  icon: 'shopping-cart', label: 'Comercial', href: 'comercial.html' },
  { page: 'roles', icon: 'shield-check', label: 'Sistema',
    href: 'roadmap.html',
    sub: [
      { href: 'roadmap.html', page: 'roadmap', label: 'Hoja de ruta', icon: 'map' },
    ],
  },
];

/* Selector de rol — cambia qué se ve, no a dónde se navega. Persistido en
   sessionStorage porque es una preferencia de la sesión de turno, no de la
   cuenta. */
const ROLES = [
  { id: 'gerente',      label: 'Gerente' },
  { id: 'despachador',  label: 'Despachador' },
  { id: 'seguridad',    label: 'Seguridad' },
  { id: 'corporativo',  label: 'Corporativo' },
];

function rolActual() {
  return sessionStorage.getItem('g500Rol') || 'gerente';
}

function renderSelectorRol() {
  const slot = document.getElementById('rol-slot');
  if (!slot) return;
  const actual = rolActual();
  slot.innerHTML = `
    <select id="rol-select" class="filter-pill" style="cursor:pointer; -webkit-appearance:none; appearance:none; max-width:118px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
      ${ROLES.map((r) => `<option value="${r.id}" ${r.id === actual ? 'selected' : ''}>${r.label}</option>`).join('')}
    </select>`;
  document.getElementById('rol-select').addEventListener('change', (ev) => {
    sessionStorage.setItem('g500Rol', ev.target.value);
  });
}

/** Grupo al que pertenece la página activa, mirando también sus `sub`. */
function grupoActivo(pagina) {
  return NAV.find((g) =>
    g.page === pagina || (g.sub || []).some((s) => s.page === pagina)
  );
}

function renderSidebar() {
  const nav = document.getElementById('sidebar');
  if (!nav) return;

  const activa = document.body.dataset.page;
  const grupo = grupoActivo(activa);

  nav.innerHTML = `
    <div class="sidebar__avatar">
      <a href="index.html" class="avatar avatar--sm avatar--ce" data-tooltip="Estación del Futuro G500">
        <span class="ce-brand-badge">G5</span>
      </a>
    </div>
    <ul class="sidebar__nav">
      ${NAV.map((item) => {
        const clases = [
          'sidebar__icon',
          grupo && item.page === grupo.page ? 'sidebar__icon--active' : '',
        ].filter(Boolean).join(' ');
        return `<li>
          <a href="${item.href}" class="${clases}" data-tooltip="${item.label}">
            <i data-lucide="${item.icon}"></i>
          </a>
        </li>`;
      }).join('')}
    </ul>
  `;
}

/* Segundo nivel.

   El diseño aprobado ponía estas píldoras en la zona izquierda de la barra
   superior, pero las páginas de módulo no tienen barra superior: solo
   index.html la monta. Así que se insertan bajo el encabezado de la página,
   con el componente .subnav-bar que ya existía en layout.css sin usarse. */
function renderSubnav() {
  const activa = document.body.dataset.page;
  const grupo = grupoActivo(activa);
  if (!grupo || !grupo.sub) return;

  const ancla = document.querySelector('.mando-header');
  if (!ancla) return;

  const barra = document.createElement('nav');
  barra.className = 'subnav-bar';
  barra.setAttribute('aria-label', `Vistas de ${grupo.label}`);
  barra.innerHTML = grupo.sub.map((s) => `
    <a href="${s.href}"
       class="subnav-btn${s.page === activa ? ' subnav-btn--active' : ''}"
       ${s.page === activa ? 'aria-current="page"' : ''}>
      <i data-lucide="${s.icon}"></i><span>${s.label}</span>
    </a>`).join('');

  ancla.insertAdjacentElement('afterend', barra);
}


/* ════════════════════════════════════════════
   AUTH — Sin login requerido
   Acceso directo para todos los usuarios.
   ════════════════════════════════════════════ */

/* Auth gates removed — open access platform */


/* ════════════════════════════════════════════
   SELLO "ACTUALIZADO HACE X MIN" + CONECTIVIDAD
   Transversal a todas las páginas. La estación no
   siempre tiene enlace en vivo, así que el sello
   declara conectividad y frescura del dato, no solo
   el reloj.
   ════════════════════════════════════════════ */

function renderAuthPill() {
  const slot = document.getElementById('auth-slot');
  if (!slot) return;

  slot.innerHTML = `
    <div class="filter-pill" style="gap:8px; cursor:default;">
      <span id="conexion-dot" style="display:inline-block;width:7px;height:7px;background:var(--accent-cyan);border-radius:50%;box-shadow:0 0 6px var(--accent-cyan);" class="animate-pulse"></span>
      <span id="conexion-texto" style="font-size:0.78rem; font-weight:600; color:var(--text-heading);">Conectado</span>
      <span style="color:var(--text-muted);">·</span>
      <span id="sello-actualizado" style="font-size:0.78rem; color:var(--text-muted);">actualizado hace instantes</span>
    </div>
  `;
  G5.initSello('#sello-actualizado');
}


/* Barra superior común para las páginas de módulo (index.html monta la suya
   propia, con buscador). Trae marca, selector de rol y el sello de arriba. */
function renderTopbarModulo() {
  if (document.getElementById('filter-bar')) return;
  const header = document.createElement('header');
  header.className = 'filter-bar filter-bar--notch';
  header.id = 'filter-bar';
  header.innerHTML = `
    <div style="display:flex; align-items:center; gap:10px;">
      <a href="index.html" class="topbar-side" style="gap:10px;">
        <span class="ce-brand-badge ce-brand-badge--chip">G5</span>
        <span style="font-weight:700; color:var(--text-heading); font-size:0.95rem;">Estación del Futuro G500</span>
      </a>
      <div id="rol-slot"></div>
    </div>
    <div id="auth-slot"></div>
  `;
  document.body.prepend(header);
}


/* ════════════════════════════════════════════
   ARRANQUE COMÚN
   ════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  renderTopbarModulo();
  renderSidebar();
  renderSubnav();
  renderSelectorRol();
  renderAuthPill();
  // Restore sidebar scroll position and persist on scroll
  const nav = document.getElementById('sidebar');
  if (nav) {
    nav.addEventListener('scroll', () => {
      sessionStorage.setItem('sidebarScroll', nav.scrollTop);
    });
    const pos = sessionStorage.getItem('sidebarScroll');
    if (pos) nav.scrollTop = parseInt(pos, 10);
  }
  if (window.lucide) lucide.createIcons();
});
