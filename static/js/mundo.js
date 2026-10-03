/* =====================================================================
   Mundo de cupons (mapa de fases no estilo do Super Mario Bros. Wii)
   Entrada: o JSON de GET /api/eu (fases, fase_atual, pontos_totais...).
   Cada cupom ativo é uma fase, em ordem de custo; a fase é liberada pelos
   pontos acumulados, que nunca diminuem (o avatar nunca volta).
   ===================================================================== */

/* avatar em pixel art (12x16), desenhado em SVG */
const SPRITE = (() => {
  const px = ['...GGGGG....', '..GGGGWGGGG.', '..HHHSSKS...', '.HSHSSSKSSS.', '.HSHHSSSKSSS', '.HHSSSSKKKK.',
              '...SSSSSSS..', '..GGBGGG....', '.GGGBGGBGGG.', 'GGGGBBBBGGGG', 'SSGBYBBYBGSS', 'SSSBBBBBBSSS',
              'SSBBBBBBBBSS', '..BBB..BBB..', '.OOO....OOO.', 'OOOO....OOOO'];
  const cor = {G:'#2fb24c', W:'#fff', H:'#6b3e1f', S:'#f6c9a0', K:'#1d1d1d', B:'#1e7fd8', Y:'#ffd21f', O:'#7a4320'};
  let r = '';
  px.forEach((linha, y) => [...linha].forEach((c, x) => {
    if (cor[c]) r += `<rect x="${x}" y="${y}" width="1.04" height="1.04" fill="${cor[c]}"/>`;
  }));
  return w => `<svg viewBox="0 0 12 16" width="${w}" height="${w * 4 / 3}" shape-rendering="crispEdges" aria-hidden="true">${r}</svg>`;
})();
const CADEADO = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path class="arco" d="M8 11V7.5a4 4 0 0 1 8 0V11" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/><rect x="5" y="10.5" width="14" height="10.5" rx="2.5" fill="#fff"/></svg>';

