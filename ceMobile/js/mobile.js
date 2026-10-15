/* ============================================
   CE MOBILE — MOTOR JS CON DATOS MOCK
   AGENTE IA INTERACTIVO + FEED DINÁMICO
   ============================================ */

'use strict';

/* ────────────────────────────
   DATOS MOCK — HISTORIAS
──────────────────────────────*/
const HISTORIAS = [
  {
    id: 'h1', label: 'Carmen', seen: false,
    icon: 'heart', iconColor: '#34d399',
    sentimiento: 'pos', sentText: 'Te adoran',
    fuente: 'Redes Sociales · Carmen', hora: 'Hace 12 min',
    titulo: 'En Ciudad del Carmen te tienen en el corazón',
    cuerpo: 'Los hashtags #ConElCandidato y #CarmenContigoCamp llevan 3,400 menciones en las últimas 4 horas. Hay videos compartidos de tu recorrido con comentarios como "así se necesita, que venga a vernos" y "ojalá llegue". Tu sentimiento en la región petrolera es el más alto del estado.',
    bgGrad: 'linear-gradient(135deg, #0f2027, #203a43, #2c5364)'
  },
  {
    id: 'h2', label: 'Video Viral', seen: false,
    icon: 'video', iconColor: '#a78bfa',
    sentimiento: 'pos', sentText: 'Viral',
    fuente: 'TikTok & Reels · Estado', hora: 'Hace 28 min',
    titulo: 'Tu clip del mitin se está haciendo viral',
    cuerpo: 'El momento en que tomaste el micrófono sin guion y dijiste "Campeche no pide permiso para crecer" está en 47,000 reproducciones. Los comentarios son de risa y cariño: "jajaja es auténtico", "que no lo entrenen por favor", "así da gusto ver a un político". Eso no se compra.',
    bgGrad: 'linear-gradient(135deg, #1a0533, #2d1b69, #1a0533)'
  },
  {
    id: 'h3', label: 'Champotón', seen: false,
    icon: 'alert-triangle', iconColor: '#f5a524',
    sentimiento: 'neg', sentText: 'Atención',
    fuente: 'CE-Análisis · Champotón', hora: 'Hace 45 min',
    titulo: 'Champotón necesita otro enfoque',
    cuerpo: 'En Champotón el sentimiento es neutro-frío. La gente ahí está preocupada por el tema del agua potable en las zonas rurales. No es que no te apoyen — es que aún no han escuchado que tienes una respuesta para eso. La próxima vez que hables ahí, arranca con el plan hídrico y lo volteas.',
    bgGrad: 'linear-gradient(135deg, #1a0c00, #3d2400, #1a0c00)'
  },
  {
    id: 'h4', label: 'Entrevista', seen: false,
    icon: 'mic', iconColor: '#22d3ee',
    sentimiento: 'pos', sentText: 'Muy Bien',
    fuente: 'MonitorSol · Canal 11', hora: 'Hace 1h',
    titulo: 'Canal 11: entrevista de 9.2 de calificación',
    cuerpo: 'El análisis de la entrevista de esta mañana fue muy positivo. Apareciste seguro, con cifras concretas, y el conductor no logró desestabilizarte en el tema de finanzas públicas. El clip de cierre ("lo vamos a hacer juntos o no lo vamos a hacer") ya está en 12,000 reproducciones.',
    bgGrad: 'linear-gradient(135deg, #00101a, #003d5c, #00101a)'
  },
  {
    id: 'h5', label: 'Hecelchakán', seen: false,
    icon: 'trending-up', iconColor: '#34d399',
    sentimiento: 'pos', sentText: 'Favorito',
    fuente: 'CE-Territorio', hora: 'Hace 2h',
    titulo: 'Hecelchakán: territorio blindado',
    cuerpo: 'En Hecelchakán tu ventaja es de +8.3pp y el voto está consolidado desde hace dos procesos. Ahí ya te quieren. Cuando vayas, es momento de escuchar más que hablar — la gente solo quiere ver que llegaste y que no los olvidaste.',
    bgGrad: 'linear-gradient(135deg, #001a0a, #00400a, #001a0a)'
  },
  {
    id: 'h6', label: 'Speech Hoy', seen: false,
    icon: 'sparkles', iconColor: '#f472b6',
    sentimiento: 'info', sentText: 'Consejo',
    fuente: 'CE-Copiloto', hora: 'Hace 3h',
    titulo: 'Así debes hablar esta tarde en la capital',
    cuerpo: 'Para el mitin de las 18:00 hrs en Campeche capital te recomiendo estos 3 ejes: (1) Seguridad hídrica: la gente ahí lo trae en mente. (2) Empleo burocrático sin recortes: el electorado de la capital es de clase media pública. (3) Cierra siempre con la frase de confianza — es lo que más repiten en redes.',
    bgGrad: 'linear-gradient(135deg, #1a0018, #3d004a, #1a0018)'
  }
];

