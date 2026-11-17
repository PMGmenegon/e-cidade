#!/usr/bin/env node
// T-030: bateria com navegador (Playwright + Chrome headless) das telas legadas que chamam a API /v4/ por JavaScript.
//   node bateria.mjs capturar --base http://localhost:8140 --container ecidade_<agente>_56 --saida saida/56.json [--casos casos.tsv]
//   node bateria.mjs comparar saida/a.json saida/b.json          (sai 1 se diferem, 0 se iguais)
// Abre cada tela com sessao valida e registra as chamadas /v4/ que ela faz SOZINHA (metodo, rota, status, corpo normalizado).
// Nao clica em nada (botao que grava e ponto cego). O unico que grava e o proprio login e o log de acesso do sistema:
// rode dentro de vigia-banco.sh (ver rodar.sh). Usuario de teste dbseller/dbseller (SISTEMA_USUARIO/SISTEMA_SENHA mudam).
import { createRequire } from 'node:module';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const opt = (n, d) => { const i = process.argv.indexOf('--' + n); return i > 0 ? process.argv[i + 1] : d; };

// ---------- normalizacao (so dados que mudam a cada rodada) ----------
const MASCARAS = [
  [/[0-9a-f]{32}/g, 'MD5X'],
  [/localhost:[0-9]{2,5}/g, 'localhost:PORT'],
  [/sid=[0-9a-z]{8,}/g, 'sid=X'],
  [/wname[0-9]+/g, 'wnameX'],
  [/[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:?[0-9]{2})?/g, 'DATAHORA'],
  [/\b1[0-9]{9}\b/g, 'EPOCH'],
];
const mascara = (s) => MASCARAS.reduce((t, [rx, r]) => t.replace(rx, r), s);
const ordena = (v) => Array.isArray(v) ? v.map(ordena)
  : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, ordena(v[k])]))
  : typeof v === 'string' ? mascara(v) : v;
export function normalizaCorpo(texto) {
  try { return { tipo: 'json', corpo: ordena(JSON.parse(texto)) }; } catch (e) { /* nao e JSON */ }
  const t = mascara(texto).replace(/\s+/g, ' ').trim();
  return { tipo: 'texto', corpo: t.length > 1500 ? t.slice(0, 1500) + '…[' + t.length + ' chars]' : t };
}
export const normalizaUrl = (u, base) => mascara(u.replace(base, ''));

// ---------- comparar ----------
function comparar(a, b) {
  const A = JSON.parse(fs.readFileSync(a, 'utf8')), B = JSON.parse(fs.readFileSync(b, 'utf8'));
  const dif = [];
  const por = (L) => Object.fromEntries(L.casos.map((c) => [c.arquivo, c]));
  const pa = por(A), pb = por(B);
  for (const k of new Set([...Object.keys(pa), ...Object.keys(pb)])) {
    const x = JSON.stringify(pa[k] ?? null, null, 1), y = JSON.stringify(pb[k] ?? null, null, 1);
    if (x !== y) dif.push(k);
  }
  console.log(dif.length ? 'DIFERE em ' + dif.length + ' de ' + A.casos.length + ': ' + dif.join(', ') : 'IGUAIS: ' + A.casos.length + ' casos');
  return dif.length ? 1 : 0;
}
if (process.argv[2] === 'comparar') process.exit(comparar(process.argv[3], process.argv[4]));
if (process.argv[2] !== 'capturar') { console.error('uso: capturar|comparar (ver cabecalho)'); process.exit(2); }

