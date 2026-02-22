
Ecco un breve riassunto di ciò che rende la **Versione 4** il nostro nuovo standard:

### 1. Integrità dei Dati e Struttura

* **Percorsi Standardizzati:** Il codice cerca i dati in `CSV/`, i template in `templates/` e le immagini in `images/`, rendendo l'installazione ordinata.
* **Supporto JSON Avanzato:** Il caricamento gestisce sia i nuovi file con il campo `istituto` che quelli vecchi, garantendo la retrocompatibilità.

### 2. Motore LaTeX Dinamico

* **Placeholder Intestazione:** La funzione `generate_latex_fila` ora elabora correttamente:
* `IDV` per l'identificativo verifica.
* `{MAT}` per la disciplina (materia).
* `{IST}` per il nome dell'istituto scolastico.


* **Mappatura Didattica:** La conversione automatica dei livelli in lettere (`A-E`) e la gestione condizionale dell'asterisco (`*`) solo per il livello 1 sono perfettamente integrate.

### 3. Sistema di Anteprima e Navigazione

* **Rendering Pulito:** L'anteprima Streamlit rimuove i tag di formatizzazione LaTeX non necessari a video (come `center`) per una lettura più chiara, pur mantenendoli nel file finale.
* **Sync tra le File:** L'uso di `preview_indices` assicura che l'esercizio scelto manualmente per la Fila A sia quello effettivamente esportato, con la Fila B che ruota automaticamente sugli altri esercizi disponibili.

### 4. Esportazione Auto-consistente

* **Cartella Immagini nello ZIP:** Lo script scansiona il testo degli esercizi e include nello ZIP solo le immagini effettivamente citate, mantenendo i percorsi relativi (`images/nome_file.png`). Questo permette al file `.tex` di essere compilato ovunque senza errori di "file not found".