/* ────────────────────────────
   DATOS MOCK — ALERTAS
──────────────────────────────*/
const ALERTAS = [
  {
    icon: 'alert-triangle', iconBg: 'rgba(255,71,87,0.15)', iconColor: '#ff4757',
    titulo: 'Sección 0142 — Champotón: Anomalía Detectada',
    cuerpo: 'Participación del 87% antes del cierre habitual. CE-Forense ya tiene coordinadores en camino.',
    hora: 'Hace 18 min', tipo: 'critica'
  },
  {
    icon: 'trending-up', iconBg: 'rgba(52,211,153,0.12)', iconColor: '#34d399',
    titulo: '+4.2pp en Ciudad del Carmen esta semana',
    cuerpo: 'El levantamiento de campo de 48h confirma crecimiento sólido tras el recorrido en colonias populares.',
    hora: 'Hace 42 min', tipo: 'positiva'
  },
  {
    icon: 'video', iconBg: 'rgba(167,139,250,0.12)', iconColor: '#a78bfa',
    titulo: 'Tu clip del mitin cruzó 40K reproducciones',
    cuerpo: 'El momento sin guion ya está siendo compartido masivamente. Sentimiento 94% positivo.',
    hora: 'Hace 1h', tipo: 'positiva'
  },
  {
    icon: 'mic-off', iconBg: 'rgba(245,165,36,0.15)', iconColor: '#f5a524',
    titulo: 'Calkiní: Oposición refuerza cobertura de medios',
    cuerpo: 'Campaña de radio contraria detectada en AM local. CE-Medios está monitoreando en tiempo real.',
    hora: 'Hace 2h', tipo: 'media'
  }
];

/* ────────────────────────────
   DATOS MOCK — MUNICIPIOS TERRITORIO
──────────────────────────────*/
const MUNICIPIOS = [
  { nombre: 'Campeche', ventaja: '+2.8', estado: 'Competitivo', color: '#f5c518', pct: 49 },
  { nombre: 'Cd. del Carmen', ventaja: '+1.4', estado: 'Apretado', color: '#f5a524', pct: 46 },
  { nombre: 'Champotón', ventaja: '-4.7', estado: 'En Riesgo', color: '#ff4757', pct: 38 },
  { nombre: 'Calkiní', ventaja: '-3.1', estado: 'En Riesgo', color: '#ff4757', pct: 40 },
  { nombre: 'Hecelchakán', ventaja: '+8.3', estado: 'Favorable', color: '#34d399', pct: 58 },
  { nombre: 'Hopelchén', ventaja: '+11.2', estado: 'Sólido', color: '#34d399', pct: 65 },
  { nombre: 'Palizada', ventaja: '+7.6', estado: 'Favorable', color: '#34d399', pct: 55 },
  { nombre: 'Seybaplaya', ventaja: '-2.3', estado: 'En Riesgo', color: '#ff8c42', pct: 41 },
  { nombre: 'Tenabo', ventaja: '+9.1', estado: 'Sólido', color: '#34d399', pct: 61 },
  { nombre: 'Escárcega', ventaja: '+3.2', estado: 'Avanzando', color: '#22d3ee', pct: 51 },
  { nombre: 'Calakmul', ventaja: '+14.8', estado: 'Dominante', color: '#34d399', pct: 72 },
  { nombre: 'Candelaria', ventaja: '+0.9', estado: 'Apretado', color: '#f5c518', pct: 45 },
  { nombre: 'Dzitbalché', ventaja: '+4.1', estado: 'Avanzando', color: '#22d3ee', pct: 52 }
];

