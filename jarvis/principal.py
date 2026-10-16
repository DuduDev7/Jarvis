"""Laço principal do Jarvis: ouvir -> pensar -> agir -> falar."""
import argparse
import difflib
import queue
import re
import sys

import anthropic

from . import config, ferramentas
from .util import normalizar

SAIR = ("desligar jarvis", "encerrar jarvis", "fechar jarvis", "sair do programa")
DORMIR = ("tchau", "pode dormir", "ate logo", "fique em silencio", "so isso", "pode descansar")
SIM = {"sim", "pode", "confirmo", "claro", "autorizo", "manda", "positivo", "faca", "isso", "ok"}
NAO = {"nao", "cancela", "cancelar", "negativo", "para", "pare", "jamais"}


class Jarvis:
    def __init__(self, tecla: bool = False):
        from .cerebro import Cerebro
        from .ouvido import Ouvido
        from .voz import Voz

        print("⚙️  Iniciando o Jarvis...")
        self.voz = Voz()
        self.ouvido = Ouvido()
        self.cerebro = Cerebro()
        self.alertas: "queue.Queue" = queue.Queue()
        self.tecla = tecla
        ferramentas.CONTEXTO["confirmar"] = self.confirmar
        ferramentas.CONTEXTO["alertas"] = self.alertas
        padrao = "|".join(
            [re.escape(config.PALAVRA_ATIVACAO), "jarves", "jarvez", "jarviz", "garvis", "charvis"]
        )
        self._re_ativacao = re.compile(rf"\b(?:{padrao})\b", re.IGNORECASE)

    # ---------------------------------------------------------------- escuta
    def _eco(self, texto: str) -> bool:
        """True se o que ouvimos parece ser a própria voz do Jarvis."""
        t, u = normalizar(texto), normalizar(self.voz.ultima_fala)
        if not t or not u:
            return False
        if len(t) > 10 and t in u:
            return True
        return len(t) > 8 and difflib.SequenceMatcher(None, t, u).ratio() > 0.65

    def ouvir_texto(self, timeout=None, abortar=None) -> str:
        pcm = self.ouvido.capturar(timeout=timeout, abortar=abortar)
        if not pcm:
            return ""
        texto = self.ouvido.transcrever(pcm)
        if not texto:
            return ""
        print(f"🎤 Você: {texto}")
        return "" if self._eco(texto) else texto

    def _extrair_comando(self, texto: str):
        """None = sem palavra de ativação. '' = só chamou. Senão, o comando."""
        m = self._re_ativacao.search(texto)
        if not m:
            return None
        depois = texto[m.end():].strip(" ,.:;!?-")
        antes = texto[:m.start()].strip(" ,.:;!?-")
        return depois or antes

    def confirmar(self, pergunta: str) -> bool:
        self.voz.falar(pergunta + " Diga sim ou não.")
        resp = normalizar(self.ouvir_texto(timeout=8))
        palavras = set(resp.split())
        if palavras & NAO:
            return False
        return bool(palavras & SIM)

    # ----------------------------------------------------------------- ações
    def processar(self, texto: str):
        n = normalizar(texto)
        if any(f in n for f in SAIR):
            self.voz.falar(f"Desligando. Até logo, {config.NOME_USUARIO}.")
            return "sair"
        if len(n.split()) <= 5 and any(f in n for f in DORMIR):
            self.voz.falar(f"Até logo, {config.NOME_USUARIO}.")
            return "dormir"
        print("🧠 pensando...")
        try:
            resposta = self.cerebro.responder(texto)
        except anthropic.AuthenticationError:
            resposta = "Sua chave da Anthropic parece inválida. Confira o arquivo .env."
        except Exception as e:
            print(f"⚠️  Erro: {e}")
            resposta = "Tive um problema para pensar agora. Tente de novo."
        self.voz.falar(resposta)
        return None

    def _avisos(self):
        while not self.alertas.empty():
            self.voz.falar(f"{config.NOME_USUARIO}, lembrete: {self.alertas.get()}")

    # ----------------------------------------------------------------- laço
    def executar(self):
        self.voz.falar(f"Sistemas online. Em que posso ajudar, {config.NOME_USUARIO}?")
        if self.tecla:
            print("⌨️  Modo tecla: aperte Enter, fale, e espere a resposta. (Ctrl+C para sair)")
        else:
            print(f'👂 Diga "{config.PALAVRA_ATIVACAO.capitalize()}" para me chamar. (Ctrl+C para sair)')

        while True:
            self._avisos()
            if self.tecla:
                input("⏎  Enter para falar... ")
                texto = self.ouvir_texto(timeout=6)
                if not texto:
                    continue
                if self.processar(texto) == "sair":
                    break
                continue

            texto = self.ouvir_texto(abortar=lambda: not self.alertas.empty())
            if not texto:
                continue
            comando = self._extrair_comando(texto)
            if comando is None:
                continue
            if comando == "":
                self.voz.falar("Pois não?")
                comando = self.ouvir_texto(timeout=6)
                if not comando:
                    continue
            if self.processar(comando) == "sair":
                break
            # janela de acompanhamento
            seguinte = self.ouvir_texto(timeout=config.JANELA_CONVERSA_S)
            while seguinte:
                extraido = self._extrair_comando(seguinte)
                if extraido is not None:
                    seguinte = extraido or self.ouvir_texto(timeout=6)
                    if not seguinte:
                        break
                r = self.processar(seguinte)
                if r == "sair":
                    return
                if r == "dormir":
                    break
                seguinte = self.ouvir_texto(timeout=config.JANELA_CONVERSA_S)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="jarvis", description="Jarvis - assistente de voz")
    ap.add_argument("--tecla", action="store_true", help="aperta Enter para falar (sem palavra de ativação)")
    ap.add_argument("--vozes", action="store_true", help="lista as vozes em português")
    ap.add_argument("--dispositivos", action="store_true", help="lista os microfones")
    args = ap.parse_args()

    if args.vozes:
        from .voz import listar_vozes

        return listar_vozes()
    if args.dispositivos:
        import sounddevice as sd

        return print(sd.query_devices())

    try:
        Jarvis(tecla=args.tecla).executar()
    except KeyboardInterrupt:
        print("\n👋 Até logo!")


if __name__ == "__main__":
    main()
