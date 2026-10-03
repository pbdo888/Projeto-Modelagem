/* =====================================================================
   McCrea · front-end (consome a API do app.py sem alterá-la)
   ===================================================================== */
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tentar = fn => async (...a) => { try { await fn(...a); } catch (e) { aviso(e.message, 'erro'); } };
const guardar = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} };
const ler = k => { try { return localStorage.getItem(k); } catch { return null; } };
const primeiroNome = u => u.nome.split(' ')[0];

let user = null, progresso = null, userPos = null, nearest = null, adminToken = null, adminOrigem = null;
let map = null, mapaPronto = null, pinos = [], me = null;
let miniMapa = null, pinoCasa = null, casaPos = null, passo = 0, soEndereco = false;
let mapaAdmin = null, pinosAdmin = [], novoPonto = null, novoPino = null;

async function api(url, body, admin) {
  const headers = {'Content-Type': 'application/json'};
  if (admin) headers['X-Admin-Token'] = adminToken || '';
  const r = await fetch(url, body ? {method: 'POST', headers, body: JSON.stringify(body)} : {headers});
  const j = await r.json().catch(() => ({}));
  if (admin && r.status === 401) sairAdmin(true);
  if (!r.ok) throw new Error(j.erro || 'Erro inesperado');
  return j;
}

async function apiForm(url, method, form) {   // envio com arquivo (multipart), sempre com o token de admin
  const r = await fetch(url, {method, headers: {'X-Admin-Token': adminToken || ''}, body: form});
  const j = await r.json().catch(() => ({}));
  if (r.status === 401) sairAdmin(true);
  if (!r.ok) throw new Error(j.erro || 'Erro inesperado');
  return j;
}

/* =====================================================================
   Mundo de cupons
   ===================================================================== */
const mundo = criarMundo({
  aoResgatar: tentar(async (id, botao, viaTeclado) => {
    const f = progresso.fases.find(x => x.id === id);
    const r = await api('/api/resgatar', {cupom_id: id});
    $('codigoMarca').textContent = `${f.marca}: ${f.descricao}`;
    $('codigo').innerHTML = [...r.codigo].map(ch => `<span>${esc(ch)}</span>`).join('');
    abrirDeOrigem($('dlgCodigo'), botao, viaTeclado);
    // código "digitado" letra a letra: evento raro, pode ter mais personalidade
    if (!viaTeclado && !semMovimento()) $('codigo').querySelectorAll('span').forEach((s, i) =>
      s.animate([{opacity: 0, transform: 'translateY(8px)'}, {opacity: 1, transform: 'none'}],
                {duration: 360, delay: 220 + i * 40, easing: EASE.mola, fill: 'backwards'}));
    await carregarUsuario();
  }),
  aoEntrar: (botao, viaTeclado) => abrirEntrar(botao, viaTeclado),
  aoAvancar: n => {   // fase que o usuário já viu o avatar alcançar
    if (!user) return;
    guardar('fase_' + user.id, n);
    atualizarBlocoMundo();
  },
});

/* =====================================================================
   Telas: menu de blocos + navegação (hash) com View Transitions
   ===================================================================== */