/* ────────────────────────────
   DATOS MOCK — CHAT AGENTE IA
──────────────────────────────*/
const INITIAL_MSGS = [
  {
    role: 'agent',
    text: '¡Buenos días! Soy tu Copiloto CE. Ya revisé todo lo de anoche y esta mañana. Tienes buenas noticias hoy — ¿quieres el resumen rápido o empezamos por algo en específico?'
  }
];

const QUICK_REPLIES_INIT = [
  'Dame el resumen del día',
  'Cómo me fue en la entrevista',
  'Qué dicen de mí en redes',
  'Qué hago en Champotón',
  'Cómo estoy en Carmen'
];

const AGENT_RESPONSES = {
  'Dame el resumen del día': `<b>Tu día de hoy, rápido y directo:</b><br><br>
<span class="highlight">Lo bueno:</span> Ciudad del Carmen sube +4.2pp. Tu clip del mitin ya tiene 47K reproducciones. La entrevista de Canal 11 fue un 9.2.<br><br>
<span class="warn">Lo que hay que atender:</span> Champotón tiene una anomalía de participación en Sección 0142 — ya tenemos coordinadores. Calkiní necesita más presencia.<br><br>
Esta tarde tienes mitin en la capital a las 18:00. El clima está bien para campaña.`,

  'Cómo me fue en la entrevista': `Muy bien. El análisis completo de MonitorSol le da a la entrevista de Canal 11 un <span class="highlight">9.2 de 10</span>.<br><br>
Lo que funcionó mejor: cuando dijiste "las cifras no mienten y yo tampoco" — eso fue el momento de mayor audiencia.<br><br>
El conductor intentó desestabilizarte en el tema de pensiones y lo bloqueaste con calma. Eso en redes se valora mucho.<br><br>
El clip de cierre ya está en 12,000 reproducciones. Ese es tu perfil en medios hoy.`,

  'Qué dicen de mí en redes': `Te voy a ser honesto porque para eso estoy:<br><br>
<span class="highlight">Lo que está sonando bien:</span> El video del mitin sin guion, tu frase de cierre, y los recorridos en Carmen. La gente dice que eres "auténtico" y "no pareces político normal".<br><br>
Hay comentarios como <b>"jajaja se le fue el script y así es mejor"</b> y <b>"es el primero que viene aquí en 3 años"</b>.<br><br>
<span class="warn">Lo que debes saber:</span> Hay una cuenta anónima generando contenido negativo sobre el tema hídrico. Lo estamos monitoreando. Por ahora es ruido menor.`,

  'Qué hago en Champotón': `Champotón es el municipio que más necesita tu atención esta semana. Aquí el análisis:<br><br>
<span class="warn">El problema:</span> Aún no han escuchado una respuesta concreta sobre agua potable rural. Hay 3 comunidades sin acceso confiable.<br><br>
<span class="highlight">Lo que propongo:</span> En la próxima visita, arranca con el Plan Hídrico antes de cualquier otra cosa. No como promesa — como anuncio concreto con fecha.<br><br>
Y si puedes llevar un técnico o ingeniero contigo, mejor. La gente de Champotón responde mucho al "no vengo solo, vengo con soluciones".`,

  'Cómo estoy en Carmen': `Ciudad del Carmen es tu mejor momento de la semana. Mira esto:<br><br>
<span class="highlight">+1.4pp de ventaja sobre el segundo lugar</span> — y subiendo. El levantamiento de 48h confirmó +4.2pp de crecimiento tras el recorrido en colonias.<br><br>
El voto joven en Carmen está respondiendo especialmente bien. Ahí el tema del empleo local y la economía del mar tiene mucha tracción.<br><br>
Mi recomendación: vuelve pronto antes de que el margen se consolide o se reduzca. Ahí tienes momentum — hay que aprovecharlo ahora.`,

  'default': `Revisando el análisis más reciente... Un momento.<br><br>Lo que puedo decirte es que el panorama general es positivo. Tu trabajo de territorio está dando resultados. ¿Hay algo específico de lo que quieras hablar?`
};

/* ────────────────────────────
   ESTADO GLOBAL
──────────────────────────────*/
const state = {
  activeTab: 'mia',
  storyOpen: false,
  storyTimer: null,
  notifOpen: false,
  chatMsgs: [...INITIAL_MSGS],
  storyProgress: 0
};

/* ────────────────────────────
   UTILS
──────────────────────────────*/
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

