// Uso: ANTHROPIC_API_KEY=sua_chave node server.js  (Node 18+)
const http = require('http'), fs = require('fs'), path = require('path');
const { exec } = require('child_process');

const KEY = process.env.ANTHROPIC_API_KEY;
const MODEL = 'claude-sonnet-5-5';
const LAT = -26.30, LON = -48.85, CIDADE = 'Joinville'; // troque se quiser
const P = process.platform; // win32 | darwin | linux

// Apps permitidos (whitelist). Adicione os seus aqui.
const APPS = {
  vscode:      { win32: 'code', darwin: 'open -a "Visual Studio Code"', linux: 'code' },
  chrome:      { win32: 'start chrome', darwin: 'open -a "Google Chrome"', linux: 'google-chrome' },
  calculadora: { win32: 'calc', darwin: 'open -a Calculator', linux: 'gnome-calculator' },
  bloco_notas: { win32: 'notepad', darwin: 'open -a TextEdit', linux: 'gedit' },
  spotify:     { win32: 'start spotify:', darwin: 'open -a Spotify', linux: 'spotify' },
  terminal:    { win32: 'start cmd', darwin: 'open -a Terminal', linux: 'x-terminal-emulator' },
  explorador:  { win32: 'explorer', darwin: 'open .', linux: 'xdg-open .' },
};

const historico = [];

async function clima() {
  try {
    const u = `https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}` +
      `&current=temperature_2m,apparent_temperature,precipitation,weather_code` +
      `&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=1`;
    const d = await (await fetch(u)).json();
    return `${CIDADE}: agora ${d.current.temperature_2m}°C (sensação ${d.current.apparent_temperature}°C), ` +
      `mín ${d.daily.temperature_2m_min[0]}°C, máx ${d.daily.temperature_2m_max[0]}°C, ` +
      `chance de chuva ${d.daily.precipitation_probability_max[0]}%, código do tempo ${d.current.weather_code}`;
  } catch { return 'clima indisponível'; }
}

function executar(acao) {
  if (!acao) return;
  let cmd;
  if (acao.tipo === 'app' && APPS[acao.alvo]) cmd = APPS[acao.alvo][P];
  else if (acao.tipo === 'site' && /^https?:\/\/[^\s"'&|<>^]+$/.test(acao.alvo)) {
    cmd = P === 'win32' ? `start "" "${acao.alvo}"` : P === 'darwin' ? `open "${acao.alvo}"` : `xdg-open "${acao.alvo}"`;
  }
  if (cmd) exec(cmd, e => e && console.log('erro ao executar:', e.message));
}

async function perguntar(texto) {
  const agora = new Date().toLocaleString('pt-BR', { dateStyle: 'full', timeStyle: 'short' });
  const system = `Você é o JARVIS, assistente pessoal do Eduardo. Responda em português, de forma curta (1-2 frases), educada e com leve sofisticação.
Chame-o de Eduardo. Se ele cumprimentar ("oi", "olá", "e aí"), responda com o nome e a saudação certa pela hora (bom dia até 11h59, boa tarde até 17h59, boa noite depois), ex.: "Olá, Eduardo, bom dia.".
Data/hora: ${agora}. Clima: ${await clima()}.
Apps que você pode abrir (use o id): ${Object.keys(APPS).join(', ')}.
Responda SOMENTE com JSON válido, sem markdown: {"fala":"...","acao":{"tipo":"app|site|nenhuma","alvo":"id do app ou URL https"}}
Se não houver ação, use {"tipo":"nenhuma","alvo":""}.`;
  historico.push({ role: 'user', content: texto });
  if (historico.length > 8) historico.splice(0, historico.length - 8);

  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-api-key': KEY, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({ model: MODEL, max_tokens: 400, system, messages: historico }),
  });
  const j = await r.json();
  if (!j.content) throw new Error(JSON.stringify(j));
  const raw = j.content.map(c => c.text || '').join('').replace(/```json|```/g, '').trim();
  historico.push({ role: 'assistant', content: raw });
  let out;
  try { out = JSON.parse(raw); } catch { out = { fala: raw, acao: null }; }
  executar(out.acao);
  return out;
}

http.createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/ask') {
    let b = ''; req.on('data', c => b += c);
    req.on('end', async () => {
      try {
        const out = await perguntar(JSON.parse(b).text);
        res.setHeader('content-type', 'application/json');
        res.end(JSON.stringify(out));
      } catch (e) { res.statusCode = 500; res.end(JSON.stringify({ fala: 'Falha: ' + e.message })); }
    });
  } else {
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.end(fs.readFileSync(path.join(__dirname, 'jarvis.html')));
  }
}).listen(3000, '127.0.0.1', () => console.log('JARVIS em http://localhost:3000'));
