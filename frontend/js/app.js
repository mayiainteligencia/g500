/* ============================================
   ESTACIÓN DEL FUTURO G500 — APP.JS
   ============================================
   Utilidades compartidas por todas las páginas:
   namespace G5 (sello de frescura, contraste del
   hero) y animaciones de scroll.
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  initScrollAnimations();
});

function initScrollAnimations() {
  const fadeElements = document.querySelectorAll('.fade-in');
  if (!fadeElements.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
  );

  fadeElements.forEach((el) => observer.observe(el));
}

/* ════════════════════════════════════════════
   G5 — NAMESPACE GLOBAL
   ════════════════════════════════════════════ */

window.G5 = window.G5 || {

  /* ── Sello "actualizado hace X min" ──
     Cada página fija su propio instante de corte la primera vez que carga
     (sessionStorage, por pestaña) y el sello cuenta desde ahí. Sin fecha de
     referencia inventada: es "desde que abriste esto", no un dato de negocio. */
  initSello(selector) {
    const el = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (!el) return;

    const clave = 'g500Corte:' + (document.body.dataset.page || 'app');
    let corte = Number(sessionStorage.getItem(clave));
    if (!corte) {
      corte = Date.now();
      sessionStorage.setItem(clave, String(corte));
    }

    const pintar = () => {
      const min = Math.floor((Date.now() - corte) / 60000);
      el.textContent = min < 1 ? 'actualizado hace instantes'
        : min === 1 ? 'actualizado hace 1 min'
        : `actualizado hace ${min} min`;
    };
    pintar();
    setInterval(pintar, 15000);
  },
};


/* ════════════════════════════════════════════
   TOASTS DE DECISIÓN
   G5.toast({ sev, icon, tag, title, text, acciones, ms })
   sev: critica | alta | media | info | ok.
   Las críticas no se cierran solas. Cada acción puede
   encadenar otro toast (`luego`) que confirma lo que se
   hizo. Alertas de demostración: datos ilustrativos.
   ════════════════════════════════════════════ */

const NOTIF_KEY = 'g500Notifs';
G5.notifs = (() => { try { return JSON.parse(sessionStorage.getItem(NOTIF_KEY)) || []; } catch { return []; } })();
G5.guardarNotifs = () => {
  G5.notifs = G5.notifs.slice(0, 40);
  try { sessionStorage.setItem(NOTIF_KEY, JSON.stringify(G5.notifs)); } catch {}
  G5.pintarCampana && G5.pintarCampana();
};

/* Apila las tarjetas: la más nueva al frente (--i = 0), el resto detrás.
   Al pasar el mouse se despliegan hacia arriba con su altura real (--off). */
G5.apilar = (stack) => {
  const vivos = [...stack.children].filter((t) => !t.classList.contains('toast--out')).reverse();
  let off = 0;
  vivos.forEach((t, i) => {
    t.style.setProperty('--i', i);
    t.style.setProperty('--off', off + 'px');
    off += t.offsetHeight + 10;
  });
};

