"""
backends/local.py
=================
Backend per la compilazione locale tramite pdflatex.

Sezione attesa in latex_config.toml:

    [local]
    pdflatex_path = "pdflatex"   # percorso all'eseguibile (o nome nel PATH)
    work_dir      = ""           # cartella temp (vuoto = temp di sistema)
    timeout       = 60           # secondi per ogni compilazione
    passes        = 2            # passate pdflatex (utile per ref. incrociati)
"""

import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path

from .base import BaseLatexBackend

try:
    from PyPDF2 import PdfWriter
except ImportError:
    PdfWriter = None


class LocalBackend(BaseLatexBackend):

    def compile(self, zip_bytes: bytes) -> bytes:
        if PdfWriter is None:
            raise RuntimeError(
                "PyPDF2 non installato. Esegui: pip install PyPDF2"
            )

        pdflatex   = self.config.get("pdflatex_path") or "pdflatex"
        timeout    = int(self.config.get("timeout", 60))
        passes     = int(self.config.get("passes", 2))
        work_base  = self.config.get("work_dir") or None

        combined_name  = self.config.get("combined_pdf_name",  "00_TUTTE_LE_VERIFICHE.pdf")
        keep_individual = self.config.get("keep_individual_pdfs", True)

        work_dir   = Path(work_base or tempfile.gettempdir()) / f"latex_{uuid.uuid4()}"
        input_dir  = work_dir / "input"
        output_dir = work_dir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Estrai lo ZIP
            zip_in = work_dir / "upload.zip"
            zip_in.write_bytes(zip_bytes)
            with zipfile.ZipFile(zip_in, "r") as zf:
                zf.extractall(input_dir)

            tex_files = sorted(input_dir.rglob("*.tex"))
            if not tex_files:
                raise RuntimeError("Nessun file .tex trovato nello ZIP.")

            merger       = PdfWriter()
            compiled_any = False

            for tex_path in tex_files:
                current_dir = tex_path.parent
                for _ in range(passes):
                    result = subprocess.run(
                        [pdflatex, "-interaction=nonstopmode",
                         "-output-directory", str(current_dir), str(tex_path)],
                        capture_output=True, text=True,
                        cwd=str(current_dir), timeout=timeout,
                    )
                    if result.returncode != 0:
                        print(f"[WARN] Errore LaTeX su '{tex_path.name}':\n"
                              + result.stdout[-2000:])

                pdf_path = tex_path.with_suffix(".pdf")
                if pdf_path.exists():
                    dest = output_dir / pdf_path.name
                    shutil.move(str(pdf_path), str(dest))
                    merger.append(str(dest))
                    compiled_any = True
                    print(f"[OK] Compilato: {tex_path.name}")
                else:
                    print(f"[SKIP] PDF non generato per: {tex_path.name}")

            if not compiled_any:
                raise RuntimeError("Nessun PDF generato. Controlla i log LaTeX.")

            # PDF unificato
            combined_path = output_dir / combined_name
            with open(combined_path, "wb") as fh:
                merger.write(fh)
            merger.close()

            # ZIP di output
            zip_out = work_dir / "risultati.zip"
            with zipfile.ZipFile(zip_out, "w") as zf:
                zf.write(combined_path, combined_name)
                if keep_individual:
                    for f in output_dir.iterdir():
                        if f.name != combined_name and f.suffix == ".pdf":
                            zf.write(f, f.name)

            return zip_out.read_bytes()

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
