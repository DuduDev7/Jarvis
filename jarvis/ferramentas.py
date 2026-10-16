"""Ferramentas (ações) que o Jarvis pode executar no computador.

Para criar uma nova ferramenta, copie uma existente: use o decorador
@ferramenta(...) e devolva sempre um texto curto com o resultado.
"""
import ctypes
import datetime
import os
import platform
import shutil
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

import requests

from . import config
from .util import normalizar

SISTEMA = platform.system()  # Windows | Darwin | Linux
WINDOWS = SISTEMA == "Windows"
MAC = SISTEMA == "Darwin"

# Preenchido pelo programa principal
CONTEXTO = {"confirmar": lambda pergunta: False, "alertas": None}

FERRAMENTAS = {}


def ferramenta(nome, descricao, propriedades=None, obrigatorios=()):
    def deco(fn):
        FERRAMENTAS[nome] = {
            "fn": fn,
            "schema": {
                "name": nome,
                "description": descricao,
                "input_schema": {
                    "type": "object",
                    "properties": propriedades or {},
                    "required": list(obrigatorios),
                },
            },
        }
        return fn

    return deco


def executar(nome: str, args: dict) -> str:
    f = FERRAMENTAS.get(nome)
    if not f:
        return f"Ferramenta desconhecida: {nome}"
    print(f"🔧 {nome}({args})")
    try:
        return str(f["fn"](**args))[:2000]
    except TypeError as e:
        return f"Argumentos inválidos: {e}"
    except Exception as e:
        return f"Erro ao executar {nome}: {e}"


# ----------------------------------------------------------------- utilidades
def _pasta(nome: str):
    """Resolve 'downloads', 'documentos', 'desktop'... para uma pasta existente."""
    home = Path.home()
    mapa = {
        "downloads": ["Downloads", "OneDrive/Downloads"],
        "documentos": ["Documents", "Documentos", "OneDrive/Documents", "OneDrive/Documentos"],
        "desktop": ["Desktop", "Área de Trabalho", "OneDrive/Desktop", "OneDrive/Área de Trabalho"],
        "imagens": ["Pictures", "Imagens", "OneDrive/Pictures", "OneDrive/Imagens"],
        "videos": ["Videos", "Vídeos"],
        "musicas": ["Music", "Músicas"],
    }
    n = normalizar(nome)
    n = {"area de trabalho": "desktop", "documents": "documentos", "fotos": "imagens", "musica": "musicas"}.get(n, n)
    for cand in mapa.get(n, []):
        if (home / cand).is_dir():
            return home / cand
    p = Path(os.path.expanduser(nome))
    return p if p.is_dir() else None


def _tecla(vk: int, vezes: int = 1):
    for _ in range(vezes):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.01)


def _achar_atalho(n: str):
    bases = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]
    melhor = None
    for base in bases:
        for dp, _, arquivos in os.walk(base):
            for f in arquivos:
                if not f.lower().endswith(".lnk"):
                    continue
                stem = normalizar(f[:-4])
                caminho = os.path.join(dp, f)
                if stem == n:
                    return caminho
                if n in stem and (melhor is None or len(stem) < len(melhor[0])):
                    melhor = (stem, caminho)
    return melhor[1] if melhor else None


# ------------------------------------------------------------------ ferramentas
@ferramenta(
    "abrir_aplicativo",
    "Abre um aplicativo instalado no computador (VS Code, Chrome, Spotify, calculadora, Word, etc.).",
    {"nome": {"type": "string", "description": "Nome do aplicativo, como o usuário falou."}},
    ["nome"],
)
def abrir_aplicativo(nome):
    n = normalizar(nome)
    if WINDOWS:
        alvo = config.APPS.get(n)
        if alvo:
            subprocess.Popen(f'start "" "{alvo}"', shell=True)
            return f"Abrindo {nome}."
        atalho = _achar_atalho(n)
        if atalho:
            os.startfile(atalho)
            return f"Abrindo {nome}."
        exe = shutil.which(nome)
        if exe:
            subprocess.Popen([exe])
            return f"Abrindo {nome}."
        return f"Não encontrei o aplicativo {nome}."
    if MAC:
        r = subprocess.run(["open", "-a", nome], capture_output=True)
        return f"Abrindo {nome}." if r.returncode == 0 else f"Não encontrei o aplicativo {nome}."
    exe = shutil.which(nome.lower().replace(" ", "-")) or shutil.which(nome.lower())
    if exe:
        subprocess.Popen([exe])
        return f"Abrindo {nome}."
    return f"Não encontrei o aplicativo {nome}."


@ferramenta(
    "abrir_site",
    "Abre um site no navegador padrão.",
    {"url": {"type": "string", "description": "Endereço, ex.: https://youtube.com"}},
    ["url"],
)
def abrir_site(url):
    url = url.strip()
    if " " in url:
        return "URL inválida."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Abrindo {url}."