G5.toast = function (o, desdePanel) {
  if (!desdePanel) {
    G5.notifs.unshift({ ...o, id: Date.now() + Math.random(), t: Date.now(), leida: false });
    G5.guardarNotifs();
  }
  let stack = document.getElementById('toast-stack');
  if (!stack) {
    stack = document.createElement('div');
    stack.id = 'toast-stack';
    stack.className = 'toast-stack';
    stack.setAttribute('role', 'region');
    stack.setAttribute('aria-live', 'polite');
    stack.setAttribute('aria-label', 'Alertas');
    document.body.appendChild(stack);
  }
  while (stack.children.length >= 5) stack.firstElementChild.remove();

  const sev = o.sev || 'info';
  const ms = o.ms ?? (sev === 'critica' ? 0 : 14000);
  const el = document.createElement('div');
  el.className = `toast toast--${sev}`;
  if (sev === 'critica') el.setAttribute('role', 'alert');
  el.innerHTML = `
    <span class="toast__icon"><i data-lucide="${o.icon || 'bell'}"></i></span>
    <div class="toast__body">
      <span class="toast__tag">${o.tag || ''}</span>
      <span class="toast__title">${o.title}</span>
      <span class="toast__text">${o.text || ''}</span>
    </div>
    <button class="toast__close" aria-label="Cerrar"><i data-lucide="x"></i></button>
    <div class="toast__actions"></div>
    ${ms ? `<div class="toast__bar" style="animation-duration:${ms}ms"></div>` : ''}`;

  const cerrar = () => {
    el.classList.add('toast--out');
    G5.apilar(stack);
    setTimeout(() => el.remove(), 300);
  };
  el.querySelector('.toast__close').onclick = cerrar;

  const acciones = el.querySelector('.toast__actions');
  (o.acciones || []).forEach((a) => {
    const b = document.createElement('button');
    b.className = 'toast__btn' + (a.ghost ? ' toast__btn--ghost' : '');
    b.textContent = a.label;
    b.onclick = () => { cerrar(); if (a.luego) G5.toast(a.luego); };
    acciones.appendChild(b);
  });
  if (!acciones.children.length) acciones.remove();

  stack.appendChild(el);
  G5.apilar(stack);
  if (window.lucide) lucide.createIcons({ nameAttr: 'data-lucide', root: el });
  if (ms) setTimeout(cerrar, ms);
};

const DESCARTAR = { label: 'Descartar', ghost: true };

