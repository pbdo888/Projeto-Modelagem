/* =====================================================================
   McCrea · partículas de fundo das telas internas
   Escuro: bolinhas douradas subindo devagar, com brilho (estilo PS5).
   Claro: poeira de luz quente do pôr do sol, mais lenta e discreta.
   Fogem de leve do cursor. ambiente.estourar(el) solta um estouro dourado
   (usado no resgate de cupom). Fica parado com "reduzir movimento",
   com a aba escondida e na tela de admin.
   ===================================================================== */
(function () {
  'use strict';
  const raiz = document.documentElement;
  const sistemaEscuro = matchMedia('(prefers-color-scheme: dark)');
  const calmo = matchMedia('(prefers-reduced-motion: reduce)');
  const escuro = () => raiz.dataset.tema ? raiz.dataset.tema === 'escuro' : sistemaEscuro.matches;

  const TEMAS = {
    escuro: { cores: ['255,214,130', '255,236,182', '255,188,96'], modo: 'lighter', subida: [7, 20], brilho: [.55, 1], bokeh: [.14, .30] },
    claro:  { cores: ['255,250,236', '255,232,186', '255,214,170'], modo: 'source-over', subida: [4, 12], brilho: [.7, 1], bokeh: [.2, .36] },
  };

  const canvas = document.createElement('canvas');
  canvas.id = 'ambiente';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d');

  // cada cor vira um "sprite" com halo radial: desenhar imagem é bem mais leve que shadowBlur
  function sprite(cor) {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const g = c.getContext('2d'), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    r.addColorStop(0, `rgba(${cor},1)`); r.addColorStop(.18, `rgba(${cor},.9)`);
    r.addColorStop(.45, `rgba(${cor},.22)`); r.addColorStop(1, `rgba(${cor},0)`);
    g.fillStyle = r; g.fillRect(0, 0, 64, 64);
    return c;
  }

  const rnd = (a, b) => a + Math.random() * (b - a);
  let W = 0, H = 0, dpr = 1, tema = null, sprites = [], parts = [], estouro = [];
  let mouse = { x: -9999, y: -9999 }, rodando = false, ultimo = 0, t = 0;

  function nova(p = {}, noTopo = false) {
    const bokeh = Math.random() < .2;
    return Object.assign(p, {
      x: rnd(0, W), y: noTopo ? H + rnd(10, 80) : rnd(0, H),
      tam: bokeh ? rnd(50, 120) : rnd(12, 30),
      bokeh, cor: (Math.random() * 3) | 0,
      sobe: rnd(...tema.subida) * (bokeh ? .55 : 1),
      onda: rnd(8, 26), freq: rnd(.15, .45), fase: rnd(0, 6.28),
      pisca: rnd(.6, 1.8), alfa: bokeh ? rnd(...tema.bokeh) : rnd(...tema.brilho),
      vx: 0, vy: 0,
    });
  }

  function aplicarTema() {
    tema = TEMAS[escuro() ? 'escuro' : 'claro'];
    sprites = [...tema.cores, ...TEMAS.escuro.cores].map(sprite);   // 0-2: tema, 3-5: ouro do estouro
    const n = Math.max(30, Math.min(90, Math.round(W * H / 15000)));
    parts = Array.from({ length: n }, () => nova());
    desenhar();
  }

  function medir() {
    dpr = Math.min(2, devicePixelRatio || 1);
    W = innerWidth; H = innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function passo(dt) {
    t += dt;
    for (const p of parts) {
      p.y -= p.sobe * dt;
      p.x += Math.sin(t * p.freq + p.fase) * p.onda * dt;
      const dx = p.x - mouse.x, dy = p.y - mouse.y, d = Math.hypot(dx, dy);
      if (d < 130 && d > .1) { const f = (130 - d) / 130 * 220; p.vx += dx / d * f * dt; p.vy += dy / d * f * dt; }
      p.x += p.vx * dt; p.y += p.vy * dt;
      p.vx *= .94; p.vy *= .94;
      if (p.y < -p.tam || p.x < -p.tam * 2 || p.x > W + p.tam * 2) nova(p, true);
    }
  }

  function desenhar() {
    ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = tema.modo;
    for (const p of parts) {
      const a = p.alfa * (p.bokeh ? 1 : .65 + .35 * Math.sin(t * p.pisca + p.fase));
      ctx.globalAlpha = Math.max(0, a);
      ctx.drawImage(sprites[p.cor], p.x - p.tam / 2, p.y - p.tam / 2, p.tam, p.tam);
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }

  const parado = () => calmo.matches || document.hidden || location.hash === '#/admin';
  function quadro(agora) {
    if (parado()) { rodando = false; desenhar(); return; }
    passo(Math.min(.05, (agora - ultimo) / 1000));
    ultimo = agora;
    desenhar();
    requestAnimationFrame(quadro);
  }
  function animar() {
    if (rodando || parado()) return;
    rodando = true; ultimo = performance.now();
    requestAnimationFrame(quadro);
  }

  /* ---------- estouro dourado (por cima de tudo, até de um diálogo aberto) ---------- */
  // Camada própria como popover: entra na camada do topo, acima até de um diálogo modal.
  const fx = document.createElement('canvas'), fctx = fx.getContext('2d'), temPopover = 'popover' in fx;
  fx.setAttribute('aria-hidden', 'true');
  if (temPopover) fx.popover = 'manual';
  fx.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;margin:0;padding:0;border:0;' +
    'background:transparent;overflow:visible;pointer-events:none;z-index:60';
  let fxRodando = false, fxUltimo = 0;
  function fxQuadro(agora) {
    const dt = Math.min(.05, (agora - fxUltimo) / 1000);
    fxUltimo = agora;
    fctx.clearRect(0, 0, W, H);
    for (let i = estouro.length - 1; i >= 0; i--) {
      const p = estouro[i];
      p.vida -= dt;
      if (p.vida <= 0) { estouro.splice(i, 1); continue; }
      p.vx *= .965; p.vy = p.vy * .965 + 60 * dt;
      p.x += p.vx * dt; p.y += p.vy * dt;
      fctx.globalAlpha = Math.min(1, p.vida / p.total * 1.6);
      fctx.drawImage(sprites[p.cor], p.x - p.tam / 2, p.y - p.tam / 2, p.tam, p.tam);
    }
    if (estouro.length) requestAnimationFrame(fxQuadro);
    else { fxRodando = false; if (temPopover && fx.matches(':popover-open')) fx.hidePopover(); fx.remove(); }
  }

  window.ambiente = {
    // estouro dourado saindo do centro de um elemento
    estourar(el) {
      if (calmo.matches || !el) return;
      if (!fx.isConnected) document.body.appendChild(fx);
      if (temPopover) { if (fx.matches(':popover-open')) fx.hidePopover(); fx.showPopover(); }   // reabre por cima do diálogo atual
      fx.width = W * dpr; fx.height = H * dpr;
      fctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      for (let i = 0; i < 40; i++) {
        const ang = rnd(0, 6.28), vel = rnd(120, 340), total = rnd(.9, 1.7);
        estouro.push({ x, y, vx: Math.cos(ang) * vel, vy: Math.sin(ang) * vel - 80, tam: rnd(14, 34), cor: 3 + ((Math.random() * 3) | 0), vida: total, total });
      }
      if (!fxRodando) { fxRodando = true; fxUltimo = performance.now(); requestAnimationFrame(fxQuadro); }
    },
  };

  addEventListener('pointermove', e => { mouse.x = e.clientX; mouse.y = e.clientY; }, { passive: true });
  document.documentElement.addEventListener('pointerleave', () => { mouse.x = mouse.y = -9999; });
  addEventListener('resize', () => { medir(); desenhar(); });   // as partículas fora da tela renascem sozinhas
  document.addEventListener('visibilitychange', animar);
  addEventListener('hashchange', animar);
  calmo.addEventListener('change', animar);
  sistemaEscuro.addEventListener('change', aplicarTema);
  new MutationObserver(aplicarTema).observe(raiz, { attributes: true, attributeFilter: ['data-tema'] });

  medir();
  aplicarTema();
  animar();
})();
