"""Ouvido do Jarvis: captura o microfone, detecta fala (VAD) e transcreve.

IMPORTANTE (anti-eco): o microfone só fica aberto DENTRO de `capturar()`.
Enquanto o Jarvis fala, o microfone está fechado, então ele nunca transcreve a
própria voz.
"""
import collections
import time

import numpy as np
import sounddevice as sd
import speech_recognition as sr

from . import config

TAXA = 16000
BLOCO = 480  # 30 ms por bloco
MS_POR_BLOCO = 30


class Ouvido:
    def __init__(self):
        dev = (config.DISPOSITIVO_MIC or "").strip()
        self.dispositivo = int(dev) if dev.isdigit() else None
        self.reconhecedor = sr.Recognizer()
        self.limiar = 400.0
        self.calibrar()

    @staticmethod
    def _nivel(bloco) -> float:
        return float(np.sqrt(np.mean(bloco.astype(np.float32) ** 2)))

    def calibrar(self, segundos: float = 1.2):
        print("🎚️  Calibrando ruído ambiente... fique em silêncio por um instante.")
        try:
            gravacao = sd.rec(
                int(TAXA * segundos), samplerate=TAXA, channels=1,
                dtype="int16", device=self.dispositivo,
            )
            sd.wait()
        except Exception as e:
            raise SystemExit(
                f"Não consegui abrir o microfone: {e}\n"
                "Rode `python -m jarvis --dispositivos` e coloque o número em JARVIS_MIC no .env."
            )
        audio = gravacao[:, 0]
        niveis = [self._nivel(audio[i:i + BLOCO]) for i in range(0, len(audio) - BLOCO, BLOCO)]
        base = float(np.percentile(niveis, 90)) if niveis else 100.0
        self.limiar = max(250.0, base * config.SENSIBILIDADE)
        print(f"   ruído ≈ {base:.0f} | limiar de voz = {self.limiar:.0f}")

    def capturar(self, timeout=None, max_s: float = 15.0, abortar=None):
        """Espera o usuário falar e devolve o áudio (bytes PCM 16 bit) ou None.

        timeout: segundos esperando alguém começar a falar (None = para sempre).
        abortar: função que, ao devolver True, interrompe a espera.
        """
        pre = collections.deque(maxlen=10)  # ~300 ms antes da fala (não corta o início)
        gravado = []
        falando = False
        consecutivos = 0
        silencio = 0
        blocos_fim = max(1, config.SILENCIO_MS // MS_POR_BLOCO)
        inicio = time.time()
        inicio_fala = inicio

        with sd.InputStream(
            samplerate=TAXA, channels=1, dtype="int16",
            blocksize=BLOCO, device=self.dispositivo,
        ) as fluxo:
            while True:
                if abortar and abortar():
                    return None
                dados, _ = fluxo.read(BLOCO)
                bloco = dados[:, 0].copy()
                nivel = self._nivel(bloco)
                agora = time.time()

                if not falando:
                    pre.append(bloco)
                    consecutivos = consecutivos + 1 if nivel > self.limiar else 0
                    if consecutivos >= 3:
                        falando = True
                        gravado = list(pre)
                        inicio_fala = agora
                        silencio = 0
                    elif timeout is not None and agora - inicio >= timeout:
                        return None
                else:
                    gravado.append(bloco)
                    silencio = 0 if nivel > self.limiar else silencio + 1
                    if silencio >= blocos_fim or agora - inicio_fala >= max_s:
                        break

        audio = np.concatenate(gravado)
        if len(audio) / TAXA < 0.5:  # barulho curto (clique, tosse)
            return None
        return audio.tobytes()

    def transcrever(self, pcm: bytes) -> str:
        audio = sr.AudioData(pcm, TAXA, 2)
        try:
            return self.reconhecedor.recognize_google(audio, language="pt-BR").strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"⚠️  Falha no reconhecimento de voz (internet?): {e}")
            return ""