const ORDEM = ['inicio', 'noticias', 'mapa', 'fases', 'perfil', 'admin'];
let telaAtual = null, proximaNav = null;
const telaEl = n => $('tela-' + n);
const blocoDe = n => document.querySelector(`.bloco-menu[data-bloco="${n}"]`);
const nomeDoHash = () => { const n = location.hash.replace(/^#\/?/, ''); return ORDEM.includes(n) ? n : 'inicio'; };

function navegar(nome, opcoes = {}) {
  if (nome === 'admin' && !adminToken) return abrirAdmin(opcoes.origem, opcoes.viaTeclado);
  proximaNav = opcoes;
  if (location.hash === '#/' + nome) mostrarTela(nome);
  else location.hash = '#/' + nome;   // o hashchange chama mostrarTela (e o "voltar" do navegador funciona)
}
addEventListener('hashchange', () => mostrarTela(nomeDoHash()));

function mostrarTela(nome) {
  if (nome === 'admin' && !adminToken) { history.replaceState(null, '', '#/inicio'); nome = 'inicio'; }
  const op = proximaNav || {}, anterior = telaAtual;
  proximaNav = null;
  if (nome === anterior) return;
  const trocar = () => {
    if (anterior === 'fases') mundo.aoEsconder();
    ORDEM.forEach(n => { telaEl(n).hidden = n !== nome; });
    telaAtual = nome;
    document.querySelectorAll('.dock button').forEach(b => {
      const alvo = b.dataset.nav || (b.id === 'dockAdmin' ? 'admin' : '');
      alvo === nome ? b.setAttribute('aria-current', 'page') : b.removeAttribute('aria-current');
    });
    $('topoTitulo').textContent = telaEl(nome).dataset.titulo;
    document.title = nome === 'inicio' ? 'McCrea' : `${telaEl(nome).dataset.titulo} · McCrea`;
    scrollTo(0, 0);
    aoMostrar(nome);
  };
  // primeira tela, teclado ou movimento reduzido: troca instantânea
  if (!anterior || op.viaTeclado || semMovimento()) return trocar();
  const dir = ORDEM.indexOf(nome) >= ORDEM.indexOf(anterior) ? 1 : -1;
  if (!document.startViewTransition) {
    trocar();
    return entrarSuave(telaEl(nome), {x: 28 * dir, y: 0, duracao: 360});
  }
  // bloco do menu <-> tela: o mesmo view-transition-name nos dois lados faz um virar o outro
  const raiz = document.documentElement;
  const de = anterior === 'inicio' && op.origem?.closest?.('.bloco-menu') ? blocoDe(nome) : null;
  const volta = nome === 'inicio' ? blocoDe(anterior) : null;
  raiz.style.setProperty('--dir', dir);
  raiz.dataset.vt = de || volta ? 'expande' : 'desliza';
  if (de) de.style.viewTransitionName = 'expande';
  if (volta) telaEl(anterior).style.viewTransitionName = 'expande';
  const vt = document.startViewTransition(() => {
    trocar();
    if (de) { de.style.viewTransitionName = ''; telaEl(nome).style.viewTransitionName = 'expande'; }
    if (volta) { telaEl(anterior).style.viewTransitionName = ''; volta.style.viewTransitionName = 'expande'; }
  });
  vt.finished.finally(() => {
    [de, volta, telaEl(nome), telaEl(anterior)].forEach(el => { if (el) el.style.viewTransitionName = ''; });
    delete raiz.dataset.vt;
  });
}

function aoMostrar(nome) {
  if (nome === 'mapa') map ? map.resize() : initMap().catch(() => mapaIndisponivel($('map')));
  if (nome === 'fases') mundo.aoMostrar();
  if (nome === 'noticias') { marcarPonto(); tocarCarrossel(); }
  if (nome === 'admin') prepararMapaAdmin();
}

/* ---------- cliques: data-nav (telas) e data-acao (ações) ---------- */
const ACOES = {
  'entrar': (el, kb) => abrirEntrar(el, kb),
  'cadastro': (el, kb) => abrirCadastro(el, kb),
  'admin': (el, kb) => adminToken ? navegar('admin', {origem: el, viaTeclado: kb}) : abrirAdmin(el, kb),
  'fechar': (el, kb) => fecharAnimado(el.closest('dialog'), kb),
  'passo-voltar': () => mostrarPasso(passo - 1, -1),
  'localizar': () => localizarEndereco(),
  'endereco': (el, kb) => abrirEndereco(el, kb),
  'sair': () => sair(),
  'cartaz-anterior': () => passarCartaz(-1),
  'cartaz-proximo': () => passarCartaz(1),
  'ir-cartaz': el => { irCartaz(+el.dataset.i); tocarCarrossel(); },
  'abrir-anuncio': (el, kb) => abrirAnuncio(+el.dataset.id, el, kb),
  'sair-admin': () => sairAdmin(),
  'planilha': () => baixarPlanilha(),
  'depositar': () => depositar(),
  'novo-cupom': () => novoCupom(),
  'nova-maquina': () => novaMaquina(),
  'cancelar-anuncio': () => limparFormAnuncio(),
  'editar-anuncio': el => editarAnuncio(+el.dataset.id),
  'alternar-anuncio': el => alternarAnuncio(+el.dataset.id),
  'excluir-anuncio': el => excluirAnuncio(+el.dataset.id),
};
document.addEventListener('click', e => {
  const nav = e.target.closest('[data-nav]');
  if (nav) {
    e.preventDefault();
    return navegar(nav.dataset.nav, {origem: nav, viaTeclado: veioDoTeclado(e)});
  }
  const el = e.target.closest('[data-acao]');
  if (el) ACOES[el.dataset.acao]?.(el, veioDoTeclado(e), e);
});

/* =====================================================================
   Conta
   ===================================================================== */
// Carrega o usuário da sessão (cookie). Sem sessão, a API responde 401 e a página fica como visitante.
async function carregarUsuario() {
  const p = await api('/api/eu');
  progresso = p;
  user = p.usuario;
  mostrarConta();
  if (user.lat != null && (!userPos || userPos.lat !== user.lat || userPos.lng !== user.lng)) {
    definirPosicao(user.lat, user.lng).catch(() => {});
  }
  // a animação do mapa parte da última fase que o avatar alcançou diante do usuário
  const visto = ler('fase_' + user.id);
  mundo.definir(p, visto == null ? p.fase_atual : Math.min(+visto, p.fase_atual));
  atualizarBlocoMundo();
  return p;
}

async function carregarVisitante() {
  progresso = null;
  user = null;
  const fases = (await api('/api/cupons')).map((c, i) => ({...c, fase: i + 1, liberada: false, resgatavel: false, resgates: 0}));
  mundo.definir({usuario: null, fases, fase_atual: 0, pontos_totais: 0, proximo_cupom: null, faltam_pontos: 0, faltam_itens: 0}, 0);
  mostrarConta();
  atualizarBlocoMundo();
}

function mostrarConta() {
  $('auth').hidden = !!user;
  $('chip').hidden = !user;
  $('login').hidden = !!user;
  $('perfil').hidden = !user;
  if (!user) {
    $('bmPerfilNome').textContent = 'Sua conta';
    $('bmPerfilTxt').textContent = 'Entre ou crie sua conta';
    return;
  }
  const p = progresso, nome = primeiroNome(user);
  if (!$('chipPontos')) $('chip').innerHTML = `<span class="mini">${SPRITE(22)}</span><span><span id="chipNome"></span><small><span id="chipPontos">${user.pontos}</span> pontos</small></span>`;
  $('chipNome').textContent = nome;
  contar($('chipPontos'), user.pontos);
  $('chip').setAttribute('aria-label', `Sua conta: ${nome}, ${user.pontos} pontos`);
  $('bmPerfilNome').textContent = nome;
  $('bmPerfilTxt').textContent = `${user.pontos} pontos de saldo`;
  const end = user.logradouro
    ? `${esc(user.logradouro)}, ${esc(user.numero)}${user.complemento ? ' · ' + esc(user.complemento) : ''}<br>${esc(user.bairro)}, ${esc(user.cidade)} - ${esc(user.uf)}`
    : 'Endereço não cadastrado';
  $('perfil').innerHTML = `
    <div class="bloco">
      <div class="perfil-topo"><div class="mini">${SPRITE(44)}</div>
        <div><b>${esc(user.nome)}</b><small class="dica">${esc(user.email)}</small></div></div>
      <div class="numeros">
        <div class="numero"><b>${user.pontos}</b><small>pontos de saldo</small></div>
        <div class="numero"><b>${p.fase_atual}/${p.fases.length}</b><small>fases liberadas</small></div>
      </div>
      <div class="acoes-perfil"><button class="btn" data-nav="fases">Ver minhas fases</button>
        <button class="btn branco" data-acao="sair">Sair da conta</button></div>
    </div>
    <div class="bloco">
      <h2 style="margin-bottom:12px"><i class="ico lima"></i>Sua casa</h2>
      <div class="endereco-casa"><b>Endereço fixo</b>${end}</div>
      <div class="acoes-perfil"><button class="btn branco" data-acao="endereco">Alterar endereço</button>
        <button class="btn branco" data-nav="mapa">Ver no mapa</button></div>
    </div>`;
}

function atualizarBlocoMundo() {
  const p = progresso;
  let frac = 0, txt = 'Entre para começar a jornada', nova = false;
  if (p && p.fases.length) {
    const prox = p.proximo_cupom, anterior = p.fase_atual ? p.fases[p.fase_atual - 1].custo : 0;
    frac = prox ? (p.pontos_totais - anterior) / (prox.custo - anterior) : 1;
    txt = prox ? `Fase ${p.fase_atual} de ${p.fases.length} · faltam ${p.faltam_pontos} pontos` : 'Todas as fases liberadas!';
    const visto = ler('fase_' + user.id);
    nova = visto != null && p.fase_atual > +visto;   // selo estático; some depois que o usuário vê a animação
  } else if (p) {
    txt = 'Nenhum cupom cadastrado ainda';
  }
  $('bmMundoTxt').textContent = txt;
  $('bmMundoBarra').style.transform = `scaleX(${Math.max(0, Math.min(1, frac))})`;
  $('bmMundoSelo').hidden = !nova;
}

const sair = tentar(async () => {
  await api('/api/logout', {});
  limparPosicao();
  await carregarVisitante();
  aviso('Você saiu da sua conta.');
});

/* ---------- entrar ---------- */
function abrirEntrar(origem, viaTeclado) {
  $('dlgEntrar').querySelector('.msg').textContent = '';
  abrirDeOrigem($('dlgEntrar'), origem, viaTeclado);
  $('l_email').focus();
}

$('formEntrar').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    await api('/api/login', {email: $('l_email').value, senha: $('l_senha').value});
  } catch (err) {
    if (err.message.startsWith('conta antiga')) {   // conta criada antes das senhas: completa o cadastro
      const email = $('l_email').value;
      abrirCadastro(null, true);
      $('c_email').value = email;
      aviso('Encontramos sua conta antiga. Complete o cadastro para criar sua senha; seus pontos serão mantidos.');
    } else {
      aviso(err.message, 'erro');
    }
    return;
  }
  $('l_senha').value = '';
  fecharAnimado($('dlgEntrar'));
  await tentar(carregarUsuario)();
  if (user) aviso(`Olá, ${primeiroNome(user)}!`);
});