// ---------- captura ----------
const base = opt('base'), container = opt('container'), saida = opt('saida');
if (!base || !container || !saida) { console.error('faltam --base, --container, --saida'); process.exit(2); }
const casosArq = opt('casos', path.join(AQUI, 'casos.tsv'));
const casos = fs.readFileSync(casosArq, 'utf8').split('\n').filter((l) => l && !l.startsWith('#')).map((l) => {
  const [arquivo, caminho, classe, obs] = l.split('\t'); return { arquivo, caminho, classe, obs: obs || '' };
});
const usuario = process.env.SISTEMA_USUARIO || 'dbseller', senha = process.env.SISTEMA_SENHA || 'dbseller';
const chrome = process.env.CHROME || '/usr/bin/google-chrome';
const pwDir = process.env.PLAYWRIGHT_DIR || fs.readdirSync(path.join(process.env.HOME, '.npm/_npx')).map((d) => path.join(process.env.HOME, '.npm/_npx', d, 'node_modules')).find((d) => fs.existsSync(path.join(d, 'playwright')));
const { chromium } = createRequire(pwDir + '/')('playwright');

const dockerExec = (args, input) => spawnSync('docker', ['exec', ...(input !== undefined ? ['-i'] : []), '-u', 'www-data', container, ...args], { input, encoding: 'latin1', maxBuffer: 1 << 26 });

const browser = await chromium.launch({ executablePath: chrome, headless: true });
const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
// Login: a tela "Entrar" faz POST v4/oauth/token e guarda o token no localStorage, de onde o HttpClient das telas o le; em seguida
// abre o desktop numa janela nova (window.open -> abrir.php). Aqui o window.open e anulado (nao queremos a janela) e o abrir.php e
// pedido direto, com a mesma senha md5. Se o token nao sai (o /v4 do 8.5 de hoje da 500) as telas seguem sem token e o modo fica
// registrado em "login".
const dlgLogin = [];
const pgLogin = await ctx.newPage();
await pgLogin.addInitScript(() => { window.open = () => null; });
pgLogin.on('dialog', async (d) => { dlgLogin.push(mascara(d.message().slice(0, 120))); await d.dismiss().catch(() => {}); });
await pgLogin.goto(base + '/login.php', { waitUntil: 'networkidle' });
await pgLogin.fill('#usu_login', usuario); await pgLogin.fill('#usu_senha', senha);
await pgLogin.click('#btnlogar');
let loginModo;
try {
  await pgLogin.waitForFunction(() => !!window.localStorage.getItem('access_token'), null, { timeout: 20000 });
  loginModo = 'token Passport (tela de login) + abrir.php';
} catch (e) {
  loginModo = 'SEM token (a tela de login nao obteve: ' + (dlgLogin[0] || 'sem aviso') + ') + abrir.php';
}
const rl = await ctx.request.post(base + '/abrir.php', { form: { DB_login: usuario, DB_senha: crypto.createHash('md5').update(senha).digest('hex'), conteudoCaptcha: '' } });
if (rl.status() !== 200) { console.error('login falhou (abrir.php ' + rl.status() + ')'); process.exit(1); }
const desktop = await ctx.newPage();
const sid = (await ctx.cookies()).find((c) => c.name === 'ECIDADEWINDOWMAIN')?.value;
if (!sid) { console.error('login falhou: sem cookie de sessao'); process.exit(1); }
// a sessao do login nao traz instituicao/modulo/exercicio (o navegador os escolhe): acrescentados no arquivo de sessao, sem tocar no banco
// (mesmo metodo de relatorios-kernel/sessao.sh). Restaurada antes de CADA tela para uma nao contaminar a outra.
const arqSessao = '/var/lib/php/sessions/sess_' + sid;
const t = Math.floor(Date.now() / 1000), ano = new Date().getFullYear();
const extra = `DB_instit|s:1:"1";DB_modulo|s:4:"9318";DB_nome_modulo|s:6:"Social";DB_anousu|i:${ano};DB_datausu|i:${t};DB_uol_hora|i:${t};DB_coddepto|s:1:"1";DB_nomedepto|s:8:"CADASTRO";DB_itemmenu_acessado|s:1:"0";DB_use_pcasp|b:0;DB_Area|s:1:"9";`;
const lido = dockerExec(['cat', arqSessao]);
if (lido.status !== 0) { console.error('sessao nao encontrada em ' + container); process.exit(1); }
const snapshot = lido.stdout.replace('DB_acessado|N;', 'DB_acessado|s:1:"0";') + extra;
const restaura = () => dockerExec(['sh', '-c', 'cat > ' + arqSessao], snapshot);

