"""Voz do Jarvis: síntese com Edge-TTS (voz neural) e reprodução com pygame.

A fala é dividida em frases: enquanto uma toca, a próxima já está sendo gerada,
o que reduz a espera. Se a internet cair, usa a voz offline do sistema.
"""
import asyncio
import os
import queue
import re
import shutil
import tempfile
import threading
import time

import edge_tts

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from . import config  # noqa: E402


def limpar(texto: str) -> str:
    t = re.sub(r"https?://\S+", "link", texto)
    t = re.sub(r"[*_`#>~|]+", "", t)
    t = re.sub(r"^\s*[-•]\s+", "", t, flags=re.M)
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)  # emojis
    return re.sub(r"\s+", " ", t).strip()


def dividir(texto: str, minimo: int = 40):
    partes = re.split(r"(?<=[.!?;:])\s+", texto)
    saida, atual = [], ""
    for p in partes:
        atual = f"{atual} {p}".strip()
        if len(atual) >= minimo:
            saida.append(atual)
            atual = ""
    if atual:
        saida.append(atual)
    return saida


class Voz:
    def __init__(self):
        self.ultima_fala = ""
        self._offline = None
        self._pygame_ok = False
        try:
            pygame.mixer.init()
            self._pygame_ok = True
        except Exception as e:
            print(f"⚠️  Áudio (pygame) indisponível, usando voz offline: {e}")

    async def _sintetizar(self, texto: str, caminho: str):
        com = edge_tts.Communicate(
            texto, config.VOZ, rate=config.VELOCIDADE_VOZ, pitch=config.TOM_VOZ
        )
        await com.save(caminho)

    def falar(self, texto: str):
        texto = limpar(texto)
        if not texto:
            return
        self.ultima_fala = texto
        print(f"🤖 Jarvis: {texto}")

        partes = dividir(texto)
        fila: "queue.Queue" = queue.Queue()
        pasta = tempfile.mkdtemp(prefix="jarvis_")

        def produtor():
            for i, parte in enumerate(partes):
                caminho = os.path.join(pasta, f"{i}.mp3")
                try:
                    asyncio.run(self._sintetizar(parte, caminho))
                    fila.put((parte, caminho))
                except Exception:
                    fila.put((parte, None))
            fila.put(None)

        threading.Thread(target=produtor, daemon=True).start()

        while True:
            item = fila.get()
            if item is None:
                break
            parte, caminho = item
            if caminho and self._pygame_ok:
                self._tocar(caminho)
            else:
                self._falar_offline(parte)

        shutil.rmtree(pasta, ignore_errors=True)
        time.sleep(0.45)  # deixa o eco da sala morrer antes de abrir o microfone

    @staticmethod
    def _tocar(caminho: str):
        pygame.mixer.music.load(caminho)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.03)
        pygame.mixer.music.unload()

    def _falar_offline(self, texto: str):
        try:
            if self._offline is None:
                import pyttsx3

                self._offline = pyttsx3.init()
                for v in self._offline.getProperty("voices"):
                    if any(k in f"{v.id} {v.name}".lower() for k in ("pt-br", "brazil", "portugu", "maria", "daniel")):
                        self._offline.setProperty("voice", v.id)
                        break
                self._offline.setProperty("rate", 175)
            self._offline.say(texto)
            self._offline.runAndWait()
        except Exception as e:
            print(f"⚠️  Sem voz offline: {e}")


def listar_vozes():
    vozes = asyncio.run(edge_tts.list_voices())
    for v in vozes:
        if v["Locale"].lower().startswith("pt-"):
            print(f'{v["ShortName"]:35} {v["Gender"]}')