/* ────────────────────────────
   INIT
──────────────────────────────*/
document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initTabs();
  initNotifDrawer();
  buildStories();
  buildFeed();
  buildAlertas();
  buildTerritorio();
  buildChat();
  lucide.createIcons();

  // Alerta dinámica que aparece después de 3 segundos
  setTimeout(() => showFloatingAlert(), 3000);
  // Segunda alerta después de 12 seg
  setTimeout(() => showFloatingAlert2(), 12000);
});

/* ────────────────────────────
   ALERTAS FLOTANTES DINÁMICAS
──────────────────────────────*/
function showFloatingAlert() {
  const wrap = $('floating-alerts');
  if (!wrap) return;
  const div = document.createElement('div');
  div.className = 'alert-banner';
  div.innerHTML = `
    <div class="alert-banner__dot"></div>
    <span class="alert-banner__text">Nuevo en Carmen: tu video tiene 47K reproducciones</span>
    <i data-lucide="arrow-right" style="width:14px;height:14px;color:#74839a;flex-shrink:0;"></i>
  `;
  div.addEventListener('click', () => {
    div.style.opacity = '0';
    setTimeout(() => div.remove(), 300);
    switchTab('redes');
  });
  wrap.appendChild(div);
  lucide.createIcons();
  setTimeout(() => { div.style.opacity = '0'; setTimeout(() => div.remove(), 300); }, 8000);
}

function showFloatingAlert2() {
  const wrap = $('floating-alerts');
  if (!wrap) return;
  const div = document.createElement('div');
  div.className = 'alert-banner';
  div.style.background = 'rgba(245,197,24,0.1)';
  div.style.borderColor = 'rgba(245,197,24,0.3)';
  div.innerHTML = `
    <div class="alert-banner__dot" style="background:#f5c518;"></div>
    <span class="alert-banner__text" style="color:#f5c518;">Candelaria: margen muy apretado — 0.9pp. Hay que mover gente.</span>
    <i data-lucide="arrow-right" style="width:14px;height:14px;color:#74839a;flex-shrink:0;"></i>
  `;
  div.addEventListener('click', () => {
    div.style.opacity = '0';
    setTimeout(() => div.remove(), 300);
    switchTab('territorio');
  });
  wrap.appendChild(div);
  lucide.createIcons();
  setTimeout(() => { div.style.opacity = '0'; setTimeout(() => div.remove(), 300); }, 10000);
}

/* ────────────────────────────
   HISTORIAS
──────────────────────────────*/
function buildStories() {
  const rail = $('stories-rail');
  if (!rail) return;
  rail.innerHTML = HISTORIAS.map(h => `
    <div class="story-bubble ${h.seen ? 'story-bubble--seen' : ''}" onclick="openStory('${h.id}')">
      <div class="story-bubble__ring">
        <div class="story-bubble__inner">
          <i data-lucide="${h.icon}" style="width:24px;height:24px;color:${h.iconColor};"></i>
        </div>
      </div>
      <span class="story-bubble__lbl">${h.label}</span>
    </div>
  `).join('');
}

function openStory(id) {
  const h = HISTORIAS.find(x => x.id === id);
  if (!h) return;
  h.seen = true;

  const overlay = $('story-overlay');
  const bg = $('story-bg');
  const sentPill = $('story-sentiment');
  const titleEl = $('story-title');
  const bodyEl = $('story-body-text');
  const sourceEl = $('story-source-text');
  const progFill = $('story-progress-fill');

  bg.style.background = h.bgGrad;
  sentPill.textContent = h.sentText;
  sentPill.className = 'story-sentiment-pill ' +
    (h.sentimiento === 'pos' ? 'story-sentiment-pill--pos' : h.sentimiento === 'neg' ? 'story-sentiment-pill--neg' : 'story-sentiment-pill--info');
  titleEl.textContent = h.titulo;
  bodyEl.textContent = h.cuerpo;
  sourceEl.textContent = `${h.fuente} · ${h.hora}`;

  overlay.classList.add('story-overlay--open');
  state.storyOpen = true;

  // Barra de progreso
  let p = 0;
  progFill.style.width = '0%';
  clearInterval(state.storyTimer);
  state.storyTimer = setInterval(() => {
    p += 1.67; // ~60 seg total / 100 steps = cada 600ms llega al 100%
    progFill.style.width = Math.min(p, 100) + '%';
    if (p >= 100) closeStory();
  }, 1000);

  // Marcar como vista en el rail
  buildStories();
  lucide.createIcons();
}

