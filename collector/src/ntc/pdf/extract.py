"""Texto de PDF por página, com detecção de PDF escaneado (G8).

O texto sai exatamente como o pdfplumber o extrai: o gate compara trechos com esse
mesmo texto (normalizando só espaços), então nenhuma limpeza extra é feita aqui.
"""

from __future__ import annotations

import hashlib
import io
import logging

import pdfplumber

from ntc.gate.evidencia import TextoDocumento

# Abaixo disso, a página é considerada sem camada de texto.
MIN_CHARS_PAGINA = 40
# Fração mínima de páginas com texto para o documento ser "com texto".
MIN_FRACAO_COM_TEXTO = 0.5
MAX_PAGINAS = 400

logging.getLogger("pdfminer").setLevel(logging.ERROR)


class NaoEhPdf(ValueError):
    pass


def eh_pdf(conteudo: bytes) -> bool:
    return conteudo[:1024].lstrip().startswith(b"%PDF")


def extrair(conteudo: bytes) -> TextoDocumento:
    """Extrai todas as páginas (texto completo: o gate pode aplicar G5 na coleta)."""
    if not eh_pdf(conteudo):
        raise NaoEhPdf("o conteúdo não começa com %PDF")
    sha = hashlib.sha256(conteudo).hexdigest()
    paginas: dict[int, str] = {}
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        if len(pdf.pages) > MAX_PAGINAS:
            raise ValueError(f"PDF com {len(pdf.pages)} páginas (limite {MAX_PAGINAS})")
        for n, pagina in enumerate(pdf.pages, start=1):
            paginas[n] = pagina.extract_text() or ""
            pagina.flush_cache()
    com_texto = sum(1 for t in paginas.values() if len(t.strip()) >= MIN_CHARS_PAGINA)
    tem_texto = bool(paginas) and com_texto / len(paginas) >= MIN_FRACAO_COM_TEXTO
    return TextoDocumento(sha256=sha, paginas=paginas, completo=True, tem_texto=tem_texto)
