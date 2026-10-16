import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e sem espaços extras (para comparar textos)."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().split())
