
## 1. Delocalizzazione del CSV: Da "File" a "Database Dinamico"

Nella V8, il CSV era un corpo estraneo che dovevi trascinarti dietro. Nella V9, il dato è **delocalizzato** e **astratto**.

* **Aggiornamento in Tempo Reale:** Non devi più fare il "push" del codice su GitHub o Render solo perché hai corretto un refuso in un esercizio. Modifichi la cella su Google Sheets e l'app Streamlit legge il dato aggiornato al refresh successivo (grazie al parametro `ttl=600`).
* **Collaborazione Multi-utente:** Puoi condividere il foglio Google con altri colleghi. Loro inseriscono gli esercizi nel foglio (interfaccia familiare), e la tua app li trasforma automaticamente in LaTeX.
* **Integrità del Dato:** Usando Google Sheets come database, eviti i classici problemi di "encoding" dei CSV (caratteri speciali che saltano, virgole che spostano le colonne) perché l'API gestisce il trasferimento dei dati in formato JSON strutturato.

---

## 2. Il Sistema di Autenticazione (Google Cloud Platform)

Questa è la parte più "professionale" del progetto. Non stiamo usando una password comune, ma un'**autenticazione tramite Service Account**.

### Come funziona il "Robot" (Service Account)

Abbiamo creato un'identità virtuale su Google Cloud. Questa identità non è un utente con una mail e una password, ma un **profilo tecnico** che possiede una coppia di chiavi crittografiche (Pubblica/Privata).

1. **Il File JSON delle Credenziali:** Quando scarichi il file da Google Cloud, ottieni una chiave privata. È la "firma digitale" che permette a Streamlit di dire a Google: *"Sono io, l'app CreVer, e ho il permesso di entrare"*.
2. **Il Principio del Minimo Privilegio:** Il tuo robot non può vedere tutto il tuo Google Drive. Può vedere **solo** i file che hai esplicitamente condiviso con la sua email (`client_email`). È un sistema di sicurezza a compartimenti stagni.
3. **Protocollo OAuth2 sotto il cofano:** Streamlit GSheets Connection gestisce il protocollo OAuth2 per te. Invia la chiave privata, riceve un "Token di accesso" temporaneo e lo usa per le chiamate API. Tutto questo avviene in millisecondi senza che l'utente veda nulla.

---

## 3. Sicurezza: Dal file `secrets.toml` a Render

In locale usi il file `secrets.toml`, ma **attenzione**: quel file non deve mai finire su GitHub (è nel `.gitignore`, spero!).

Quando caricherai l'app su **Render**, non caricherai il file. Userai le **Environment Variables**:

* Copi il contenuto del file TOML.
* Lo incolli nelle impostazioni di Render.
* In questo modo, le tue chiavi private rimangono criptate nei server di Render e non sono visibili nel codice sorgente.

---

## 💡 Riflessione tecnica: Perché è meglio?

Se domani il tuo database dovesse crescere da 100 a 10.000 esercizi, il tuo codice non cambierebbe di una virgola. Hai separato la **logica applicativa** (Python/Streamlit) dal **deposito dei dati** (Google Cloud). Questa si chiama *Separation of Concerns* ed è la base del software moderno.