/* `global` = aparece en cualquier página; si no, solo en las de `paginas`. */
const ALERTAS_DEMO = [
  {
    global: true, espera: 5000,
    sev: 'critica', icon: 'siren', tag: 'Seguridad · CAM-02 · Isla 11-12',
    title: 'Asalto detectado, confianza 94%',
    text: 'Dos sujetos en motocicleta. Placas detectadas: NNN-888. Clip de 8 s y 3 capturas listos.',
    acciones: [
      { label: 'Llamar a la policía', luego: { sev: 'ok', icon: 'phone-call', tag: '911 · Folio C5-0000',
          title: 'Llamada en curso', text: 'Se envió ubicación, placas NNN-888 y evidencia de video al operador.' } },
      { label: 'Enviar evidencia', luego: { sev: 'ok', icon: 'file-check', tag: 'Evidencia',
          title: 'Evidencia enviada', text: 'Clip, capturas, placas NNN-888 y hora del evento enviados a la autoridad.' } },
      { label: 'Bloquear bombas', luego: { sev: 'media', icon: 'lock', tag: 'Bombas',
          title: 'Bombas 7 y 8 bloqueadas', text: 'Reapertura solo con confirmación del gerente.' } },
    ],
  },
  { global: true, sev: 'alta', icon: 'heart-crack', tag: 'Seguridad · CAM-05 · Pasillo 2',
    title: 'Desmayo detectado, confianza 91%', text: 'Persona en el piso sin movimiento desde hace 12 s.',
    acciones: [
      { label: 'Pedir ambulancia', luego: { sev: 'ok', icon: 'ambulance', tag: 'Emergencias', title: 'Ambulancia solicitada', text: 'Se envió ubicación exacta y captura de la cámara.' } },
      { label: 'Enviar empleado con botiquín', luego: { sev: 'ok', icon: 'cross', tag: 'Tienda', title: 'Empleado en camino', text: 'Llega al pasillo 2 en menos de 1 min.' } }, DESCARTAR ] },
  { global: true, sev: 'alta', icon: 'car-front', tag: 'Seguridad · CAM-06 · Salida sur',
    title: 'Accidente vehicular, confianza 87%', text: 'Colisión leve entre dos vehículos en el carril de salida.',
    acciones: [
      { label: 'Llamar a tránsito', luego: { sev: 'ok', icon: 'phone-call', tag: 'Tránsito', title: 'Reporte levantado', text: 'Se enviaron ubicación, hora y video del impacto.' } },
      { label: 'Cerrar carril', luego: { sev: 'media', icon: 'traffic-cone', tag: 'Operación', title: 'Carril de salida sur cerrado', text: 'Se redirige el flujo por la salida norte.' } }, DESCARTAR ] },
  { global: true, sev: 'critica', icon: 'flame', tag: 'Seguridad · CAM-04 · Isla 3',
    title: 'Fuego detectado, confianza 96%', text: 'Llama visible junto a la Bomba 3. Riesgo para el combustible.',
    acciones: [
      { label: 'Paro de emergencia', luego: { sev: 'ok', icon: 'octagon-x', tag: 'Emergencia', title: 'Paro de emergencia activo', text: 'Las 8 bombas se detuvieron y la alarma está sonando.' } },
      { label: 'Llamar a bomberos', luego: { sev: 'ok', icon: 'phone-call', tag: 'Bomberos', title: 'Bomberos notificados', text: 'Se envió ubicación, captura y tipo de combustible cercano.' } } ] },
  { global: true, sev: 'media', icon: 'package-search', tag: 'Seguridad · CAM-01 · Caja',
    title: 'Objeto olvidado, confianza 61%', text: 'Bolsa sin dueño en el mostrador desde hace 4 min.',
    acciones: [
      { label: 'Avisar al cajero', luego: { sev: 'ok', icon: 'bell-ring', tag: 'Tienda', title: 'Cajero avisado', text: 'Revisará el objeto y buscará al cliente.' } },
      { label: 'Guardar y registrar', luego: { sev: 'ok', icon: 'archive', tag: 'Objetos perdidos', title: 'Objeto registrado', text: 'Quedó en resguardo con foto y hora.' } }, DESCARTAR ] },
  { global: true, sev: 'media', icon: 'fuel', tag: 'Seguridad · CAM-08 · Bomba 2',
    title: 'Mal uso de bomba, confianza 82%', text: 'Cliente manipula la manguera con el motor encendido.',
    acciones: [
      { label: 'Pausar Bomba 2', luego: { sev: 'ok', icon: 'pause-circle', tag: 'Bombas', title: 'Bomba 2 en pausa', text: 'Se reanuda cuando el despachador lo confirme.' } },
      { label: 'Avisar al despachador', luego: { sev: 'ok', icon: 'megaphone', tag: 'Despachador', title: 'Despachador avisado', text: 'Va hacia la Bomba 2.' } }, DESCARTAR ] },
  { global: true, sev: 'info', icon: 'users', tag: 'Seguridad · CAM-07 · Acceso norte',
    title: 'Fila excesiva, confianza 74%', text: '8 vehículos en espera, tiempo estimado 7 min.',
    acciones: [
      { label: 'Abrir bombas libres', luego: { sev: 'ok', icon: 'fuel', tag: 'Bombas', title: 'Bombas 4 y 8 abiertas', text: 'Se dirige el tráfico con el LED de acceso.' } },
      { label: 'Llamar despachador extra', luego: { sev: 'ok', icon: 'user-plus', tag: 'Turno', title: 'Refuerzo solicitado', text: 'Un despachador sale de descanso.' } }, DESCARTAR ] },
  { paginas: ['bombas'], espera: 14000, sev: 'alta', icon: 'wifi-off', tag: 'Bomba 5 · Pago',
    title: 'Falla de red en el cobro', text: 'Despacho de Diésel terminado sin cobrar. Decide cómo cerrar la venta.',
    acciones: [
      { label: 'Cobrar manual', luego: { sev: 'ok', icon: 'receipt', tag: 'Bomba 5', title: 'Cobro manual registrado', text: 'Queda marcado para conciliar al restablecer la red.' } },
      { label: 'Reintentar', luego: { sev: 'info', icon: 'refresh-cw', tag: 'Bomba 5', title: 'Reintentando cobro', text: 'Se revisará la conexión en 30 s.' } }, DESCARTAR ] },
  { paginas: ['bombas', 'mantenimiento'], espera: 28000, sev: 'media', icon: 'scale', tag: 'Conciliación · Diésel',
    title: 'Diferencia de 20 L entre despacho y venta', text: 'Fuera de tolerancia. Conviene abrir investigación antes del corte.',
    acciones: [ { label: 'Abrir investigación', luego: { sev: 'ok', icon: 'search-check', tag: 'Conciliación', title: 'Investigación abierta', text: 'Asignada a mantenimiento con el detalle por bomba.' } }, DESCARTAR ] },
  { paginas: ['despachador'], espera: 9000, sev: 'media', icon: 'user-x', tag: 'Despachador · Bomba 6',
    title: 'Identidad no confirmada', text: 'Valida al operador antes de autorizar el despacho.',
    acciones: [ { label: 'Validar ahora', luego: { sev: 'ok', icon: 'user-check', tag: 'Despachador', title: 'Identidad confirmada', text: 'Turno matutino habilitado.' } }, DESCARTAR ] },
  { paginas: ['despachador'], espera: 24000, sev: 'info', icon: 'sparkles', tag: 'Oferta sugerida',
    title: 'Cliente recurrente en Bomba 6', text: 'Suele comprar lavado. Ofrecer paquete antes del cobro.',
    acciones: [ { label: 'Ofrecer', luego: { sev: 'ok', icon: 'check', tag: 'Oferta', title: 'Oferta mostrada al cliente', text: 'Se registrará si la acepta.' } }, DESCARTAR ] },
  { paginas: ['mantenimiento'], espera: 10000, sev: 'alta', icon: 'activity', tag: 'Dispensario 3 · Pronóstico',
    title: 'Riesgo de falla en 48 h', text: 'Vibración fuera de rango. Programar antes de que detenga la bomba.',
    acciones: [ { label: 'Programar orden', luego: { sev: 'ok', icon: 'wrench', tag: 'Mantenimiento', title: 'Orden de trabajo creada', text: 'Ventana sugerida: horario de menor demanda.' } }, DESCARTAR ] },
  { paginas: ['mantenimiento'], espera: 26000, sev: 'media', icon: 'truck', tag: 'Inventario · Regular',
    title: 'Entrega llega en 2 h con nivel bajo', text: 'Nivel proyectado bajo el mínimo antes de la descarga.',
    acciones: [ { label: 'Limitar despacho', luego: { sev: 'ok', icon: 'gauge', tag: 'Inventario', title: 'Límite aplicado', text: 'Despacho de Regular restringido hasta la entrega.' } }, DESCARTAR ] },
  { global: true, sev: 'alta', icon: 'cigarette', tag: 'CAM-03 · Bomba 5',
    title: 'Cigarro encendido, confianza 88%', text: 'Riesgo de incendio en isla de despacho.',
    acciones: [ { label: 'Avisar al guardia', luego: { sev: 'ok', icon: 'shield-check', tag: 'Seguridad', title: 'Guardia en camino', text: 'Notificado con ubicación y captura.' } }, DESCARTAR ] },
  { paginas: ['energia'], espera: 8000, sev: 'media', icon: 'zap', tag: 'Energía · Pico 14 h',
    title: 'Demanda alta prevista', text: 'Pasar a batería durante el pico reduce el cargo por demanda.',
    acciones: [ { label: 'Usar batería', luego: { sev: 'ok', icon: 'battery-charging', tag: 'Energía', title: 'Modo batería programado', text: 'Se activa de 13:30 a 15:30.' } }, DESCARTAR ] },
  { paginas: ['comercial'], espera: 8000, sev: 'info', icon: 'trending-down', tag: 'Tienda',
    title: 'Venta 18% bajo lo esperado', text: 'Activar escena de promoción en el LED de la entrada.',
    acciones: [ { label: 'Activar promoción', luego: { sev: 'ok', icon: 'lightbulb', tag: 'Tienda', title: 'Promoción activa', text: 'Escena LED cambiada a Promoción.' } }, DESCARTAR ] },
];