function closeStory() {
  $('story-overlay').classList.remove('story-overlay--open');
  state.storyOpen = false;
  clearInterval(state.storyTimer);
}

/* ────────────────────────────
   FEED — MI DÍA
──────────────────────────────*/
function buildFeed() {
  const feed = $('feed-list');
  if (!feed) return;

  feed.innerHTML = `
    <!-- POST 1: Resumen del día con ego -->
    <div class="feed-post">
      <div class="post-header">
        <div class="post-agent-avatar">CE</div>
        <div class="post-agent-info">
          <div class="post-agent-name">CE-Copiloto</div>
          <div class="post-agent-time">Resumen matutino · Hoy 06:00</div>
        </div>
        <span class="proc-badge proc--dato">Dato</span>
      </div>
      <div class="post-visual" style="background:linear-gradient(135deg,#0f1e3a,#162040);">
        <div class="post-visual-text">
          <div class="post-visual-label">Tu día de hoy</div>
          <div class="post-visual-headline">3 eventos. Ciudad del Carmen, capital y Calkiní. Cobertura de medios en verde.</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;flex-shrink:0;">
          <div style="text-align:center;">
            <div class="post-big-num" style="color:#22d3ee;">3</div>
            <div style="font-size:0.62rem;color:#74839a;">eventos</div>
          </div>
        </div>
      </div>
      <div class="post-body">
        <p class="post-agent-quote">Todo está coordinado. <b>Tu primer evento es a las 10:00 hrs en Carmen.</b> Llevas viento a favor — el levantamiento de ayer confirma crecimiento en esa zona.</p>
      </div>
      <div class="post-actions">
        <div class="post-action-btn" onclick="switchTab('agente')">
          <i data-lucide="message-circle" style="width:18px;height:18px;"></i> Pregúntame algo
        </div>
      </div>
    </div>

    <div class="feed-gap"></div>

    <!-- POST 2: Viral en redes -->
    <div class="feed-post">
      <div class="post-header">
        <div class="post-agent-avatar" style="background:linear-gradient(135deg,#7c3aed,#a78bfa);">RD</div>
        <div class="post-agent-info">
          <div class="post-agent-name">CE-Redes</div>
          <div class="post-agent-time">Análisis en tiempo real · Hace 28 min</div>
        </div>
        <span class="proc-badge proc--inferencia">Inferencia</span>
      </div>
      <div class="post-visual" style="background:linear-gradient(135deg,#1a0533,#2d1b69);">
        <div>
          <div class="post-big-num" style="color:#a78bfa;">47K</div>
          <div style="font-size:0.68rem;color:#74839a;margin-top:2px;">reproducciones</div>
        </div>
        <div class="post-visual-text">
          <div class="post-visual-label">Tu clip del mitin</div>
          <div class="post-visual-headline">"Campeche no pide permiso para crecer"</div>
        </div>
      </div>
      <div class="post-body">
        <p class="post-agent-quote">El momento que dijiste eso sin guion <b>ya se está haciendo viral.</b> Los comentarios están de película:<br><br>
        <b>"jajaja es auténtico, no lo entrenen por favor"</b> — 2.1K likes<br>
        <b>"así da gusto ver a un político"</b> — 1.8K likes<br>
        <b>"es el primero que viene aquí en 3 años"</b> — 1.4K likes<br><br>
        <span class="highlight">Sentimiento: 94% positivo.</span> Eso no se compra con pauta.</p>
      </div>
      <div class="pill-row" style="padding:0 16px 14px;">
        <span class="pill pill--purple"><i data-lucide="trending-up" style="width:12px;height:12px;"></i> Viral</span>
        <span class="pill pill--green">94% Positivo</span>
        <span class="pill pill--cyan">TikTok + Reels</span>
      </div>
    </div>

    <div class="feed-gap"></div>

    <!-- POST 3: Carmen te quiere -->
    <div class="feed-post">
      <div class="post-header">
        <div class="post-agent-avatar" style="background:linear-gradient(135deg,#059669,#34d399);">TT</div>
        <div class="post-agent-info">
          <div class="post-agent-name">CE-Territorio</div>
          <div class="post-agent-time">Ciudad del Carmen · Hace 1h</div>
        </div>
        <span class="proc-badge proc--estimacion">Estimación</span>
      </div>
      <div class="post-visual" style="background:linear-gradient(135deg,#001a14,#003d28);">
        <div>
          <div class="post-big-num" style="color:#34d399;">+4.2</div>
          <div style="font-size:0.68rem;color:#74839a;margin-top:2px;">pp esta semana</div>
        </div>
        <div class="post-visual-text">
          <div class="post-visual-label">Ciudad del Carmen</div>
          <div class="post-visual-headline">El municipio que más te está apoyando en este momento</div>
        </div>
      </div>
      <div class="post-body">
        <p class="post-agent-quote">Después del recorrido en colonias populares, los números subieron. La gente en Carmen valora mucho que hayas ido a zonas que no suelen visitar los candidatos. <b>Ahí tienes momentum — hay que aprovecharlo ahora.</b></p>
      </div>
      <div class="post-actions">
        <div class="post-action-btn" onclick="openStory('h1')">
          <i data-lucide="heart" style="width:18px;height:18px;color:#34d399;"></i> Ver historia completa
        </div>
      </div>
    </div>

    <div class="feed-gap"></div>

    <!-- POST 4: Consejo de speech -->
    <div class="feed-post" style="border-color:rgba(244,114,182,0.2);">
      <div class="post-header">
        <div class="post-agent-avatar" style="background:linear-gradient(135deg,#9d174d,#f472b6);">CP</div>
        <div class="post-agent-info">
          <div class="post-agent-name">CE-Speech Copiloto</div>
          <div class="post-agent-time">Mitin Capital · 18:00 hrs hoy</div>
        </div>
        <span class="proc-badge proc--recomendacion">Recomendación</span>
      </div>
      <div class="post-body" style="padding-top:14px;">
        <p class="post-agent-quote">Para el mitin de esta tarde en la capital, aquí está mi análisis de lo que más tracción tiene ahí:<br><br>
        <b>1. Seguridad hídrica</b> — La gente de la capital lo trae en mente. Arranca con esto.<br>
        <b>2. Empleo burocrático</b> — El electorado de la capital es clase media pública. Tranquilizalos.<br>
        <b>3. Cierra con confianza</b> — Tu frase de cierre "lo hacemos juntos o no lo hacemos" es lo que más repiten. No la cambies.<br><br>
        <span class="warn">Nota:</span> Esta sugerencia requiere tu revisión antes de usarla.</p>
      </div>
      <div class="pill-row" style="padding:8px 16px 14px;">
        <span class="pill pill--purple">Validar antes</span>
        <span class="pill pill--cyan">Análisis CE-Medios</span>
      </div>
    </div>

    <div class="feed-gap"></div>

    <!-- POST 5: Entrevista calificación -->
    <div class="feed-post">
      <div class="post-header">
        <div class="post-agent-avatar" style="background:linear-gradient(135deg,#0f4c8a,#22d3ee);">MS</div>
        <div class="post-agent-info">
          <div class="post-agent-name">MonitorSol · Canal 11</div>
          <div class="post-agent-time">Análisis de entrevista · Esta mañana</div>
        </div>
        <span class="proc-badge proc--inferencia">Inferencia</span>
      </div>
      <div class="post-visual" style="background:linear-gradient(135deg,#00101a,#003d5c);">
        <div>
          <div class="post-big-num" style="color:#22d3ee;">9.2</div>
          <div style="font-size:0.68rem;color:#74839a;margin-top:2px;">calificación</div>
        </div>
        <div class="post-visual-text">
          <div class="post-visual-label">Entrevista Canal 11</div>
          <div class="post-visual-headline">Seguro, con cifras, y no te dejaste desestabilizar</div>
        </div>
      </div>
      <div class="post-body">
        <p class="post-agent-quote">El conductor intentó desestabilizarte en el tema de pensiones. Lo bloqueaste con calma y eso en redes se valora mucho. <b>El clip de cierre ya va en 12,000 reproducciones.</b><br><br>Ese es tu perfil en medios hoy.</p>
      </div>
    </div>
  `;
}