@ferramenta(
    "pesquisar_no_navegador",
    "Abre no navegador uma pesquisa no Google, YouTube ou Maps (use quando o usuário pedir para pesquisar/tocar/mostrar algo na tela).",
    {
        "consulta": {"type": "string"},
        "site": {"type": "string", "enum": ["google", "youtube", "maps"], "description": "Padrão: google"},
    },
    ["consulta"],
)
def pesquisar_no_navegador(consulta, site="google"):
    q = quote_plus(consulta)
    urls = {
        "google": f"https://www.google.com/search?q={q}",
        "youtube": f"https://www.youtube.com/results?search_query={q}",
        "maps": f"https://www.google.com/maps/search/{q}",
    }
    webbrowser.open(urls.get(site, urls["google"]))
    return f"Pesquisa aberta no {site}."


_CLIMA = {
    0: "céu limpo", 1: "quase sem nuvens", 2: "parcialmente nublado", 3: "nublado",
    45: "neblina", 48: "neblina", 51: "garoa fraca", 53: "garoa", 55: "garoa forte",
    56: "garoa congelante", 57: "garoa congelante", 61: "chuva fraca", 63: "chuva moderada",
    65: "chuva forte", 66: "chuva congelante", 67: "chuva congelante", 71: "neve fraca",
    73: "neve", 75: "neve forte", 77: "granizo fino", 80: "pancadas de chuva fracas",
    81: "pancadas de chuva", 82: "pancadas de chuva fortes", 85: "pancadas de neve",
    86: "pancadas de neve fortes", 95: "trovoadas", 96: "trovoadas com granizo",
    99: "trovoadas com granizo forte",
}


@ferramenta(
    "clima",
    "Consulta o clima atual e a previsão de uma cidade (padrão: cidade do usuário).",
    {
        "cidade": {"type": "string", "description": "Opcional."},
        "dias": {"type": "integer", "description": "Dias de previsão (1 a 7). Padrão 1."},
    },
)
def clima(cidade="", dias=1):
    cidade = cidade or config.CIDADE_PADRAO
    g = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": cidade, "count": 1, "language": "pt"}, timeout=8,
    ).json()
    if not g.get("results"):
        return f"Não encontrei a cidade {cidade}."
    r = g["results"][0]
    dias = max(1, min(int(dias), 7))
    f = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": r["latitude"], "longitude": r["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
            "timezone": "auto", "forecast_days": dias,
        }, timeout=8,
    ).json()
    c, d = f["current"], f["daily"]
    linhas = [
        f"{r['name']}: agora {c['temperature_2m']} graus (sensação {c['apparent_temperature']}), "
        f"{_CLIMA.get(c['weather_code'], 'tempo variável')}, umidade {c['relative_humidity_2m']}%, "
        f"vento {c['wind_speed_10m']} km/h."
    ]
    for i in range(dias):
        linhas.append(
            f"Dia {d['time'][i]}: mínima {d['temperature_2m_min'][i]}, máxima {d['temperature_2m_max'][i]}, "
            f"{_CLIMA.get(d['weather_code'][i], 'variável')}, chance de chuva {d['precipitation_probability_max'][i]}%."
        )
    return "\n".join(linhas)


@ferramenta(
    "volume",
    "Controla o volume do computador.",
    {
        "acao": {"type": "string", "enum": ["aumentar", "diminuir", "mudo", "definir"]},
        "nivel": {"type": "integer", "description": "0 a 100, só para 'definir'."},
    },
    ["acao"],
)
def volume(acao, nivel=None):
    if WINDOWS:
        if acao == "mudo":
            _tecla(0xAD)
        elif acao == "aumentar":
            _tecla(0xAF, 5)
        elif acao == "diminuir":
            _tecla(0xAE, 5)
        elif acao == "definir":
            if nivel is None:
                return "Faltou informar o nível."
            _tecla(0xAE, 50)
            _tecla(0xAF, round(max(0, min(100, nivel)) / 2))
        return "Volume ajustado."
    if MAC:
        scr = {"aumentar": "set volume output volume ((output volume of (get volume settings)) + 10)",
               "diminuir": "set volume output volume ((output volume of (get volume settings)) - 10)",
               "mudo": "set volume output muted true",
               "definir": f"set volume output volume {nivel or 50}"}[acao]
        subprocess.run(["osascript", "-e", scr])
        return "Volume ajustado."
    cmd = {"aumentar": "10%+", "diminuir": "10%-", "mudo": "toggle", "definir": f"{nivel or 50}%"}[acao]
    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", cmd], capture_output=True)
    return "Volume ajustado."


@ferramenta(
    "midia",
    "Controla a música/vídeo que está tocando (pausar/continuar, próxima, anterior).",
    {"acao": {"type": "string", "enum": ["pausar_ou_tocar", "proxima", "anterior"]}},
    ["acao"],
)
def midia(acao):
    if WINDOWS:
        _tecla({"pausar_ou_tocar": 0xB3, "proxima": 0xB0, "anterior": 0xB1}[acao])
        return "Feito."
    if shutil.which("playerctl"):
        subprocess.run(["playerctl", {"pausar_ou_tocar": "play-pause", "proxima": "next", "anterior": "previous"}[acao]])
        return "Feito."
    return "Controle de mídia não suportado neste sistema."