// As telas legadas rodam DENTRO do frame "corpo" do desktop (inicio.php): scripts.js usa CurrentWindow.corpo e, sem ele, volta ao login.
// Por isso abrimos o desktop uma vez e navegamos o frame "corpo" para cada tela, como o menu faz.
let corrente = null; // coletor da tela em andamento
desktop.on('response', (res) => {
  const u = res.url(); if (!corrente || !/\/v4\//.test(u)) return;
  const col = corrente;
  col.pend.push((async () => {
    let corpo;
    try { corpo = normalizaCorpo(await res.text()); } catch (e) { corpo = { tipo: 'erro', corpo: 'corpo indisponivel' }; }
    col.v4.push({ metodo: res.request().method(), rota: normalizaUrl(u, base), status: res.status(), ...corpo });
  })());
});
desktop.on('requestfailed', (rq) => { if (corrente && /\/v4\//.test(rq.url())) corrente.v4.push({ metodo: rq.method(), rota: normalizaUrl(rq.url(), base), status: 0, tipo: 'falha', corpo: String(rq.failure()?.errorText || '') }); });
desktop.on('dialog', async (d) => { if (corrente) corrente.alertas.push(mascara(d.message().slice(0, 200))); await d.dismiss().catch(() => {}); });
// O texto do erro de JSON vazio oscila entre rodadas conforme a corrida entre os pedidos em paralelo: o Chrome ora diz
// "Failed to execute 'json' on 'Response': Unexpected end of JSON input", ora so "Unexpected end of JSON input". Mesmo erro: o prefixo sai.
const normalizaErroJs = (m) => mascara(String(m).replace(/^Failed to execute 'json' on 'Response': /, '').slice(0, 200));
desktop.on('pageerror', (e) => { if (corrente) corrente.erros.push(normalizaErroJs(e.message)); });
await desktop.goto(base + '/inicio.php?uso=' + encodeURIComponent(usuario) + '&janelaWidth=1280', { waitUntil: 'networkidle', timeout: 60000 });
await desktop.waitForLoadState('networkidle').catch(() => {});
await desktop.waitForTimeout(2000);
if (!desktop.frame({ name: 'corpo' })) { console.error('desktop sem frame corpo (login/sessao invalidos?)'); process.exit(1); }

const resultado = { gerado_por: 'T-030 bateria.mjs', runtime: opt('runtime', ''), login: loginModo, casos: [] };
for (const c of casos) {
  const r = { arquivo: c.arquivo, classe: c.classe, abre: c.caminho || null };
  if (c.classe !== 'tela' && c.classe !== 'host') { r.motivo = c.obs; resultado.casos.push(r); continue; }
  restaura();
  corrente = { v4: [], alertas: [], erros: [], pend: [] };
  try {
    const doc = await desktop.frame({ name: 'corpo' }).goto(base + c.caminho, { waitUntil: 'networkidle', timeout: 45000 });
    await desktop.waitForTimeout(1500);
    r.documento = doc ? doc.status() : null;
    r.titulo = mascara(await desktop.frame({ name: 'corpo' }).title().catch(() => ''));
  } catch (e) { r.documento = 'ERRO: ' + mascara(String(e.message).split('\n')[0]); }
  await Promise.allSettled(corrente.pend);
  r.chamadas_v4 = corrente.v4.sort((x, y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));
  r.alertas = corrente.alertas; r.erros_js = corrente.erros.sort();
  console.log(c.arquivo.padEnd(48), 'doc', r.documento, ' /v4:', r.chamadas_v4.length, ' alertas:', r.alertas.length, ' erros_js:', r.erros_js.length);
  corrente = null;
  resultado.casos.push(r);
}
await browser.close();
fs.mkdirSync(path.dirname(path.resolve(saida)), { recursive: true });
fs.writeFileSync(saida, JSON.stringify(resultado, null, 1) + '\n');
console.log('gravado', saida);