/* ── Campana: historial de todas las notificaciones ── */
const haceTxt = (t) => {
  const m = Math.floor((Date.now() - t) / 60000);
  return m < 1 ? 'ahora' : `hace ${m} min`;
};

G5.pintarCampana = () => {
  const n = G5.notifs.filter((x) => !x.leida).length;
  const b = document.getElementById('campana-badge');
  if (!b) return;
  b.textContent = n > 9 ? '9+' : n;
  b.hidden = !n;
  if (document.getElementById('campana-panel')?.classList.contains('campana-panel--abierto')) G5.pintarPanel();
};

G5.pintarPanel = () => {
  const lista = document.getElementById('campana-lista');
  lista.innerHTML = G5.notifs.length ? '' : '<p class="campana-vacio">Sin notificaciones.</p>';
  G5.notifs.forEach((n) => {
    const el = document.createElement('div');
    el.className = `campana-item campana-item--${n.sev || 'info'}`;
    el.innerHTML = `
      <span class="toast__icon"><i data-lucide="${n.icon || 'bell'}"></i></span>
      <div class="toast__body">
        <span class="toast__tag">${n.tag || ''} · ${haceTxt(n.t)}</span>
        <span class="toast__title">${n.title}</span>
        <span class="toast__text">${n.text || ''}</span>
        <div class="toast__actions"></div>
      </div>`;
    const ac = el.querySelector('.toast__actions');
    (n.acciones || []).forEach((a) => {
      const b = document.createElement('button');
      b.className = 'toast__btn' + (a.ghost ? ' toast__btn--ghost' : '');
      b.textContent = a.label;
      b.onclick = () => {
        G5.notifs = G5.notifs.filter((x) => x.id !== n.id);
        G5.guardarNotifs();
        if (a.luego) G5.toast(a.luego);
      };
      ac.appendChild(b);
    });
    if (!ac.children.length) ac.remove();
    lista.appendChild(el);
  });
  if (window.lucide) lucide.createIcons({ root: lista });
};