/* ---------- criar conta (3 etapas) e alterar endereço ---------- */
const CAMPOS_ENDERECO = ['e_cep', 'e_rua', 'e_num', 'e_comp', 'e_bairro', 'e_cidade', 'e_uf'];

function abrirCadastro(origem, viaTeclado) {
  soEndereco = false;
  $('formCadastro').reset();
  $('cadTitulo').innerHTML = '<i class="ico lima"></i>Criar conta';
  $('passos').hidden = false;
  $('termos').hidden = false;
  const max = new Date();
  max.setFullYear(max.getFullYear() - 13);
  $('c_nasc').max = max.toISOString().slice(0, 10);
  definirCasa(null);
  mostrarPasso(0, 0);
  abrirDeOrigem($('dlgCadastro'), origem, viaTeclado);
  $('c_nome').focus();
}

function abrirEndereco(origem, viaTeclado) {
  soEndereco = true;
  $('formCadastro').reset();
  $('cadTitulo').innerHTML = '<i class="ico"></i>Alterar endereço';
  $('passos').hidden = true;
  $('termos').hidden = true;
  const v = {e_cep: user.cep, e_rua: user.logradouro, e_num: user.numero, e_comp: user.complemento,
             e_bairro: user.bairro, e_cidade: user.cidade, e_uf: user.uf};
  CAMPOS_ENDERECO.forEach(id => { $(id).value = v[id] ?? ''; });
  abrirDeOrigem($('dlgCadastro'), origem, viaTeclado);   // abre antes do mini mapa, que precisa do tamanho visível
  mostrarPasso(2, 0);
  definirCasa(user.lat != null ? {lat: user.lat, lng: user.lng} : null);
}

// dir: 1 avança, -1 volta, 0 sem animação. A etapa entra pelo lado de onde o usuário "veio".
function mostrarPasso(n, dir = 1) {
  passo = n;
  $('dlgCadastro').querySelector('.msg').textContent = '';
  document.querySelectorAll('#formCadastro fieldset').forEach(f => { f.hidden = +f.dataset.passo !== n; });
  document.querySelectorAll('#passos li').forEach((li, i) => li.classList.toggle('feito', i <= n));
  $('btnVoltar').hidden = n === 0 || soEndereco;
  $('btnAvancar').textContent = soEndereco ? 'Salvar endereço' : n < 2 ? 'Continuar' : 'Criar conta';
  if (dir) entrarSuave(document.querySelector(`#formCadastro fieldset[data-passo="${n}"]`), {x: 24 * dir, y: 0, duracao: 320});
  if (n === 2) prepararMiniMapa();
}

function etapaValida() {   // usa as regras do HTML (required, minlength…) só dos campos visíveis
  for (const el of document.querySelectorAll(`#formCadastro fieldset[data-passo="${passo}"] [required]`)) {
    if (!el.checkValidity()) { el.reportValidity(); return false; }
  }
  if (passo === 0 && $('c_senha').value !== $('c_senha2').value) {
    aviso('As senhas não são iguais.', 'erro');
    return false;
  }
  return true;
}

