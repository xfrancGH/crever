"""
compiler.py
===========
Wrapper principale. Legge il config, istanzia il backend giusto, espone
un'unica API pubblica: compile_zip().

Questo file NON va mai modificato quando si aggiunge un nuovo backend.
Per aggiungere un backend basta:
  1. Creare backends/nome.py con una classe che eredita BaseLatexBackend
  2. Aggiungere una riga nel dizionario BACKENDS qui sotto
  3. Aggiungere la sezione [nome] in latex_config.toml
"""

from pathlib import Path
from typing import Optional

try:
    import tomllib          # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib   # pip install tomli
    except ImportError:
        tomllib = None

# --- Registro dei backend disponibili -------------------------------------------
from .backends.local        import LocalBackend
from .backends.huggingface  import HuggingFaceBackend
from .backends.render       import RenderBackend
# Per aggiungere un nuovo backend: from backends.nome import NomeBackend

BACKENDS = {
    "local":        LocalBackend,
    "huggingface":  HuggingFaceBackend,
    "render":       RenderBackend,
    # "nome":        NomeBackend,   ← unica riga da aggiungere
}
# --------------------------------------------------------------------------------

DEFAULT_CONFIG = Path(__file__).parent / "latex_config.toml"


class LatexCompiler:
    """
    Punto di ingresso unificato per la compilazione LaTeX.

    Parameters
    ----------
    config_path : str | Path, optional
        Percorso al file .toml. Default: latex_config.toml accanto a compiler.py
    mode : str, optional
        Override della modalità (ignora il valore nel .toml).
    """

    def __init__(
        self,
        config_path: Optional[str | Path] = None,
        mode: Optional[str] = None,
    ):
        self._config = self._load_config(config_path or DEFAULT_CONFIG)
        self.mode = (mode or self._config["compiler"]["mode"]).lower()

        if self.mode not in BACKENDS:
            raise ValueError(
                f"Modalità '{self.mode}' non riconosciuta. "
                f"Disponibili: {list(BACKENDS)}"
            )

        # Passa al backend la propria sezione del config + la sezione [output]
        backend_cfg = {
            **self._config.get(self.mode, {}),
            **self._config.get("output", {}),
        }
        self._backend = BACKENDS[self.mode](backend_cfg)

    def compile_zip(
        self,
        zip_input: "str | Path | bytes",
        output_path: Optional["str | Path"] = None,
    ) -> bytes:
        """
        Compila tutti i file .tex dentro lo ZIP.

        Parameters
        ----------
        zip_input : str | Path | bytes
            Percorso allo ZIP oppure bytes già letti.
        output_path : str | Path, optional
            Se fornito, salva il risultato su file.

        Returns
        -------
        bytes  —  ZIP con i PDF generati.
        """
        if isinstance(zip_input, (str, Path)):
            with open(zip_input, "rb") as fh:
                zip_bytes = fh.read()
        else:
            zip_bytes = zip_input

        if not zip_bytes:
            raise ValueError("ZIP di input vuoto.")

        print(f"[INFO] Backend attivo: {self.mode.upper()}")
        result = self._backend.compile(zip_bytes)

        if output_path:
            with open(output_path, "wb") as fh:
                fh.write(result)
            print(f"[DONE] Output salvato: {output_path}")

        return result

    # ------------------------------------------------------------------
    @staticmethod
    def _load_config(path: "str | Path") -> dict:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"Config non trovato: {path}\n"
                "Assicurati che 'latex_config.toml' sia nella stessa cartella."
            )
        if tomllib is None:
            raise ImportError(
                "Libreria TOML non disponibile.\n"
                "Su Python < 3.11 esegui: pip install tomli"
            )
        with open(path, "rb") as fh:
            return tomllib.load(fh)


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Compila .tex in uno ZIP (locale o remoto)."
    )
    p.add_argument("zip_input",          help="ZIP di input")
    p.add_argument("-o", "--output",     default="output_verifiche.zip")
    p.add_argument("--mode",             choices=list(BACKENDS))
    p.add_argument("--config",           default=None)
    args = p.parse_args()

    LatexCompiler(
        config_path=args.config,
        mode=args.mode,
    ).compile_zip(args.zip_input, output_path=args.output)