/* ────────────────────────────
   ALERTAS DRAWER
──────────────────────────────*/
function buildAlertas() {
  const list = $('notif-list');
  if (!list) return;
  list.innerHTML = ALERTAS.map(a => `
    <div class="notif-item">
      <div class="notif-icon-wrap" style="background:${a.iconBg};">
        <i data-lucide="${a.icon}" style="width:18px;height:18px;color:${a.iconColor};"></i>
      </div>
      <div class="notif-item__text">
        <div class="notif-item__title">${a.titulo}</div>
        <div class="notif-item__body">${a.cuerpo}</div>
        <div class="notif-item__time">${a.hora}</div>
      </div>
    </div>
  `).join('');
}

/* ────────────────────────────
   TERRITORIO
──────────────────────────────*/
function buildTerritorio() {
  const grid = $('municipios-grid');
  if (!grid) return;

  const fav = MUNICIPIOS.filter(m => parseFloat(m.ventaja) >= 5).length;
  const comp = MUNICIPIOS.filter(m => parseFloat(m.ventaja) > 0 && parseFloat(m.ventaja) < 5).length;
  const riesgo = MUNICIPIOS.filter(m => parseFloat(m.ventaja) < 0).length;

  $('cnt-fav').textContent = fav;
  $('cnt-comp').textContent = comp;
  $('cnt-riesgo').textContent = riesgo;

  grid.innerHTML = MUNICIPIOS.map(m => `
    <div class="mun-card" onclick="askAboutMunicipio('${m.nombre}')">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div class="mun-card__name">${m.nombre}</div>
        <div style="font-size:0.62rem;color:${m.color};font-weight:800;">${m.estado}</div>
      </div>
      <div class="mun-card__value" style="color:${m.color};">${m.ventaja}pp</div>
      <div style="background:rgba(255,255,255,0.06);height:4px;border-radius:2px;overflow:hidden;margin-top:4px;">
        <div style="width:${m.pct}%;height:100%;background:${m.color};border-radius:2px;opacity:0.7;"></div>
      </div>
      <div class="mun-card__label">toca para preguntar al agente</div>
    </div>
  `).join('');
}