$('formCadastro').addEventListener('submit', tentar(async e => {
  e.preventDefault();
  if (!etapaValida()) return;
  if (passo < 2) return mostrarPasso(passo + 1, 1);
  if (!casaPos) {   // localiza automaticamente e pede para o usuário conferir o pino antes de enviar
    if (await localizarEndereco()) aviso('Confira se o pino azul está na sua casa e clique de novo para confirmar.');
    return;
  }
  const endereco = {cep: $('e_cep').value, logradouro: $('e_rua').value, numero: $('e_num').value,
                    complemento: $('e_comp').value, bairro: $('e_bairro').value, cidade: $('e_cidade').value,
                    uf: $('e_uf').value, ...casaPos};
  if (soEndereco) {
    await api('/api/eu/endereco', endereco);
    fecharAnimado($('dlgCadastro'));
    userPos = null;
    await carregarUsuario();
    return aviso('Endereço atualizado!');
  }
  if (!$('c_termos').checked) throw new Error('Para criar a conta, aceite os termos de uso e a política de privacidade.');
  await api('/api/cadastro', {
    nome: $('c_nome').value, email: $('c_email').value, senha: $('c_senha').value,
    nascimento: $('c_nasc').value, telefone: $('c_tel').value, sexo: $('c_sexo').value,
    estado_civil: $('c_ec').value, moradores: $('c_mor').value, como_conheceu: $('c_como').value,
    aceite_termos: true, aceita_ofertas: $('c_ofertas').checked, ...endereco});
  fecharAnimado($('dlgCadastro'));
  await carregarUsuario();
  aviso(`Conta criada! Bem-vindo, ${primeiroNome(user)}.`);
}));

// máscaras simples
$('c_tel').addEventListener('input', e => {
  const d = e.target.value.replace(/\D/g, '').slice(0, 11);
  e.target.value = d.length > 10 ? `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
                 : d.length > 6 ? `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
                 : d.length > 2 ? `(${d.slice(0, 2)}) ${d.slice(2)}` : d;
});
$('e_cep').addEventListener('input', e => {
  const d = e.target.value.replace(/\D/g, '').slice(0, 8);
  e.target.value = d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
  if (d.length === 8) buscarCep(d);
});
// mudou o endereço: o pino antigo deixa de valer
['e_cep', 'e_rua', 'e_num', 'e_bairro', 'e_cidade', 'e_uf'].forEach(id => $(id).addEventListener('change', () => definirCasa(null)));

async function buscarCep(cep) {   // ViaCEP preenche rua, bairro, cidade e UF
  try {
    const r = await (await fetch(`https://viacep.com.br/ws/${cep}/json/`)).json();
    if (r.erro) return aviso('CEP não encontrado. Preencha o endereço manualmente.', 'erro');
    $('e_rua').value = r.logradouro || $('e_rua').value;
    $('e_bairro').value = r.bairro || $('e_bairro').value;
    $('e_cidade').value = r.localidade || '';
    $('e_uf').value = r.uf || '';
    definirCasa(null);
    $('e_num').focus();
  } catch {
    aviso('Não foi possível consultar o CEP agora. Preencha o endereço manualmente.', 'erro');
  }
}

/* =====================================================================
   Mapas (MapLibre + OpenFreeMap, sem chave e sem custo)
   ===================================================================== */
const ESTILO_MAPA = 'https://tiles.openfreemap.org/styles/positron';   // estilo claro, combina com o visual
const CENTRO_SP = [-46.6333, -23.5505];   // MapLibre usa [longitude, latitude]

function marcador(pos, cor, titulo, alvo = map, arrastavel = false) {
  const m = new maplibregl.Marker({color: cor, draggable: arrastavel})
    .setLngLat([pos.lng, pos.lat])
    .setPopup(new maplibregl.Popup({offset: 28, closeButton: false}).setText(titulo))
    .addTo(alvo);
  m.getElement().title = titulo;
  return m;
}

function mapaIndisponivel(el) {
  el.innerHTML = '<div class="mapa-vazio">Não foi possível carregar o mapa. Verifique sua conexão com a internet.</div>';
}

function desenharRota(a, b) {   // linha reta tracejada = distância euclidiana usada no cálculo
  mapaPronto?.then(() => map.getSource('rota').setData({
    type: 'Feature', properties: {},
    geometry: {type: 'LineString', coordinates: a && b ? [[a.lng, a.lat], [b.lng, b.lat]] : []}}));
}

async function carregarMaquinas() {
  if (!map) return;
  pinos.forEach(p => p.remove());
  pinos = (await api('/api/maquinas')).map(m => marcador({lat: m.lat, lng: m.lng}, '#2fb24c', m.nome));
}

// A posição do usuário é sempre o endereço fixo do cadastro (sem localização em tempo real)
async function definirPosicao(lat, lng) {
  userPos = {lat, lng};
  if (map) {
    me?.remove();
    me = marcador(userPos, '#1a73e8', 'Sua casa');
  }
  await atualizarProxima(true);
}

function limparPosicao() {
  userPos = nearest = null;
  me?.remove();
  me = null;
  desenharRota(null);
  $('proxima').className = 'dica';
  $('proxima').textContent = 'Entre ou crie sua conta para ver as máquinas mais próximas do seu endereço.';
  $('bmMapaTxt').textContent = 'Máquinas da cidade';
}

async function atualizarProxima(ajustar) {
  if (!userPos) return;
  const lista = await api(`/api/maquinas/proximas?lat=${userPos.lat}&lng=${userPos.lng}`);
  nearest = lista[0];
  $('bmMapaTxt').textContent = `Mais perto: ${nearest.nome} · ${nearest.distancia_km} km`;
  $('proxima').className = 'tiles';
  $('proxima').innerHTML = lista.map((m, i) => {
    const pct = Math.round(100 * m.ocupacao / m.capacidade);
    return `<div class="tile ${i ? '' : 'destaque'}"><div class="num">${i + 1}</div>
      <div class="info"><b>${esc(m.nome)}</b><small>${i ? '' : 'Mais próxima · '}${esc(m.bairro)} · ${pct}% cheia</small>
      <div class="ocupa"><i class="${pct > 80 ? 'cheia' : ''}" style="transform:scaleX(${Math.min(pct, 100) / 100})"></i></div></div>
      <span class="pilula">${m.distancia_km} km</span></div>`;
  }).join('');
  if (!map) return;
  const alvo = {lat: nearest.lat, lng: nearest.lng};
  desenharRota(userPos, alvo);
  if (ajustar) {   // enquadra casa + máquina só depois que o mapa terminou de carregar
    const casa = userPos;
    mapaPronto?.then(() => map.fitBounds(
      [[Math.min(casa.lng, alvo.lng), Math.min(casa.lat, alvo.lat)], [Math.max(casa.lng, alvo.lng), Math.max(casa.lat, alvo.lat)]],
      {padding: 80, maxZoom: 15, duration: semMovimento() ? 0 : 800}));
  }
}