function criarMundo({aoResgatar, aoEntrar, aoAvancar = () => {}}) {
  const $m = id => document.getElementById(id);
  const raiz = $m('mundo'), cena = $m('cena'), palco = $m('palco'), svg = $m('trilhaSvg'), camadaNos = $m('nos');
  const avatar = $m('avatar'), salto = $m('salto'), sombraPos = $m('sombraPos'), balao = $m('balao'), btnPular = $m('pular');
  const PASSO = 150, MARGEM = 90, ALTURA = 340, BASE = 178, AMPL = 56, RAIO = 30, GAP = 17;
  let pts = [], segs = [], fases = [], dados = null, atual = 0, alvo = 0;
  let desenhado = false, pendente = null, emSequencia = false, pulando = false, aberto = null;
  const rodando = new Set(), esperas = new Set();

  salto.innerHTML = SPRITE(36);
  const visivel = () => cena.clientWidth > 0;
  const logado = () => !!dados?.usuario;
  const posicao = i => ({x: MARGEM + i * PASSO, y: BASE - Math.round(Math.sin(i * 1.1 + .4) * AMPL)});

  // Catmull-Rom -> Bézier: curva suave passando por todos os nós
  function curva(i) {
    const p0 = pts[Math.max(i - 1, 0)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(i + 2, pts.length - 1)];
    const c1 = {x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6};
    const c2 = {x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6};
    return `M${p1.x},${p1.y} C${c1.x},${c1.y} ${c2.x},${c2.y} ${p2.x},${p2.y}`;
  }

  // ---- utilitários: tudo que roda pode ser concluído de uma vez por "Pular" ----
  function rodar(el, quadros, opcoes) {
    const a = el.animate(quadros, opcoes);
    rodando.add(a);
    a.finished.catch(() => {}).finally(() => rodando.delete(a));
    return a;
  }
  function esperar(ms) {
    if (pulando || semMovimento()) return Promise.resolve();
    return new Promise(ok => {
      const fim = () => { clearTimeout(t); esperas.delete(fim); ok(); };
      const t = setTimeout(fim, ms);
      esperas.add(fim);
    });
  }
  function pular() {
    if (!emSequencia) return;
    pulando = true;
    rodando.forEach(a => a.finish());
    esperas.forEach(fim => fim());
  }

  const noEl = k => camadaNos.querySelector(`.no[data-k="${k}"]`);
  const posicionarAvatar = p => { avatar.style.transform = `translate(${p.x - 20}px, ${p.y - 86}px)`; };   // pés na borda do nó
  const centralizar = (x, suave) => cena.scrollTo({left: x - cena.clientWidth / 2, behavior: suave && !semMovimento() ? 'smooth' : 'auto'});

  // ---- desenho ----
  function desenhar(de) {
    fecharBalao(true);
    const n = fases.length;
    pts = Array.from({length: n + 1}, (_, i) => posicao(i));
    const largura = MARGEM + n * PASSO + 190;
    palco.style.width = largura + 'px';
    svg.setAttribute('width', largura);
    svg.setAttribute('viewBox', `0 0 ${largura} ${ALTURA}`);
    svg.innerHTML = pts.slice(0, -1).map((_, i) => {
      const d = curva(i);
      return `<g class="seg ${i < de ? 'aberto' : ''}" data-s="${i}"><path class="seg-trancado" d="${d}"/>
        <g class="seg-aberto"><path class="borda" d="${d}"/><path class="miolo" d="${d}"/></g><g class="pontos"></g></g>`;
    }).join('');
    segs = [...svg.querySelectorAll('.seg-trancado')];
    svg.querySelectorAll('.seg').forEach((g, i) => {   // pontinhos igualmente espaçados, longe dos nós
      const s = segs[i], L = s.getTotalLength(), ini = RAIO + 8, util = L - 2 * ini;
      const q = Math.max(2, Math.floor(util / GAP) + 1);
      let h = '';
      for (let j = 0; j < q; j++) {
        const p = s.getPointAtLength(ini + j * util / (q - 1));
        h += `<circle class="ponto" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.4"/>`;
      }
      g.querySelector('.pontos').innerHTML = h;
    });

    let nuvens = '';
    for (let i = 0; i * 250 < largura; i++) nuvens += `<div class="nuvem" style="left:${40 + i * 250 + (i % 3) * 40}px;top:${18 + (i % 2) * 30}px"></div>`;
    $m('nuvens').innerHTML = nuvens;

    camadaNos.innerHTML =
      `<div class="no inicio" style="left:${pts[0].x}px;top:${pts[0].y}px"><span class="no-face">★</span><span class="no-rotulo">Início</span></div>` +
      fases.map((f, i) => {
        const k = i + 1, q = pts[k];
        return `<button class="no ${k <= de ? 'liberado' : ''} ${f.resgates ? 'resgatado' : ''}" data-k="${k}"
            style="left:${q.x}px;top:${q.y}px" aria-expanded="false" aria-controls="balao">
          <span class="no-anel"></span>
          <span class="no-face no-face-trancada">${CADEADO}</span>
          <span class="no-face no-face-liberada">${k}</span>
          <span class="no-estrela" aria-hidden="true">★</span>
          <span class="no-rotulo">${esc(f.marca)}</span>
          <span class="no-falta"></span></button>`;
      }).join('') +
      `<div class="bandeira" style="left:${pts[n].x + 110}px;top:${pts[n].y - 100}px"></div>`;
    desenhado = true;
    atual = de;
    rotular();
    posicionarAvatar(pts[de]);
    marcarProximo();
    centralizar(pts[de].x, false);
    if (logado()) aoAvancar(de);
  }

  function rotular() {
    camadaNos.querySelectorAll('button.no').forEach(no => {
      const k = +no.dataset.k, f = fases[k - 1];
      no.setAttribute('aria-label', `Fase ${k}: ${f.marca}, ${no.classList.contains('liberado') ? 'liberada' : 'trancada'}` +
                                    (f.resgates ? `, resgatada ${f.resgates} vez(es)` : ''));
    });
  }

  function marcarProximo() {
    camadaNos.querySelectorAll('.no.proximo').forEach(e => e.classList.remove('proximo'));
    const prox = noEl(atual + 1);
    if (!prox || !logado()) return;
    const falta = fases[atual].custo - dados.pontos_totais;
    if (falta <= 0) return;   // vai ser liberada nesta sequência
    prox.classList.add('proximo');
    prox.querySelector('.no-falta').textContent = `faltam ${falta} pts`;
  }

  // ---- desbloqueio: o caminho se preenche > o avatar anda > o cadeado abre ----
  function revelarSegmento(i) {
    const g = svg.querySelector(`.seg[data-s="${i}"]`);
    g.classList.add('aberto');   // estado final já aplicado; as animações partem do estado anterior
    if (pulando || semMovimento()) return Promise.resolve();
    const pontos = [...g.querySelectorAll('.ponto')];
    const total = pontos.length * 45 + 320;
    rodar(g.querySelector('.seg-aberto'), [{opacity: 0}, {opacity: 1}], {duration: total, easing: EASE.entra, fill: 'backwards'});
    pontos.forEach((p, j) => rodar(p, [{opacity: 0, transform: 'scale(.3)'}, {opacity: 1, transform: 'scale(1)'}],
                                   {duration: 320, delay: j * 45, easing: EASE.mola, fill: 'backwards'}));
    return esperar(total * .75);   // o avatar sai antes do último ponto pousar (offset, não fila)
  }

  function andarSegmento(i) {
    const seg = segs[i], L = seg.getTotalLength(), fim = pts[i + 1];
    if (pulando || semMovimento()) { posicionarAvatar(fim); return Promise.resolve(); }
    const dur = Math.min(1100, Math.max(600, L * 3.4)), passos = Math.max(2, Math.round(L / 38));
    // o avatar segue a própria curva da estrada (offset-path), no compositor
    avatar.classList.add('andando');
    avatar.style.transform = 'none';
    avatar.style.offsetPath = `path("${seg.getAttribute('d')}")`;
    centralizar(fim.x, true);
    const anda = rodar(avatar, [{offsetDistance: '0%'}, {offsetDistance: '100%'}],
                       {duration: dur, easing: EASE.estado, fill: 'forwards'});
    // pulinhos: sobe desacelerando, desce acelerando; a sombra encolhe no ar
    const pulo = {duration: dur / passos, iterations: passos};
    rodar(salto, [{transform: 'none', easing: EASE.entra}, {transform: 'translateY(-7px)', offset: .5, easing: EASE.sai}, {transform: 'none'}], pulo);
    rodar(sombraPos, [{transform: 'none', easing: EASE.entra}, {transform: 'scaleX(.7)', offset: .5, easing: EASE.sai}, {transform: 'none'}], pulo);
    return anda.finished.catch(() => {}).then(() => {
      posicionarAvatar(fim);
      avatar.style.offsetPath = '';
      anda.cancel();
      avatar.classList.remove('andando');
    });
  }

  function liberarNo(k) {
    const no = noEl(k);
    no.classList.add('liberado');
    atual = k;
    rotular();
    marcarProximo();
    aoAvancar(k);
    anunciar(`Fase ${k} liberada: ${fases[k - 1].marca}!`);
    if (pulando || semMovimento()) return Promise.resolve();
    // o arco do cadeado gira para fora, o cadeado some e o número salta no lugar
    rodar(no.querySelector('.arco'), [{transform: 'none'}, {transform: 'translateY(-3px) rotate(-30deg)'}],
          {duration: 220, easing: EASE.entra, fill: 'forwards'});
    rodar(no.querySelector('.no-face-trancada'),
          [{opacity: 1, transform: 'scale(1)', filter: 'blur(0)'}, {opacity: 0, transform: 'scale(.85)', filter: 'blur(3px)'}],
          {duration: 200, delay: 180, easing: EASE.sai, fill: 'backwards'});
    rodar(no.querySelector('.no-face-liberada'), [{opacity: 0, transform: 'scale(.6)'}, {opacity: 1, transform: 'scale(1)'}],
          {duration: 560, delay: 260, easing: EASE.molaViva, fill: 'backwards'});
    rodar(no.querySelector('.no-anel'), [{opacity: .8, transform: 'scale(.9)'}, {opacity: 0, transform: 'scale(1.7)'}],
          {duration: 650, delay: 240, easing: EASE.entra});
    soltarMoeda(pts[k], 300);
    return esperar(520);
  }

  function soltarMoeda(p, atraso) {
    const m = document.createElement('div');
    m.className = 'moeda';
    m.style.cssText = `left:${p.x}px;top:${p.y - 44}px`;
    palco.append(m);
    rodar(m, [{opacity: 0, transform: 'translateY(0) scale(.7) rotateY(0)'},
              {opacity: 1, offset: .2},
              {opacity: 0, transform: 'translateY(-56px) scale(1) rotateY(540deg)'}],
          {duration: 720, delay: atraso, easing: EASE.entra, fill: 'backwards'}).finished.catch(() => {}).finally(() => m.remove());
  }

  async function sequencia() {
    if (emSequencia) return;
    emSequencia = true;
    fecharBalao(true);
    btnPular.classList.add('visivel');
    while (atual < alvo) {
      const k = atual + 1;
      await revelarSegmento(k - 1);
      await andarSegmento(k - 1);
      await liberarNo(k);
    }
    btnPular.classList.remove('visivel');
    pulando = false;
    emSequencia = false;
    if (pendente && visivel()) aplicar();   // chegou dado novo durante a animação
  }

  // ---- dados -> tela ----
  function aplicar() {
    const {p, de} = pendente;
    const redesenhar = !desenhado || p.fases.length !== fases.length || (dados?.usuario?.id ?? null) !== (p.usuario?.id ?? null);
    if (redesenhar && emSequencia) { pular(); return; }   // termina a animação e aplica no fim dela
    pendente = null;
    const eraLogado = dados?.usuario?.id;
    dados = p;
    fases = p.fases;
    alvo = p.fase_atual;
    if (redesenhar) desenhar(Math.min(de ?? (desenhado && eraLogado === p.usuario?.id ? atual : alvo), alvo));
    else atualizarNos();
    resumo(p);
    if (alvo > atual) sequencia();
  }

  function atualizarNos() {
    camadaNos.querySelectorAll('button.no').forEach(no => {
      const f = fases[no.dataset.k - 1], novo = f.resgates && !no.classList.contains('resgatado');
      no.classList.toggle('resgatado', !!f.resgates);
      if (novo && !semMovimento()) rodar(no.querySelector('.no-estrela'), [{opacity: 0, transform: 'scale(.6)'}, {opacity: 1, transform: 'scale(1)'}],
                                         {duration: 520, delay: 200, easing: EASE.molaViva, fill: 'backwards'});
    });
    rotular();
    marcarProximo();
    if (aberto && !emSequencia) abrirBalao(aberto, true, false);   // só atualiza o conteúdo
  }

  // ---- balão da fase ----
  function abrirBalao(k, instantaneo, focar = instantaneo) {
    const no = noEl(k), f = fases[k - 1], liberada = logado() && k <= atual;
    let acao;
    if (!logado()) acao = '<button class="btn pequeno" data-entrar>Entrar para jogar</button>';
    else if (!liberada) acao = `<small>Faltam ${f.custo - dados.pontos_totais} pontos acumulados</small>`;
    else if (f.resgatavel) acao = `<button class="btn lima pequeno" data-resgatar="${f.id}">Resgatar</button>`;
    else acao = `<small>Saldo: ${dados.usuario.pontos} de ${f.custo}</small>`;
    balao.innerHTML = `<div class="balao-topo"><span class="selo-fase ${liberada ? 'liberada' : ''}">Fase ${k}</span>
        <span class="estado">${liberada ? (f.resgates ? `Resgatada ${f.resgates}x` : 'Liberada') : 'Trancada'}</span></div>
      <b>${esc(f.marca)}</b><p>${esc(f.descricao)}</p>
      <div class="balao-rodape"><span class="custo">${f.custo} pts</span>${acao}</div>`;
    // posição relativa ao bloco, presa às bordas; a seta continua apontando para o nó
    const r = raiz.getBoundingClientRect(), n = no.getBoundingClientRect();
    const cx = n.left + n.width / 2 - r.left, meia = 125;
    const left = Math.min(Math.max(cx, meia + 8), r.width - meia - 8);
    balao.style.left = left + 'px';
    balao.style.top = (n.top - r.top - 14) + 'px';
    balao.style.setProperty('--seta', (cx - left + meia) + 'px');
    if (aberto && aberto !== k) noEl(aberto)?.setAttribute('aria-expanded', 'false');
    no.setAttribute('aria-expanded', 'true');
    aberto = k;
    balao.classList.toggle('instantaneo', instantaneo || semMovimento());
    balao.classList.remove('aberto');
    balao.classList.add('preparando');
    balao.offsetWidth;   // aplica o estado inicial antes de animar
    balao.classList.remove('preparando');
    balao.classList.add('aberto');
    if (focar) balao.querySelector('button')?.focus();
  }

  function fecharBalao(instantaneo) {
    if (!aberto) return;
    noEl(aberto)?.setAttribute('aria-expanded', 'false');
    aberto = null;
    balao.classList.toggle('instantaneo', !!instantaneo || semMovimento());
    balao.classList.remove('aberto');
  }

  // ---- faixa de progresso ----
  function resumo(p) {
    const n = p.fases.length, prox = p.proximo_cupom;
    $m('mundoResumo').textContent = n ? `${p.fase_atual} de ${n} fases liberadas` : '';
    if (!n) {
      $m('pTitulo').textContent = 'Nenhum cupom cadastrado ainda.';
      $m('pSub').textContent = 'As fases aparecem aqui assim que as marcas parceiras entrarem.';
    } else if (!p.usuario) {
      $m('pTitulo').textContent = 'Entre na sua conta para começar a jornada.';
      $m('pSub').textContent = 'Cada fase é um cupom de uma marca parceira. Recicle para avançar!';
    } else if (prox) {
      $m('pTitulo').textContent = `Faltam ${p.faltam_pontos} pontos para liberar ${prox.marca}`;
      $m('pSub').textContent = `Cerca de ${p.faltam_itens} itens reciclados · ${p.pontos_totais} pontos acumulados`;
    } else {
      $m('pTitulo').textContent = 'Você liberou todas as fases!';
      $m('pSub').textContent = `${p.pontos_totais} pontos acumulados · toque numa fase para resgatar`;
    }
    const anterior = p.fase_atual ? p.fases[p.fase_atual - 1].custo : 0;
    const frac = !p.usuario ? 0 : prox ? (p.pontos_totais - anterior) / (prox.custo - anterior) : 1;
    $m('pBarra').style.transform = `scaleX(${Math.max(0, Math.min(1, frac))})`;
    $m('saldoMundo').hidden = !p.usuario;
    if (p.usuario) contar($m('pSaldo'), p.usuario.pontos);
  }
  const anunciar = msg => { $m('anunciador').textContent = msg; };

  // ---- eventos ----
  camadaNos.addEventListener('click', e => {
    const no = e.target.closest('button.no');
    if (!no || emSequencia) return;
    const k = +no.dataset.k, viaTeclado = veioDoTeclado(e);   // teclado: sem animação
    aberto === k ? fecharBalao(viaTeclado) : abrirBalao(k, viaTeclado);
  });
  balao.addEventListener('click', e => {
    const b = e.target.closest('[data-resgatar], [data-entrar]');
    if (!b) return;
    if (b.dataset.resgatar) aoResgatar(+b.dataset.resgatar, b, veioDoTeclado(e));
    else aoEntrar(b, veioDoTeclado(e));
  });
  document.addEventListener('pointerdown', e => {
    if (aberto && !balao.contains(e.target) && !e.target.closest('button.no')) fecharBalao();
  });
  raiz.addEventListener('keydown', e => {
    if (e.key === 'Escape' && aberto) { const k = aberto; fecharBalao(true); noEl(k)?.focus(); return; }
    const no = e.target.closest?.('button.no');
    if (!no || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return;   // direcional, como no GamePad
    e.preventDefault();
    noEl(+no.dataset.k + (e.key === 'ArrowRight' ? 1 : -1))?.focus();
  });
  cena.addEventListener('scroll', () => {
    if (aberto && !emSequencia) fecharBalao(true);
    // parallax leve: as nuvens andam mais devagar que o chão
    $m('nuvens').style.transform = semMovimento() ? '' : `translateX(${cena.scrollLeft * .35}px)`;
  }, {passive: true});
  btnPular.addEventListener('click', pular);
  // flutuação pausada quando o mapa não está na tela
  new IntersectionObserver(([e]) => raiz.classList.toggle('fora-da-tela', !e.isIntersecting)).observe(cena);

  return {
    // de: fase em que o avatar estava na última visita (a animação parte dali)
    definir(p, de) {
      pendente = {p, de: pendente?.de ?? de};
      if (visivel()) aplicar();
    },
    // chamado quando a tela de fases aparece: só então desenha/anima (precisa do tamanho real)
    aoMostrar() {
      if (pendente) aplicar();
      else if (desenhado && !emSequencia) centralizar(pts[atual].x, false);
    },
    aoEsconder() { fecharBalao(true); pular(); },
  };
}
