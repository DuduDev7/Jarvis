# 🤖 JARVIS

Assistente de voz em português, estilo Siri / J.A.R.V.I.S. Você fala, ele entende, age no computador e responde com voz neural.

- **Ouvido:** microfone + detecção de fala + Google Speech (pt-BR, sem chave)
- **Cérebro:** Claude (API da Anthropic) com ferramentas e busca na web
- **Voz:** Edge-TTS `pt-BR-AntonioNeural` (grátis, soa natural)
- **Anti-eco:** o microfone fica fechado enquanto ele fala, então ele nunca transcreve a própria voz

## Instalação (Windows)

1. Instale o **Python 3.11 ou 3.12** (python.org, marque *Add to PATH*).
2. Dê dois cliques em `instalar.bat` e cole sua chave em `ANTHROPIC_API_KEY` no `.env` (crie em console.anthropic.com).
3. Dê dois cliques em `iniciar.bat`.

Mac/Linux:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edite e coloque a chave
python -m jarvis
```
(Mac: `brew install portaudio` · Linux: `sudo apt install libportaudio2 ffmpeg`)

## Como usar

Diga **"Jarvis"** + o pedido. Depois da resposta ele continua ouvindo por ~8 s sem precisar do nome.

| Exemplo | O que acontece |
|---|---|
| "Oi Jarvis" | Cumprimenta pelo nome e horário |
| "Jarvis, como está o dia hoje?" | Data, hora e clima |
| "Jarvis, abra o VS Code" | Abre o aplicativo |
| "Jarvis, pesquise no YouTube lo-fi" | Abre a pesquisa |
| "Jarvis, aumente o volume" / "volume em 30" | Controla o volume |
| "Jarvis, pause a música" / "próxima" | Controle de mídia |
| "Jarvis, acha meu último PDF nos downloads" | Busca e abre arquivos |
| "Jarvis, me lembra em 10 minutos de tirar o bolo" | Timer falado |
| "Jarvis, anota: comprar café" | Salva em `~/Jarvis/notas.txt` |
| "Jarvis, quem ganhou o jogo ontem?" | Busca na web |
| "Jarvis, apague o arquivo X" | Pede confirmação (sim/não) |
| "Tchau Jarvis" | Volta a esperar pelo nome |
| "Desligar Jarvis" | Fecha o programa |

Sem palavra de ativação (aperte Enter para falar): `python -m jarvis --tecla`

## Configuração (`.env`)

| Variável | Para quê |
|---|---|
| `JARVIS_VOZ` | Voz. Veja todas: `python -m jarvis --vozes` |
| `JARVIS_VELOCIDADE` / `JARVIS_TOM` | Ex.: `+10%` / `-6Hz` (mais grave = mais "Jarvis") |
| `JARVIS_MODELO` | `claude-sonnet-5-5` (mais esperto) ou `claude-haiku-5-5` (mais rápido) |
| `JARVIS_MIC` | Número do microfone: `python -m jarvis --dispositivos` |
| `JARVIS_SENSIBILIDADE` | Menor = capta voz mais baixa (2.0–5.0) |
| `JARVIS_SILENCIO_MS` | Pausa que significa "terminei de falar" |
| `JARVIS_BUSCA_WEB` | `false` para desativar a busca na web |

Apps extras: edite o dicionário `APPS` em `jarvis/config.py`.

## Problemas comuns

- **Ele não me ouve / ouve barulho:** ajuste `JARVIS_SENSIBILIDADE` e `JARVIS_MIC`. Fique em silêncio durante a calibração inicial.
- **Ele corta o fim da minha frase:** aumente `JARVIS_SILENCIO_MS` (ex.: 1200).
- **Ele ainda capta a própria voz:** use fones, ou aumente o tempo de espera em `voz.py` (`time.sleep(0.45)`).
- **Sem som / erro de pygame:** use Python 3.11 ou 3.12. Sem internet ele usa a voz offline do sistema.
- **Erro de chave:** confira `ANTHROPIC_API_KEY` no `.env`.

## Estrutura

```
jarvis/
  principal.py    laço: ouvir -> pensar -> agir -> falar
  ouvido.py       microfone, detecção de fala e transcrição
  voz.py          síntese de voz e reprodução
  cerebro.py      Claude + chamada de ferramentas
  ferramentas.py  ações no PC (adicione as suas aqui)
  config.py       configurações e atalhos de apps
```

## Segurança

Ele executa ações reais no seu PC. Apagar arquivos e rodar comandos exigem confirmação por voz. Nunca suba o `.env` para o GitHub (já está no `.gitignore`).