// criado só quando a tela do mapa aparece (o MapLibre precisa do tamanho real)
async function initMap() {
  if (map) return;
  if (!window.maplibregl) return mapaIndisponivel($('map'));
  $('map').innerHTML = '';
  map = new maplibregl.Map({container: 'map', style: ESTILO_MAPA, center: CENTRO_SP, zoom: 11,
                            attributionControl: {compact: true}});
  map.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right');
  map.addControl(new maplibregl.FullscreenControl(), 'top-right');
  mapaPronto = new Promise(ok => map.on('load', () => {
    map.addSource('rota', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'rota', type: 'line', source: 'rota', layout: {'line-cap': 'round'},
                  paint: {'line-color': '#1fb3f5', 'line-width': 4, 'line-dasharray': [1, 2]}});
    ok();
  }));
  map.on('error', e => console.warn('Mapa:', e.error?.message || e));
  await carregarMaquinas();
  if (userPos) await definirPosicao(userPos.lat, userPos.lng);
}

function prepararMiniMapa() {   // criado só quando o diálogo está visível
  if (!window.maplibregl) return mapaIndisponivel($('miniMapa'));
  if (miniMapa) return miniMapa.resize();
  miniMapa = new maplibregl.Map({container: 'miniMapa', style: ESTILO_MAPA, center: CENTRO_SP, zoom: 10,
                                 attributionControl: {compact: true}});
  miniMapa.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right');
  miniMapa.on('click', e => definirCasa({lat: e.lngLat.lat, lng: e.lngLat.lng}));
  if (casaPos) definirCasa(casaPos);
}

function definirCasa(pos) {   // pino azul (arrastável) com a casa do usuário no mini mapa
  casaPos = pos;
  $('pinoInfo').textContent = pos
    ? `Casa marcada em ${pos.lat.toFixed(5)}, ${pos.lng.toFixed(5)}. Se não estiver certo, clique no mapa ou arraste o pino.`
    : 'Clique em "Localizar endereço no mapa" e confira o pino azul. Você também pode clicar no mapa para marcar sua casa.';
  if (!miniMapa) return;
  pinoCasa?.remove();
  pinoCasa = null;
  if (!pos) return;
  pinoCasa = marcador(pos, '#1a73e8', 'Sua casa', miniMapa, true);
  pinoCasa.on('dragend', () => {
    const p = pinoCasa.getLngLat();
    definirCasa({lat: p.lat, lng: p.lng});
  });
  miniMapa.jumpTo({center: [pos.lng, pos.lat], zoom: Math.max(miniMapa.getZoom(), 16)});
}

// Nominatim (OpenStreetMap): endereço -> latitude/longitude. Grátis, até 1 consulta por segundo.
async function nominatim(params) {
  const q = new URLSearchParams({format: 'jsonv2', limit: '1', countrycodes: 'br', 'accept-language': 'pt-BR', ...params});
  const r = await fetch('https://nominatim.openstreetmap.org/search?' + q);
  if (!r.ok) throw new Error('falha no Nominatim');
  return (await r.json())[0];
}

async function localizarEndereco() {
  const faltando = ['e_rua', 'e_num', 'e_cidade', 'e_uf'].find(id => !$(id).value.trim());
  if (faltando) { $(faltando).reportValidity(); $(faltando).focus(); return false; }
  prepararMiniMapa();
  const [rua, num, cidade, uf, cep] = ['e_rua', 'e_num', 'e_cidade', 'e_uf', 'e_cep'].map(id => $(id).value.trim());
  try {
    // 1º: rua + número; 2º: só a rua (o número nem sempre está no OpenStreetMap)
    let achou = await nominatim({street: `${num} ${rua}`, city: cidade, state: uf, postalcode: cep});
    const exato = !!achou;
    if (!achou) achou = await nominatim({street: rua, city: cidade, state: uf});
    if (!achou) {
      aviso('Não encontramos esse endereço. Confira os dados ou clique no mapa para marcar sua casa.', 'erro');
      return false;
    }
    definirCasa({lat: +achou.lat, lng: +achou.lon});
    if (!exato) aviso('Achamos a rua, mas não o número. Arraste o pino azul até a sua casa.');
    return true;
  } catch {
    aviso('Não foi possível localizar o endereço agora. Clique no mapa para marcar sua casa.', 'erro');
    return false;
  }
}

/* =====================================================================
   Notícias: carrossel de cartazes
   ===================================================================== */
const INTERVALO_CARROSSEL = 6000;
let anuncios = [], cartazAtual = 0, timerCarrossel = null, carrosselPausado = false;
const cartazes = () => [...$('trilhaCartazes').children];
const resumo = t => { const s = String(t).replace(/\s+/g, ' ').trim(); return s.length > 140 ? s.slice(0, 137).trimEnd() + '…' : s; };
const dataBR = s => s ? new Date(s.replace(' ', 'T') + 'Z').toLocaleDateString('pt-BR') : '';