@ferramenta(
    "buscar_arquivos",
    "Procura arquivos no computador pelo nome e/ou extensão. Devolve os mais recentes.",
    {
        "termo": {"type": "string", "description": "Parte do nome do arquivo."},
        "extensao": {"type": "string", "description": "Ex.: pdf, docx, png."},
        "pasta": {"type": "string", "description": "downloads, documentos, desktop, imagens, videos, musicas. Vazio = todas."},
    },
)
def buscar_arquivos(termo="", extensao="", pasta=""):
    raizes = []
    if pasta and _pasta(pasta):
        raizes = [_pasta(pasta)]
    else:
        for p in ("documentos", "downloads", "desktop", "imagens", "videos", "musicas"):
            if _pasta(p):
                raizes.append(_pasta(p))
    ext = extensao.lower().lstrip(".")
    termo_n = normalizar(termo)
    ignorar = {"node_modules", "__pycache__", "venv", ".venv", "AppData"}
    achados, limite, parar = [], time.time() + 8, False
    for raiz in raizes:
        for dp, dns, arquivos in os.walk(raiz):
            dns[:] = [d for d in dns if d not in ignorar and not d.startswith(".")]
            for f in arquivos:
                if ext and not f.lower().endswith("." + ext):
                    continue
                if termo_n and termo_n not in normalizar(f):
                    continue
                p = os.path.join(dp, f)
                try:
                    achados.append((os.path.getmtime(p), p))
                except OSError:
                    pass
            if time.time() > limite:
                parar = True
                break
        if parar:
            break
    achados.sort(reverse=True)
    if not achados:
        return "Nenhum arquivo encontrado."
    return "\n".join(p for _, p in achados[:8])


@ferramenta(
    "abrir_arquivo",
    "Abre um arquivo ou pasta pelo caminho completo (use buscar_arquivos antes se não souber o caminho).",
    {"caminho": {"type": "string"}},
    ["caminho"],
)
def abrir_arquivo(caminho):
    p = Path(os.path.expanduser(caminho))
    if not p.exists():
        return "Esse caminho não existe."
    if WINDOWS:
        os.startfile(str(p))
    elif MAC:
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])
    return f"Abrindo {p.name}."


@ferramenta(
    "criar_pasta",
    "Cria uma pasta nova.",
    {
        "nome": {"type": "string"},
        "local": {"type": "string", "description": "documentos, downloads, desktop... Padrão: desktop."},
    },
    ["nome"],
)
def criar_pasta(nome, local="desktop"):
    base = _pasta(local) or Path.home()
    destino = base / Path(nome).name
    destino.mkdir(parents=True, exist_ok=True)
    return f"Pasta criada em {destino}."


@ferramenta(
    "mover_para_lixeira",
    "Envia um arquivo ou pasta para a lixeira (pede confirmação por voz).",
    {"caminho": {"type": "string"}},
    ["caminho"],
)
def mover_para_lixeira(caminho):
    from send2trash import send2trash

    p = Path(os.path.expanduser(caminho))
    if not p.exists():
        return "Esse caminho não existe."
    if not CONTEXTO["confirmar"](f"Posso enviar {p.name} para a lixeira?"):
        return "O usuário não autorizou."
    send2trash(str(p))
    return f"{p.name} foi para a lixeira."


@ferramenta(
    "anotar",
    "Salva uma anotação/lembrete de texto no arquivo de notas do usuário.",
    {"texto": {"type": "string"}},
    ["texto"],
)
def anotar(texto):
    config.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    with open(config.PASTA_DADOS / "notas.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] {texto}\n")
    return "Anotado."


@ferramenta("ler_notas", "Lê as últimas anotações salvas pelo usuário.")
def ler_notas():
    arq = config.PASTA_DADOS / "notas.txt"
    if not arq.exists():
        return "Você ainda não tem anotações."
    return "".join(arq.read_text(encoding="utf-8").splitlines(keepends=True)[-15:])


@ferramenta(
    "definir_timer",
    "Define um timer/lembrete que o Jarvis anuncia por voz quando terminar.",
    {
        "segundos": {"type": "integer", "description": "Tempo em segundos."},
        "mensagem": {"type": "string", "description": "O que lembrar."},
    },
    ["segundos", "mensagem"],
)
def definir_timer(segundos, mensagem):
    t = threading.Timer(max(1, int(segundos)), lambda: CONTEXTO["alertas"].put(mensagem))
    t.daemon = True
    t.start()
    return f"Timer de {int(segundos)} segundos definido."


@ferramenta(
    "executar_comando",
    "Executa um comando no terminal do computador (pede confirmação por voz). Use só quando nenhuma outra ferramenta servir.",
    {"comando": {"type": "string"}},
    ["comando"],
)
def executar_comando(comando):
    if not CONTEXTO["confirmar"]("Posso executar um comando no terminal?"):
        return "O usuário não autorizou."
    r = subprocess.run(
        comando, shell=True, capture_output=True, text=True, errors="replace",
        timeout=30, cwd=str(Path.home()),
    )
    saida = (r.stdout + r.stderr).strip()
    return f"Código {r.returncode}. {saida[:800]}"
