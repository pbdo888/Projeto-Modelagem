/* =====================================================================
   Movimento: curvas, avisos, diálogos que nascem do botão de origem.
   Regra geral: ação vinda do teclado não anima; prefers-reduced-motion
   leva tudo direto ao estado final.
   ===================================================================== */
const semMovimento = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

// As mesmas curvas do CSS, para a Web Animations API (com plano B onde linear() não existe)
const EASE = (() => {
  const css = getComputedStyle(document.documentElement);
  const temLinear = CSS.supports('transition-timing-function', 'linear(0, 1)');
  return {
    entra: 'cubic-bezier(.22, 1, .36, 1)',
    sai: 'cubic-bezier(.55, 0, 1, .45)',
    estado: 'cubic-bezier(.65, 0, .35, 1)',
    mola: temLinear ? css.getPropertyValue('--mola').trim() : 'cubic-bezier(.34, 1.4, .64, 1)',
    molaViva: temLinear ? css.getPropertyValue('--mola-viva').trim() : 'cubic-bezier(.34, 1.8, .64, 1)',
  };
})();

// clique feito pelo teclado (Enter/Espaço) chega com detail === 0
const veioDoTeclado = e => !!e && e.detail === 0;

/* ---------- entrada padrão: opacidade + deslocamento + desfoque ---------- */
function entrarSuave(el, {x = 0, y = 10, atraso = 0, duracao = 380} = {}) {
  if (semMovimento() || !el) return;
  el.animate([{opacity: 0, transform: `translate(${x}px, ${y}px)`, filter: 'blur(4px)'},
              {opacity: 1, transform: 'none', filter: 'blur(0)'}],
             {duration: duracao, delay: atraso, easing: EASE.entra, fill: 'backwards'});
}

/* ---------- número que conta até o novo valor (Value Change) ---------- */
function contar(el, valor) {
  if (!el) return;
  cancelAnimationFrame(el._conta);
  const de = parseInt(el.textContent, 10);
  if (!Number.isFinite(de) || de === valor || semMovimento()) { el.textContent = valor; return; }
  let t0 = null;
  const quadro = agora => {
    t0 ??= agora;
    const t = Math.min(1, Math.max(0, (agora - t0) / 600)), e = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(de + (valor - de) * e);
    if (t < 1) el._conta = requestAnimationFrame(quadro);
  };
  el._conta = requestAnimationFrame(quadro);
}

/* ---------- avisos: entram com materialização, saem mais discretos ---------- */
function aviso(msg, tipo = 'ok') {
  const caixa = document.querySelector('dialog[open] .msg');   // com diálogo aberto, a mensagem aparece nele
  if (caixa) {
    caixa.textContent = msg;
    caixa.className = 'msg ' + tipo;
    entrarSuave(caixa, {y: -4, duracao: 260});
    return;
  }
  const d = document.createElement('div');
  d.className = 'aviso ' + tipo;
  d.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
  d.textContent = msg;
  document.getElementById('avisos').append(d);
  if (!semMovimento()) {
    d.animate([{opacity: 0, transform: 'translateY(-10px) scale(.98)', filter: 'blur(4px)'}, {opacity: 1, transform: 'none', filter: 'blur(0)'}],
              {duration: 320, easing: EASE.entra});
  }
  setTimeout(() => {
    if (semMovimento()) return d.remove();
    d.animate([{opacity: 1, transform: 'none'}, {opacity: 0, transform: 'translateX(12px)'}],
              {duration: 180, easing: EASE.sai, fill: 'forwards'}).finished.then(() => d.remove(), () => d.remove());
  }, 3400);
}

/* ---------- diálogos de vidro ---------- */
// Abre expandindo a partir do elemento que o chamou (causa e efeito).
function abrirDeOrigem(dlg, origem, instantaneo) {
  document.querySelectorAll('dialog[open]').forEach(d => d !== dlg && d.close());
  if (dlg.open) return;
  dlg.showModal();
  if (instantaneo || semMovimento() || !origem?.isConnected) return;
  const o = origem.getBoundingClientRect(), d = dlg.getBoundingClientRect();
  if (!o.width) return;
  const dx = o.left + o.width / 2 - (d.left + d.width / 2), dy = o.top + o.height / 2 - (d.top + d.height / 2);
  dlg.animate([{transform: `translate(${dx}px, ${dy}px) scale(.5)`}, {transform: 'none'}], {duration: 520, easing: EASE.mola});
  dlg.animate([{opacity: 0, filter: 'blur(6px)'}, {opacity: 1, filter: 'blur(0)'}], {duration: 220, easing: EASE.entra});
}

// Fecha mais discreto do que abriu; pelo teclado (ou Esc, que é nativo) fecha na hora.
function fecharAnimado(dlg, instantaneo) {
  if (!dlg?.open) return;
  if (instantaneo || semMovimento()) return dlg.close();
  const a = dlg.animate([{opacity: 1, transform: 'none'}, {opacity: 0, transform: 'translateY(6px) scale(.97)'}],
                        {duration: 150, easing: EASE.sai, fill: 'forwards'});
  a.onfinish = () => { dlg.close(); a.cancel(); };
}
