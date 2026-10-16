"""Configurações do Jarvis (lidas do arquivo .env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _bool(valor, padrao=True):
    if valor is None or valor == "":
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "s", "yes")


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODELO = os.getenv("JARVIS_MODELO", "claude-sonnet-5-5")
NOME_USUARIO = os.getenv("JARVIS_NOME", "Eduardo")
CIDADE_PADRAO = os.getenv("JARVIS_CIDADE", "Joinville")
PALAVRA_ATIVACAO = os.getenv("JARVIS_PALAVRA", "jarvis").strip().lower()

# Voz
VOZ = os.getenv("JARVIS_VOZ", "pt-BR-AntonioNeural")
VELOCIDADE_VOZ = os.getenv("JARVIS_VELOCIDADE", "+8%")
TOM_VOZ = os.getenv("JARVIS_TOM", "-4Hz")

# Microfone
DISPOSITIVO_MIC = os.getenv("JARVIS_MIC", "")
SENSIBILIDADE = float(os.getenv("JARVIS_SENSIBILIDADE", "3.0"))
SILENCIO_MS = int(os.getenv("JARVIS_SILENCIO_MS", "900"))
JANELA_CONVERSA_S = float(os.getenv("JARVIS_JANELA_CONVERSA", "8"))

BUSCA_WEB = _bool(os.getenv("JARVIS_BUSCA_WEB"), True)

# Pasta onde o Jarvis guarda notas
PASTA_DADOS = Path.home() / "Jarvis"

# Atalhos de aplicativos (Windows). Chave: nome falado, sem acento e minúsculo.
# Valor: comando/protocolo que o Windows entende. Adicione os seus!
APPS = {
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "calculadora": "calc",
    "bloco de notas": "notepad",
    "explorador": "explorer",
    "explorador de arquivos": "explorer",
    "paint": "mspaint",
    "terminal": "wt",
    "prompt de comando": "cmd",
    "powershell": "powershell",
    "spotify": "spotify:",
    "whatsapp": "whatsapp:",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "configuracoes": "ms-settings:",
    "gerenciador de tarefas": "taskmgr",
}
