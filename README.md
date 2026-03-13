Il pattern giusto è **Strategy**: un file per ogni backend, un'interfaccia comune, il wrapper che li orchestra.

```
latex_compiler/
├── latex_config.toml          ← unico file di config
├── compiler.py                ← wrapper (non si tocca mai)
├── backends/
│   ├── base.py                ← interfaccia astratta comune
│   ├── local.py               ← backend pdflatex locale
│   ├── huggingface.py         ← backend HuggingFace
│   └── render.py              ← backend Render.com (o qualsiasi altro)
└── esempio_integrazione.py
```

**Aggiungere un nuovo backend diventa**: creare `backends/render.py`, implementare un solo metodo `compile(zip_bytes) -> bytes`, aggiungere tre righe al `.toml`. Il `compiler.py` non si tocca mai.Struttura finale — il pattern **Strategy** rende tutto triviale da estendere:

```
latex_compiler/
├── latex_config.toml       ← cambia "mode" e sei a posto
├── compiler.py             ← wrapper, non si tocca mai
└── backends/
    ├── base.py             ← interfaccia astratta (1 metodo: compile)
    ├── local.py            ← pdflatex locale
    ├── huggingface.py      ← FastAPI su HF Spaces
    └── render.py           ← FastAPI su Render.com
```

### Aggiungere un quarto backend in futuro

Sono esattamente **3 operazioni**:

1. Crea `backends/nuovo.py`, eredita `BaseLatexBackend`, implementa `compile()`
2. Aggiungi **una riga** in `compiler.py` nel dizionario `BACKENDS`:
   ```python
   "nuovo": NuovoBackend,
   ```
3. Aggiungi la sezione `[nuovo]` in `latex_config.toml`

Il `compiler.py` non cambia strutturalmente mai. Nota anche che `render.py` riusa l'helper `_post_zip` di `huggingface.py` — se aggiungi un altro servizio REST con la stessa struttura API, sono letteralmente 10 righe di codice.