function montarCampana() {
  const slot = document.getElementById('auth-slot');
  if (!slot) return;
  slot.style.cssText += 'display:flex; align-items:center; gap:8px;';
  const wrap = document.createElement('div');
  wrap.className = 'campana';
  wrap.innerHTML = `
    <button class="campana__btn" id="campana-btn" aria-label="Notificaciones" aria-expanded="false">
      <i data-lucide="bell"></i><span class="campana__badge" id="campana-badge" hidden>0</span>
    </button>
    <div class="campana-panel" id="campana-panel">
      <div class="campana-panel__head">
        <strong>Notificaciones</strong>
        <button class="toast__btn toast__btn--ghost" id="campana-limpiar">Limpiar todo</button>
      </div>
      <div class="campana-panel__lista" id="campana-lista"></div>
    </div>`;
  slot.appendChild(wrap);

  const panel = wrap.querySelector('#campana-panel');
  const btn = wrap.querySelector('#campana-btn');
  const alternar = (abrir) => {
    panel.classList.toggle('campana-panel--abierto', abrir);
    btn.setAttribute('aria-expanded', abrir);
    if (abrir) {
      G5.notifs.forEach((n) => { n.leida = true; });
      G5.guardarNotifs();
      G5.pintarPanel();
    }
  };
  btn.onclick = (e) => { e.stopPropagation(); alternar(!panel.classList.contains('campana-panel--abierto')); };
  panel.onclick = (e) => e.stopPropagation();
  document.addEventListener('click', () => alternar(false));
  wrap.querySelector('#campana-limpiar').onclick = () => { G5.notifs = []; G5.guardarNotifs(); G5.pintarPanel(); };
  if (window.lucide) lucide.createIcons({ root: wrap });
  G5.pintarCampana();
}

/* ── Cada 15 s emerge una alerta distinta de la página; al agotarlas, reinicia. ── */
document.addEventListener('DOMContentLoaded', () => {
  montarCampana();
  const pagina = document.body.dataset.page;
  const pool = ALERTAS_DEMO.filter((a) => a.global || (a.paginas || []).includes(pagina));
  let vistas = [];
  const siguiente = () => {
    let libres = pool.filter((a) => !vistas.includes(a.title));
    if (!libres.length) { vistas = [vistas[vistas.length - 1]]; libres = pool.filter((a) => !vistas.includes(a.title)); }
    const a = libres[Math.floor(Math.random() * libres.length)];
    vistas.push(a.title);
    G5.toast(a);
  };
  setTimeout(() => { siguiente(); setInterval(siguiente, 15000); }, 3000);
});
