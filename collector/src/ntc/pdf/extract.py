"""Texto de PDF por página, com detecção de PDF escaneado (G8).

Usa o pdftotext (Poppler): cerca de 25 vezes mais rápido que o pdfplumber nos editais
testados, com as mesmas cláusulas e o espaçamento entre palavras preservado (o PDFium juntava
palavras: "Asinscrições"). O gate compara trechos com este mesmo texto, normalizando só espaços.
Requer o pacote poppler-utils (os workflows instalam se faltar).
"""

from __future__ import annotations

import hashlib

import shutil
import subprocess
import tempfile

from ntc.gate.evidencia import TextoDocumento

# Abaixo disso, a página é considerada sem camada de texto.
MIN_CHARS_PAGINA = 40
# Fração mínima de páginas com texto para o documento ser "com texto".
MIN_FRACAO_COM_TEXTO = 0.5
MAX_PAGINAS = 400



class NaoEhPdf(ValueError):
    pass


def eh_pdf(conteudo: bytes) -> bool:
    return conteudo[:1024].lstrip().startswith(b"%PDF")


def extrair(conteudo: bytes) -> TextoDocumento:
    """Extrai todas as páginas (texto completo: o gate pode aplicar G5 na coleta)."""
    if not eh_pdf(conteudo):
        raise NaoEhPdf("o conteúdo não começa com %PDF")
    sha = hashlib.sha256(conteudo).hexdigest()
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext não encontrado: instale poppler-utils")
    with tempfile.TemporaryDirectory() as tmp:
        entrada = f"{tmp}/doc.pdf"
        with open(entrada, "wb") as f:
            f.write(conteudo)
        r = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", "-l", str(MAX_PAGINAS + 1), entrada, "-"],
            capture_output=True, timeout=180,
        )
    if r.returncode != 0:
        raise ValueError(f"pdftotext falhou: {r.stderr.decode(errors='replace')[:200]}")
    partes = r.stdout.decode("utf-8", errors="replace").split("\f")
    if partes and not partes[-1].strip():
        partes = partes[:-1]  # o pdftotext termina cada página com \f
    if len(partes) > MAX_PAGINAS:
        raise ValueError(f"PDF com mais de {MAX_PAGINAS} páginas")
    paginas = {n: texto for n, texto in enumerate(partes, start=1)}
    com_texto = sum(1 for t in paginas.values() if len(t.strip()) >= MIN_CHARS_PAGINA)
    tem_texto = bool(paginas) and com_texto / len(paginas) >= MIN_FRACAO_COM_TEXTO
    return TextoDocumento(sha256=sha, paginas=paginas, completo=True, tem_texto=tem_texto)
