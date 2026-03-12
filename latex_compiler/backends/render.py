"""
backends/render.py
==================
Backend per la compilazione remota su un servizio FastAPI deployato su Render.com.

L'API di Render.com è identica a quella HuggingFace (stessa struttura FastAPI),
l'unica differenza è l'URL e il metodo di autenticazione (Bearer token invece di x-api-key).

Sezione attesa in latex_config.toml:

    [render]
    api_url = "https://il-tuo-servizio.onrender.com/compile-multiple"
    api_key = ""      # oppure lascia vuoto e usa la variabile d'ambiente RENDER_API_KEY
    timeout = 180

Se il tuo servizio su Render usa una struttura API diversa, modifica solo
il metodo compile() — il resto del wrapper non cambia.
"""

import os

from .base import BaseLatexBackend
from .huggingface import HuggingFaceBackend   # riusa l'helper _post_zip

try:
    import requests
except ImportError:
    requests = None


class RenderBackend(BaseLatexBackend):

    def compile(self, zip_bytes: bytes) -> bytes:
        if requests is None:
            raise RuntimeError(
                "requests non installato. Esegui: pip install requests"
            )

        api_url = self.config.get("api_url", "")
        if not api_url:
            raise RuntimeError(
                "api_url mancante nella sezione [render] del config."
            )

        # Render di solito usa Bearer token — adatta se usi un altro schema
        api_key = self.config.get("api_key") or os.environ.get("RENDER_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "API key non trovata. Impostala in latex_config.toml "
                "oppure nella variabile d'ambiente RENDER_API_KEY."
            )

        timeout = int(self.config.get("timeout", 180))
        headers = {"Authorization": f"Bearer {api_key}"}

        # Stesso meccanismo HTTP di HuggingFace — riusa l'helper
        return HuggingFaceBackend._post_zip(api_url, zip_bytes, headers, timeout)