function askAboutMunicipio(nombre) {
  switchTab('agente');
  setTimeout(() => {
    const input = $('chat-input');
    if (input) {
      input.value = `Cómo estoy en ${nombre}`;
      sendChatMsg();
    }
  }, 400);
}

/* ────────────────────────────
   TEMA CLARO / OSCURO
──────────────────────────────*/
function initThemeToggle() {
  const btn = $('theme-toggle-btn');
  if (!btn) return;

  // Leer preferencia guardada
  const saved = localStorage.getItem('ce-theme') || 'dark';
  applyTheme(saved);

  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem('ce-theme', next);
  });
}

function applyTheme(theme) {
  const iconEl = $('theme-icon');
  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    if (iconEl) {
      iconEl.setAttribute('data-lucide', 'moon');
      lucide.createIcons();
    }
  } else {
    document.documentElement.removeAttribute('data-theme');
    if (iconEl) {
      iconEl.setAttribute('data-lucide', 'sun');
      lucide.createIcons();
    }
  }
}

/* ────────────────────────────
   CHAT AGENTE IA (MOCK)
──────────────────────────────*/
function buildChat() {
  renderChatMsgs();
  showQuickReplies(QUICK_REPLIES_INIT);

  const input = $('chat-input');
  const sendBtn = $('chat-send');
  if (!input || !sendBtn) return;

  input.addEventListener('keypress', e => { if (e.key === 'Enter') sendChatMsg(); });
  sendBtn.addEventListener('click', sendChatMsg);
}

function renderChatMsgs() {
  const list = $('chat-messages');
  if (!list) return;

  list.innerHTML = state.chatMsgs.map(m => m.role === 'agent' ? `
    <div class="chat-msg chat-msg--agent">
      <div class="chat-agent-icon">CE</div>
      <div class="chat-bubble chat-bubble--agent">${m.text}</div>
    </div>
  ` : `
    <div class="chat-msg chat-msg--user">
      <div class="chat-bubble chat-bubble--user">${m.text}</div>
    </div>
  `).join('');

  list.scrollTop = list.scrollHeight;
}

