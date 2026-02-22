# Documentazione Versione 2

La **Versione 2** rappresenta un salto di qualità significativo nella gestione dell'interfaccia e del rendering dei contenuti, rendendo lo strumento pronto per un utilizzo professionale con database complessi.

## 🛠️ Architettura e Stato

- **Identità Univoca degli Esercizi (**`id_es`**)**: Ogni esercizio viene generato con un ID basato su timestamp. Questo garantisce che i widget di Streamlit non entrino in conflitto e che lo stato di ogni sezione (aperta/chiusa) sia mantenuto correttamente.
- **Gestione Persistente della Vista**: Grazie a `st.session_state`, l'applicazione ricorda quali expander sono aperti o chiusi, evitando fastidiosi "salti" dell'interfaccia durante l'aggiornamento dei dati.
- **Modalità di Avvio Doppia**: Possibilità di iniziare una nuova verifica da zero (selezionando la disciplina dal CSV) o di caricare un file JSON preesistente per modificarlo.

## 👁️ Visualizzazione Avanzata (Rendering)

- **LaTeX Inline Fluido**: La funzione `render_preview` è stata ottimizzata per supportare KaTeX senza spezzare le righe. Il testo e le formule matematiche (es. frazioni come 35​) convivono nello stesso paragrafo per una leggibilità naturale.
- **Integrazione Immagini**: Supporto nativo per il comando LaTeX `\includegraphics`. Il sistema intercetta automaticamente il nome del file, lo cerca nella cartella locale `/images` e lo visualizza direttamente nell'anteprima web.
- **Navigazione Anteprime**: Se per una data combinazione (Tipo/Argomento/Livello) esistono più esercizi nel database, l'utente può scorrere tra le opzioni disponibili tramite frecce di navigazione (`⬅️`, `➡️`) integrate.
- **Soluzioni a Scomparsa**: Se presenti nel CSV, le soluzioni vengono caricate in un expander dedicato all'interno dell'anteprima per una consultazione rapida senza ingombrare la vista.

## ⚙️ Funzionalità Interattive

- **Sidebar di Controllo**:
  - **Expand/Collapse All**: Pulsanti globali per aprire o chiudere tutti gli esercizi con un solo clic.
  - **Reset Totale**: Ripristina l'applicazione allo stato iniziale pulendo la memoria cache.
- **Sistema a Varianti**: Ogni blocco esercizio può contenere più varianti. È possibile aggiungere, clonare o rimuovere varianti specifiche con aggiornamento dinamico dei filtri.
- **Filtri Dinamici**: I menu a tendina (Tipo → Argomento → Subargomento → Livello) si aggiornano in tempo reale in base alle disponibilità effettive nel file `db_esercizi.csv`.

## 📤 Export e Compatibilità

- **Formato JSON Standard**: L'export produce un file JSON pulito e strutturato, che include tutti i metadati della verifica (classe, id_template, disciplina) e la lista dettagliata degli esercizi e delle varianti selezionate.
- **Anteprima Codice**: Un expander finale permette di ispezionare il codice JSON generato prima di procedere al download.

---