async function carregarAnuncios() {
  const novos = await api('/api/anuncios');
  if (JSON.stringify(novos) === JSON.stringify(anuncios) && cartazes().length) return;   // nada mudou: não reinicia o carrossel
  anuncios = novos;
  $('carrossel').hidden = !anuncios.length;
  $('noticiasVazio').hidden = !!anuncios.length;
  $('trilhaCartazes').innerHTML = anuncios.map((a, i) => `
    <button class="cartaz" data-acao="abrir-anuncio" data-id="${a.id}" aria-label="${esc(a.titulo)}: saiba mais">
      <img src="${esc(a.imagem)}" alt="" ${i > 1 ? 'loading="lazy"' : ''}>
      <span class="corpo"><b>${esc(a.titulo)}</b><span class="resumo">${esc(resumo(a.texto))}</span>
      <span class="saiba">Saiba mais →</span></span></button>`).join('');
  $('pontosCarrossel').innerHTML = anuncios.map((a, i) =>
    `<button data-acao="ir-cartaz" data-i="${i}" aria-label="Ir para o cartaz ${i + 1}: ${esc(a.titulo)}"></button>`).join('');
  // bloco do menu mostra o cartaz mais recente
  const img = $('bmNoticiasImg');
  img.hidden = !anuncios.length;
  if (anuncios.length) img.src = anuncios[0].imagem;
  $('bmNoticiasTxt').textContent = anuncios.length ? anuncios[0].titulo : 'Novidades da comunidade';
  cartazAtual = 0;
  $('trilhaCartazes').scrollLeft = 0;
  marcarPonto();
  tocarCarrossel();
}

function marcarPonto() {   // acende os pontos dos cartazes que estão inteiros na tela (2 no computador, 1 no celular)
  const t = $('trilhaCartazes'), lista = cartazes();
  if (!lista.length || !t.clientWidth) return;
  const esq = t.scrollLeft, dir = esq + t.clientWidth;
  [...$('pontosCarrossel').children].forEach((b, i) => {
    const x = lista[i].offsetLeft - lista[0].offsetLeft;
    b.classList.toggle('ativo', x >= esq - 4 && x + lista[i].offsetWidth <= dir + 4);
  });
}

function irCartaz(i) {
  const lista = cartazes();
  if (!lista.length) return;
  cartazAtual = (i + lista.length) % lista.length;
  $('trilhaCartazes').scrollTo({left: lista[cartazAtual].offsetLeft - lista[0].offsetLeft, behavior: semMovimento() ? 'auto' : 'smooth'});
  marcarPonto();
}

function passarCartaz(delta) {
  const t = $('trilhaCartazes');
  // no fim da trilha (vários cartazes visíveis de uma vez) volta para o primeiro
  const noFim = t.scrollLeft + t.clientWidth >= t.scrollWidth - 4;
  irCartaz(delta > 0 && noFim ? 0 : cartazAtual + delta);
  tocarCarrossel();
}

function tocarCarrossel() {   // troca sozinho a cada 6 s; para fora da tela, com mouse em cima, foco, aba oculta ou movimento reduzido
  clearInterval(timerCarrossel);
  if (semMovimento() || anuncios.length < 2) return;
  timerCarrossel = setInterval(() => {
    if (telaAtual === 'noticias' && !carrosselPausado && !document.hidden && !document.querySelector('dialog[open]')) passarCartaz(1);
  }, INTERVALO_CARROSSEL);
}

// arrastar com o dedo também atualiza o indicador
let timerRolagem = null;
$('trilhaCartazes').addEventListener('scroll', () => {
  clearTimeout(timerRolagem);
  timerRolagem = setTimeout(() => {
    const lista = cartazes();
    if (!lista.length) return;
    const dist = c => Math.abs(c.offsetLeft - lista[0].offsetLeft - $('trilhaCartazes').scrollLeft);
    cartazAtual = lista.reduce((melhor, c, i) => dist(c) < dist(lista[melhor]) ? i : melhor, 0);
    marcarPonto();
  }, 120);
}, {passive: true});
// pausa com o mouse em cima ou com foco de teclado (o foco que fica após um clique não trava o carrossel)
let sobreCarrossel = false, focoTeclado = false;
const atualizarPausa = () => { carrosselPausado = sobreCarrossel || focoTeclado; };
$('carrossel').addEventListener('pointerenter', e => { sobreCarrossel = e.pointerType === 'mouse'; atualizarPausa(); });
$('carrossel').addEventListener('pointerleave', () => { sobreCarrossel = false; atualizarPausa(); });
$('carrossel').addEventListener('focusin', e => { focoTeclado = e.target.matches(':focus-visible'); atualizarPausa(); });
$('carrossel').addEventListener('focusout', () => { focoTeclado = false; atualizarPausa(); });

async function abrirAnuncio(id, origem, viaTeclado) {
  const a = anuncios.find(x => x.id === id) || await api(`/api/anuncios/${id}`);
  $('anImagem').src = a.imagem;
  $('anImagem').alt = 'Cartaz: ' + a.titulo;
  $('anTitulo').textContent = a.titulo;
  $('anData').textContent = a.criado_em ? 'Publicado em ' + dataBR(a.criado_em) : '';
  $('anTexto').textContent = a.texto;
  abrirDeOrigem($('dlgAnuncio'), origem, viaTeclado);
  $('dlgAnuncio').scrollTop = 0;
}

/* =====================================================================
   Admin (o painel só existe na página depois de validar o token no servidor)
   ===================================================================== */
function abrirAdmin(origem, viaTeclado) {
  adminOrigem = origem;
  $('token').value = '';
  $('dlgAdmin').querySelector('.msg').textContent = '';
  abrirDeOrigem($('dlgAdmin'), origem, viaTeclado);
  $('token').focus();
}

$('formAdmin').addEventListener('submit', tentar(async e => {
  e.preventDefault();
  await entrarAdmin($('token').value);
  $('dlgAdmin').close();   // fecha antes da transição, para o diálogo não entrar na "foto" da tela
  aviso('Modo administrador ativado.');
  navegar('admin', {origem: adminOrigem});
}));

async function entrarAdmin(token, silencioso) {
  const r = await fetch('/api/admin/painel', {headers: {'X-Admin-Token': token}});
  if (!r.ok) {
    try { sessionStorage.removeItem('adminToken'); } catch {}
    if (!silencioso) throw new Error('Token de administrador inválido.');
    return false;
  }
  adminToken = token;
  try { sessionStorage.setItem('adminToken', token); } catch {}
  mapaAdmin?.remove();
  mapaAdmin = null;
  $('painelAdmin').innerHTML = await r.text();
  marcarAdmin(true);
  if (telaAtual === 'admin') prepararMapaAdmin();
  await carregarAnalise();
  await carregarAnunciosAdmin();
  return true;
}

