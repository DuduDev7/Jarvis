"""Cérebro do Jarvis: conversa com o Claude e executa as ferramentas pedidas."""
import datetime
import platform

import anthropic

from . import config, ferramentas

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


class Cerebro:
    def __init__(self):
        if not config.ANTHROPIC_API_KEY or "cole_sua" in config.ANTHROPIC_API_KEY:
            raise SystemExit("Falta a chave: coloque ANTHROPIC_API_KEY no arquivo .env")
        self.cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.historico = []
        self.busca_web = config.BUSCA_WEB

    def _sistema(self) -> str:
        a = datetime.datetime.now()
        data = f"{DIAS[a.weekday()]}, {a.day} de {MESES[a.month - 1]} de {a.year}, {a:%H:%M}"
        return (
            f"Você é o JARVIS, assistente pessoal de voz de {config.NOME_USUARIO}, inspirado no "
            "J.A.R.V.I.S. do Homem de Ferro: educado, eficiente e com um toque sutil de ironia elegante.\n"
            "REGRAS:\n"
            "- Fale sempre em português do Brasil.\n"
            "- Suas respostas são LIDAS EM VOZ ALTA: no máximo 2 frases curtas, sem markdown, "
            "sem listas, sem emojis e sem URLs. Escreva números como se fala (ex.: 'vinte e três graus').\n"
            "- Para agir no computador, use as ferramentas e depois confirme em uma frase o que foi feito.\n"
            "- Se uma ferramenta falhar, diga o que houve e sugira uma alternativa. Nunca invente resultados.\n"
            "- Para fatos atuais (notícias, placar, cotação, etc.) use a busca web.\n"
            "- Se o usuário só cumprimentar, responda com o nome dele e a saudação certa para o horário.\n"
            "- A transcrição de voz pode ter erros; se algo não fizer sentido, peça para repetir.\n"
            f"CONTEXTO: agora é {data}. Cidade padrão: {config.CIDADE_PADRAO}. "
            f"Sistema operacional: {platform.system()}."
        )

    def _chamar(self):
        tools = [f["schema"] for f in ferramentas.FERRAMENTAS.values()]
        if self.busca_web:
            tools.append({"type": "web_search_20250305", "name": "web_search", "max_uses": 3})
        try:
            return self.cliente.messages.create(
                model=config.MODELO,
                max_tokens=700,
                system=self._sistema(),
                tools=tools,
                messages=self.historico,
            )
        except anthropic.BadRequestError as e:
            if self.busca_web and "web_search" in str(e).lower():
                print("⚠️  Busca web indisponível na sua conta; desativando.")
                self.busca_web = False
                return self._chamar()
            raise

    def responder(self, texto: str) -> str:
        base = len(self.historico)
        self.historico.append({"role": "user", "content": texto})
        resposta = ""
        try:
            for _ in range(8):
                resp = self._chamar()
                self.historico.append({"role": "assistant", "content": resp.content})

                if resp.stop_reason == "tool_use":
                    resultados = []
                    for b in resp.content:
                        if b.type == "tool_use":
                            saida = ferramentas.executar(b.name, b.input)
                            resultados.append(
                                {"type": "tool_result", "tool_use_id": b.id, "content": saida}
                            )
                    self.historico.append({"role": "user", "content": resultados})
                    continue
                if resp.stop_reason == "pause_turn":
                    continue

                resposta = " ".join(b.text for b in resp.content if b.type == "text").strip()
                break
        except Exception:
            del self.historico[base:]
            raise

        # guarda só o texto do turno (histórico leve e sem blocos de ferramentas)
        del self.historico[base:]
        self.historico += [
            {"role": "user", "content": texto},
            {"role": "assistant", "content": resposta or "Pronto."},
        ]
        self.historico = self.historico[-24:]
        while self.historico and self.historico[0]["role"] != "user":
            self.historico.pop(0)
        return resposta or "Pronto."
