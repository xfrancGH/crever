"""
backends/huggingface.py
=======================
Backend per la compilazione remota sul Docker FastAPI su HuggingFace Spaces.

Sezione attesa in latex_config.toml:

    [huggingface]
    api_url = "https://xfrancgh-compiletex.hf.space/compile-multiple"
    api_key = ""      # oppure lascia vuoto e usa la variabile d'ambiente HF_TOKEN
    timeout = 180
"""

import os
import threading
import time

from .base import BaseLatexBackend

try:
    import requests
except ImportError:
    requests = None


class HuggingFaceBackend(BaseLatexBackend):

    def compile(self, zip_bytes: bytes) -> bytes:
        if requests is None:
            raise RuntimeError(
                "requests non installato. Esegui: pip install requests"
            )

        api_url = self.config.get("api_url", "")
        if not api_url:
            raise RuntimeError(
                "api_url mancante nella sezione [huggingface] del config."
            )

        api_key = self.config.get("api_key") or os.environ.get("HF_TOKEN", "")
        if not api_key:
            raise RuntimeError(
                "API key non trovata. Impostala in latex_config.toml "
                "oppure nella variabile d'ambiente HF_TOKEN."
            )

        timeout = int(self.config.get("timeout", 180))
        return self._post_zip(api_url, zip_bytes, {"x-api-key": api_key}, timeout)

    # ------------------------------------------------------------------
    #  Helper condiviso (può essere riutilizzato da backend simili)
    # ------------------------------------------------------------------
    @staticmethod
    def _post_zip(api_url: str, zip_bytes: bytes, headers: dict, timeout: int) -> bytes:
        """Invia lo ZIP via POST e attende il risultato con progress log."""
        holder: dict = {"data": None, "error": None, "done": False}

        def call():
            try:
                files = {"file": ("upload.zip", zip_bytes, "application/zip")}
                res = requests.post(api_url, files=files, headers=headers, timeout=timeout)
                if res.status_code != 200:
                    holder["error"] = f"Errore HTTP {res.status_code}: {res.text[:500]}"
                else:
                    holder["data"] = res.content
            except Exception as exc:
                holder["error"] = str(exc)
            finally:
                holder["done"] = True

        thread = threading.Thread(target=call, daemon=True)
        thread.start()

        start = time.time()
        while not holder["done"]:
            if holder["error"]:
                break
            elapsed = time.time() - start
            if elapsed > timeout:
                holder["error"] = "Timeout della richiesta"
                break
            pct = min(int((elapsed / timeout) * 100), 99)
            print(f"\r[INFO] Compilazione remota... {pct}%", end="", flush=True)
            time.sleep(1)

        print()
        if holder["error"]:
            raise RuntimeError(holder["error"])

        return holder["data"]