function marcarAdmin(ativo) {
  $('dockAdmin').classList.toggle('admin-ativo', ativo);
  $('bmAdmin').classList.toggle('ativo', ativo);
  $('bmAdminTxt').textContent = ativo ? 'Painel ativo' : 'Requer token';
}

function sairAdmin(expirou) {
  adminToken = null;
  try { sessionStorage.removeItem('adminToken'); } catch {}
  mapaAdmin?.remove();
  mapaAdmin = novoPino = novoPonto = null;
  pinosAdmin = [];
  $('painelAdmin').innerHTML = '';
  marcarAdmin(false);
  if (telaAtual === 'admin') navegar('inicio');
  aviso(expirou ? 'Sessão de administrador inválida.' : 'Modo administrador encerrado.', expirou ? 'erro' : 'ok');
}

function prepararMapaAdmin() {   // mapa próprio do painel: clique para marcar a nova máquina
  if (!window.maplibregl || !$('mapaAdmin')) return;
  if (mapaAdmin) return mapaAdmin.resize();
  mapaAdmin = new maplibregl.Map({container: 'mapaAdmin', style: ESTILO_MAPA, center: CENTRO_SP, zoom: 10.5,
                                  attributionControl: {compact: true}});
  mapaAdmin.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right');
  mapaAdmin.on('click', e => {
    novoPonto = {lat: e.lngLat.lat, lng: e.lngLat.lng};
    novoPino?.remove();
    novoPino = marcador(novoPonto, '#ff8a1f', 'Nova máquina', mapaAdmin);
    $('m_local').textContent = `${novoPonto.lat.toFixed(5)}, ${novoPonto.lng.toFixed(5)}`;
  });
  carregarPinosAdmin().catch(() => {});
}

async function carregarPinosAdmin() {
  if (!mapaAdmin) return;
  pinosAdmin.forEach(p => p.remove());
  pinosAdmin = (await api('/api/maquinas')).map(m => marcador({lat: m.lat, lng: m.lng}, '#2fb24c', m.nome, mapaAdmin));
}

async function carregarAnalise() {
  if (!adminToken || !$('analise')) return;
  const a = await api('/api/analise', null, true);
  $('analise').innerHTML = '<tr><th>Bairro</th><th>Máquinas</th><th>Depósitos</th><th>Itens</th><th>Pontos</th><th>Usuários</th></tr>' +
    a.por_bairro.map(b => `<tr><td>${esc(b.bairro)}</td><td>${b.maquinas}</td><td>${b.depositos}</td><td>${b.itens}</td><td>${b.pontos}</td><td>${b.usuarios}</td></tr>`).join('');
  const max = Math.max(1, ...a.por_material.map(m => m.itens));
  $('por_material').innerHTML = a.por_material.map(m =>
    `<div class="barra-mat"><div><span>${esc(m.material).toUpperCase()}</span><span>${m.itens}</span></div><i style="transform:scaleX(${m.itens / max})"></i></div>`).join('');
}

const novaMaquina = tentar(async () => {
  if (!novoPonto) throw new Error('Clique no mapa do painel para escolher o local da máquina.');
  await api('/api/maquinas', {nome: $('m_nome').value, bairro: $('m_bairro').value, endereco: $('m_end').value, ...novoPonto}, true);
  novoPino?.remove();
  novoPino = novoPonto = null;
  $('m_local').textContent = 'nenhum';
  await carregarPinosAdmin();
  await carregarMaquinas();
  await atualizarProxima(false);
  await carregarAnalise();
  aviso('Máquina adicionada!');
});

const novoCupom = tentar(async () => {
  await api('/api/cupons', {marca: $('c_marca').value, descricao: $('c_desc').value, custo: $('c_custo').value}, true);
  await (user ? carregarUsuario() : carregarVisitante());
  aviso('Cupom adicionado como nova fase!');
});

const depositar = tentar(async () => {
  if (!user || !nearest) throw new Error('Entre numa conta de usuário com endereço cadastrado antes.');
  const r = await api('/api/depositos', {usuario_id: user.id, maquina_id: nearest.id, material: $('d_mat').value, quantidade: $('d_qtd').value}, true);
  aviso(`+${r.pontos} pontos!`);
  const antes = progresso.fase_atual;
  await atualizarProxima(false);
  await carregarAnalise();
  await carregarUsuario();
  if (progresso.fase_atual > antes) navegar('fases');   // liberou fase nova: o avatar anda até ela
});

