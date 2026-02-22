## 📋 Documentazione Tecnica - Versione 3

Questa versione rappresenta l'evoluzione stabile del progetto, integrando una gestione avanzata dei file, un sistema di mappatura dei livelli di difficoltà e un motore di esportazione automatizzato.

### 1. 📂 Struttura e Gestione File

Il sistema è stato riorganizzato per una gestione professionale degli asset:

- **Database:** Il file `db_esercizi.csv` viene ora caricato dalla sottocartella dedicata `CSV/`.
- **Template Dinamici:** I modelli LaTeX risiedono nella cartella `templates/`. Il sistema seleziona il file (`tver_1.tex`, `tver_2.tex`, ecc.) in base al campo **ID Template** impostato nella webapp.
- **Immagini:** Il rendering delle anteprime scansiona la cartella `images/` supportando formati multipli (`.png`, `.jpg`, `.jpeg`, `.svg`).

### 2. 🧠 Logica Didattica e Livelli

È stata introdotta una mappatura intelligente per la corrispondenza tra database e output finale:

- **Conversione Livelli:** I livelli numerici del database (1-5) vengono convertiti automaticamente in lettere nel documento LaTeX:
  - `1 → [A]`, `2 → [B]`, `3 → [C]`, `4 → [D]`, `5 → [E]`.
- **Obiettivi Minimi (Asterisco):** La spunta "Asterisco (DSA)" applica il simbolo `*` nel PDF **esclusivamente** agli esercizi di livello **1 (A)**, garantendo la corretta segnalazione degli obiettivi minimi senza intervenire manualmente.

### 3. 🚀 Motore di Esportazione ZIP

La sezione di esportazione è stata potenziata per generare un pacchetto completo pronto all'uso:

- **Doppia Fila (A/B):** Genera istantaneamente i file `.tex` per entrambe le file.
  - **Fila A:** Utilizza l'esatto esercizio selezionato nell'anteprima.
  - **Fila B:** Applica una rotazione automatica, selezionando l'esercizio successivo nel database per la stessa categoria (se disponibile).
- **Naming Convention Dinamica:** I file prodotti seguono lo standard:
  - `verifica_disciplina_classe_idver_FILA_X.tex`
  - `configurazione_disciplina_classe_idver.json`
- **Robustezza Dati:** Implementato un `json_serialize_helper` per prevenire errori di compatibilità tra i tipi di dati Pandas (`int64`) e lo standard JSON.

### 4. 🖥️ Interfaccia Utente (UI/UX)

- **Sidebar Control:** Pulsanti dedicati per espandere o comprimere tutti i blocchi esercizi contemporaneamente.
- **Navigazione Anteprime:** Sistema di frecce `⬅️` `➡️` per scorrere i varianti disponibili nel database mantenendo lo stato sincronizzato con l'export.
- **Clonazione Varianti:** Quando si aggiunge una nuova variante a un blocco esistente, il sistema eredita automaticamente i parametri (Argomento, Sub, Livello) dell'ultima inserita per velocizzare il lavoro.

---

### Prossimi Passaggi Consigliati

- **Validazione Template:** Assicurarsi che i file `tver_X.tex` contengano i tag corretti `%<<SECESR>>` e `%<<SECTPL>>`.
- **Gestione Immagini in ZIP:** Valutare se includere anche la cartella `images/` nel pacchetto ZIP finale per rendere il progetto LaTeX totalmente portabile.

---