function sendChatMsg() {
  const input = $('chat-input');
  const text = (input.value || '').trim();
  if (!text) return;

  state.chatMsgs.push({ role: 'user', text });
  input.value = '';

  // Ocultar chips mientras escribe
  const qr = $('quick-replies');
  if (qr) qr.innerHTML = '';

  renderChatMsgs();
  showTypingIndicator();

  const delay = 1200 + Math.random() * 800;
  setTimeout(() => {
    removeTypingIndicator();
    const response = AGENT_RESPONSES[text] || AGENT_RESPONSES['default'];
    state.chatMsgs.push({ role: 'agent', text: response });
    renderChatMsgs();

    // Siempre muestra chips de seguimiento contextuales y visibles
    const followUps = getFollowUps(text);
    showQuickReplies(followUps);
    lucide.createIcons();
  }, delay);
}

// Chips contextuales según la pregunta anterior
function getFollowUps(question) {
  const map = {
    'Dame el resumen del día': ['Cómo me fue en la entrevista', 'Qué dicen de mí en redes', 'Qué hago en Champotón'],
    'Cómo me fue en la entrevista': ['Qué mejorar para la próxima', 'Qué dicen de mí en redes', 'Cómo estoy en Carmen'],
    'Qué dicen de mí en redes': ['Cuál es el video que más compartió la gente', 'Cómo estoy en Carmen', 'Qué hago en Champotón'],
    'Qué hago en Champotón': ['Dame el resumen del día', 'Cómo estoy en Carmen', 'Cómo estoy en Calkiní'],
    'Cómo estoy en Carmen': ['Qué dicen de mí en redes', 'Dame el resumen del día', 'Y en Hecelchakán?'],
  };
  return map[question] || ['Dame el resumen del día', 'Cómo estoy en Carmen', 'Qué hago en Champotón', 'Qué dicen de mí en redes'];
}

function sendQuickReply(text) {
  const input = $('chat-input');
  if (input) input.value = text;
  sendChatMsg();
}

function showTypingIndicator() {
  const list = $('chat-messages');
  const typing = document.createElement('div');
  typing.className = 'chat-msg chat-msg--agent';
  typing.id = 'typing-indicator';
  typing.innerHTML = `
    <div class="chat-agent-icon">CE</div>
    <div class="chat-typing">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  list.appendChild(typing);
  list.scrollTop = list.scrollHeight;
}

function removeTypingIndicator() {
  const ind = $('typing-indicator');
  if (ind) ind.remove();
}

function showQuickReplies(replies) {
  const container = $('quick-replies');
  if (!container) return;

  // Header de "Preguntas sugeridas" visible
  container.innerHTML = `
    <div style="width:100%; padding:8px 12px 4px; font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--mob-text-3); display:flex; align-items:center; gap:6px;">
      <i data-lucide="sparkles" style="width:12px;height:12px;"></i>
      Preguntas sugeridas
    </div>
    <div style="display:flex; gap:7px; flex-wrap:wrap; padding:0 12px 10px;">
      ${replies.map(r => `
        <button class="qr-chip" onclick="sendQuickReply('${r}')">${r}</button>
      `).join('')}
    </div>
  `;
  lucide.createIcons();
}

// Alias para compatibilidad con código legado
function buildQuickReplies(replies) {
  showQuickReplies(replies);
}

/* ────────────────────────────
   NOTIF DRAWER
──────────────────────────────*/
function initNotifDrawer() {
  const btn = $('notif-btn');
  const drawer = $('notif-drawer');
  if (!btn || !drawer) return;

  btn.addEventListener('click', () => {
    state.notifOpen = !state.notifOpen;
    drawer.classList.toggle('notif-drawer--open', state.notifOpen);
    lucide.createIcons();
  });

  // Cerrar al hacer tap fuera
  document.addEventListener('click', e => {
    if (state.notifOpen && !drawer.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
      state.notifOpen = false;
      drawer.classList.remove('notif-drawer--open');
    }
  });
}

/* ────────────────────────────
   TABS
──────────────────────────────*/
function initTabs() {
  $$('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
}

function switchTab(tabId) {
  $$('.tab').forEach(t => t.classList.toggle('tab--active', t.dataset.tab === tabId));
  $$('.view').forEach(v => v.classList.toggle('view--active', v.id === `view-${tabId}`));
  state.activeTab = tabId;
  lucide.createIcons();

  // Scroll al top de la vista
  const scroll = document.querySelector('.main-scroll');
  if (scroll) scroll.scrollTop = 0;
}