const baixarPlanilha = tentar(async () => {
  const r = await fetch('/api/admin/planilha', {headers: {'X-Admin-Token': adminToken || ''}});
  if (r.status === 401) { sairAdmin(true); return; }
  if (!r.ok) throw new Error('Não foi possível gerar a planilha.');
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement('a'), {href: url, download: 'usuarios_mccrea.xlsx'});
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

/* ---------- admin: anúncios (cartaz + título + texto) ---------- */
const MAX_CARTAZ_MB = 5;
let anunciosAdmin = [], anuncioEditando = null;

function formAnuncio(a) {
  const f = new FormData();
  f.append('titulo', a.titulo);
  f.append('texto', a.texto);
  f.append('ordem', a.ordem);
  f.append('ativo', a.ativo ? '1' : '0');
  return f;
}

async function carregarAnunciosAdmin() {
  if (!adminToken || !$('listaAnuncios')) return;
  anunciosAdmin = await api('/api/admin/anuncios', null, true);
  $('listaAnuncios').innerHTML = anunciosAdmin.length ? anunciosAdmin.map(a => `
    <div class="tile ${a.ativo ? '' : 'oculto'}">
      <img class="miniatura" src="${esc(a.imagem)}" alt="" loading="lazy">
      <div class="info"><b>${esc(a.titulo)}</b>
        <small>${a.ativo ? 'Publicado' : 'Oculto'} · ordem ${a.ordem} · ${dataBR(a.criado_em)}</small></div>
      <div class="botoes">
        <button class="btn branco pequeno" data-acao="editar-anuncio" data-id="${a.id}">Editar</button>
        <button class="btn branco pequeno" data-acao="alternar-anuncio" data-id="${a.id}">${a.ativo ? 'Ocultar' : 'Publicar'}</button>
        <button class="btn branco pequeno perigo" data-acao="excluir-anuncio" data-id="${a.id}">Excluir</button>
      </div>
    </div>`).join('') : '<p class="dica">Nenhum anúncio cadastrado.</p>';
}

function previaCartaz() {
  const arq = $('an_imagem').files[0];
  if (!arq) return;
  if (arq.size > MAX_CARTAZ_MB * 1024 * 1024) {
    $('an_imagem').value = '';
    return aviso(`Imagem muito grande (máximo ${MAX_CARTAZ_MB} MB).`, 'erro');
  }
  if ($('an_previa').src.startsWith('blob:')) URL.revokeObjectURL($('an_previa').src);
  $('an_previa').src = URL.createObjectURL(arq);
  $('an_previa').hidden = false;
}

function limparFormAnuncio() {
  anuncioEditando = null;
  $('formAnuncio').reset();
  $('an_previa').hidden = true;
  $('an_form_titulo').textContent = 'Novo anúncio (Notícias)';
  $('an_imagem_dica').textContent = '';
  $('an_salvar').textContent = 'Publicar anúncio';
  $('an_cancelar').hidden = true;
}

function editarAnuncio(id) {
  const a = anunciosAdmin.find(x => x.id === id);
  if (!a) return;
  anuncioEditando = id;
  $('an_imagem').value = '';
  $('an_previa').src = a.imagem;
  $('an_previa').hidden = false;
  $('an_titulo').value = a.titulo;
  $('an_texto').value = a.texto;
  $('an_ordem').value = a.ordem;
  $('an_ativo').checked = !!a.ativo;
  $('an_form_titulo').textContent = 'Editar anúncio';
  $('an_imagem_dica').textContent = '(deixe vazio para manter o cartaz atual)';
  $('an_salvar').textContent = 'Salvar alterações';
  $('an_cancelar').hidden = false;
  $('formAnuncio').scrollIntoView({behavior: semMovimento() ? 'auto' : 'smooth', block: 'center'});
}

const salvarAnuncio = tentar(async e => {
  e.preventDefault();
  const titulo = $('an_titulo').value.trim(), texto = $('an_texto').value.trim(), arq = $('an_imagem').files[0];
  if (!anuncioEditando && !arq) throw new Error('Escolha a imagem do cartaz.');
  if (titulo.length < 3) throw new Error('O título precisa ter pelo menos 3 caracteres.');
  if (!texto) throw new Error('Escreva o texto do anúncio.');
  const f = formAnuncio({titulo, texto, ordem: $('an_ordem').value || 0, ativo: $('an_ativo').checked});
  if (arq) f.append('imagem', arq);
  $('an_salvar').disabled = true;
  try {
    await apiForm(anuncioEditando ? `/api/anuncios/${anuncioEditando}` : '/api/anuncios', anuncioEditando ? 'PUT' : 'POST', f);
  } finally {
    $('an_salvar').disabled = false;
  }
  aviso(anuncioEditando ? 'Anúncio atualizado!' : 'Anúncio publicado no carrossel!');
  limparFormAnuncio();
  await carregarAnunciosAdmin();
  await carregarAnuncios();
});

const alternarAnuncio = tentar(async id => {
  const a = anunciosAdmin.find(x => x.id === id);
  await apiForm(`/api/anuncios/${id}`, 'PUT', formAnuncio({...a, ativo: !a.ativo}));
  aviso(a.ativo ? 'Anúncio ocultado do carrossel.' : 'Anúncio publicado no carrossel!');
  await carregarAnunciosAdmin();
  await carregarAnuncios();
});

const excluirAnuncio = tentar(async id => {
  const a = anunciosAdmin.find(x => x.id === id);
  if (!confirm(`Excluir o anúncio "${a.titulo}"? Isso não pode ser desfeito.`)) return;
  await apiForm(`/api/anuncios/${id}`, 'DELETE');
  if (anuncioEditando === id) limparFormAnuncio();
  aviso('Anúncio excluído.');
  await carregarAnunciosAdmin();
  await carregarAnuncios();
});

// o formulário de anúncios chega junto com o painel: eventos delegados
document.addEventListener('submit', e => { if (e.target.id === 'formAnuncio') salvarAnuncio(e); });
document.addEventListener('change', e => { if (e.target.id === 'an_imagem') previaCartaz(); });

/* =====================================================================
   Início
   ===================================================================== */
(async function iniciar() {   // roda mesmo se o mapa não carregar
  $('miniBoasVindas').innerHTML = SPRITE(44);
  $('bmAvatar').innerHTML = SPRITE(40);
  $('bmPerfilAvatar').innerHTML = SPRITE(30);
  const pedida = nomeDoHash();
  mostrarTela(pedida);
  // entrada escalonada dos blocos só na primeira carga (evento raro; voltar ao menu não repete)
  if (telaAtual === 'inicio') document.querySelectorAll('.bloco-menu').forEach((b, i) => entrarSuave(b, {atraso: i * 50, duracao: 420}));
  carregarAnuncios().catch(() => { $('carrossel').hidden = true; $('noticiasVazio').hidden = false; });
  setInterval(() => carregarAnuncios().catch(() => {}), 5 * 60 * 1000);   // novidades sem recarregar a página
  addEventListener('resize', marcarPonto);
  let t = null;
  try { t = sessionStorage.getItem('adminToken'); } catch {}
  if (t) entrarAdmin(t, true).then(ok => { if (ok && pedida === 'admin') navegar('admin', {viaTeclado: true}); }).catch(() => {});
  try { await carregarUsuario(); }
  catch { await carregarVisitante().catch(() => {}); }
})();
