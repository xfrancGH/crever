"""
backends/base.py
================
Interfaccia astratta che ogni backend deve implementare.

Per aggiungere un nuovo backend:
  1. Crea backends/nome_backend.py
  2. Fai ereditare da BaseLatexBackend
  3. Implementa il metodo compile()
  4. Aggiungi la sezione [nome_backend] in latex_config.toml
  5. Registra il backend in compiler.py (una riga nel dizionario BACKENDS)
"""

from abc import ABC, abstractmethod


class BaseLatexBackend(ABC):
    """
    Ogni backend riceve la propria sezione del config nel costruttore
    e deve implementare un solo metodo: compile().
    """

    def __init__(self, config: dict):
        """
        Parameters
        ----------
        config : dict
            Sezione del .toml relativa a questo backend,
            es. config["local"], config["huggingface"], ecc.
        """
        self.config = config

    @abstractmethod
    def compile(self, zip_bytes: bytes) -> bytes:
        """
        Compila i file .tex contenuti in zip_bytes.

        Parameters
        ----------
        zip_bytes : bytes
            Contenuto dello ZIP con i file .tex da compilare.

        Returns
        -------
        bytes
            Contenuto dello ZIP con i PDF generati.

        Raises
        ------
        LatexCompilerError (o sottoclasse) in caso di errore.
        """
        ...
