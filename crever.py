import streamlit as st
import json
import pandas as pd
import os
import time
import numpy as np
import zipfile
import io
import re
import requests
from streamlit_gsheets import GSheetsConnection
from googleapiclient.discovery import build
from google.oauth2 import service_account

# --- CONFIGURAZIONE DRIVE ---
FOLDER_ID_TEMPLATES = st.secrets.get("TEMPLATE_FOLDER_ID", "")

if not FOLDER_ID_TEMPLATES:
    st.error("⚠️ Errore: TEMPLATE_FOLDER_ID non trovato nei secrets!")

def json_serialize_helper(obj):
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def parse_image_field(value):
    """
    Estrae URL e nome file da una stringa tipo: 
    IMAGE("https://i.ibb.co/XxdrLNZz/id-81.png") o semplicemente l'URL.
    """
    v = str(value)
    # Cerca il primo URL valido nella stringa
    match = re.search(r'https?://[^\s"\'\)]+', v)
    if match:
        url = match.group(0)
        filename = url.split('/')[-1] # es: id-81.png
        return url, filename
    return None, None

def download_image_from_url(url):
    """Scarica l'immagine e restituisce i byte."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Errore download immagine {url}: {e}")
    return None

# def get_raw_image_url(id_esercizio):
#     """
#     Legge direttamente la formula della cella dal foglio Google 
#     usando gspread, bypassando l'interpretazione NaN di Pandas.
#     """
#     try:
#         # Recupera il client gspread che hai già configurato in sheetMGR.py
#         # Assicurati che la funzione di autenticazione sia visibile qui
#         client = get_gspread_client() 
#         sheet = client.open_by_url(SPREADSHEET_URL).sheet1
        
#         # Cerca la riga dove l'ID corrisponde (supponendo colonna A/1)
#         cell = sheet.find(str(id_esercizio))
#         if cell:
#             # Legge la colonna 3 (IMMAGINE), basandosi sull'indice del tuo foglio
#             formula = sheet.cell(cell.row, 3).value
#             return formula
#     except Exception as e:
#         st.error(f"Errore lettura gspread: {e}")
#     return None

st.set_page_config(page_title="Configuratore Verifiche", layout="wide")

# --- FUNZIONE CARICAMENTO TEMPLATE DA DRIVE ---
@st.cache_data(ttl=3600)
def load_templates_from_drive():
    try:
        # Usa le stesse credenziali già presenti nei secrets per GSheets
        creds_info = st.secrets["connections"]["gsheets"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)

        # Cerca file .tex nella cartella specifica
        query = f"'{FOLDER_ID_TEMPLATES}' in parents and name contains '.tex'"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            st.warning("⚠️ Nessun file .tex trovato nella cartella di Google Drive.")
            return {}

        templates = {}
        for item in items:
            file_id = item['id']
            file_name = item['name']
            # Download contenuto
            content = service.files().get_media(fileId=file_id).execute()
            templates[file_name] = content.decode('utf-8')
        
        return templates
    except Exception as e:
        st.error(f"❌ Errore nel caricamento template da Drive: {e}")
        return {}

st.set_page_config(page_title="Configuratore Verifiche v0.2", layout="wide")

# --- INIZIALIZZAZIONE DEGLI STATI (BLINDATA) ---
# Usiamo un ciclo per assicurarci che tutte le chiavi esistano all'avvio
keys_to_init = {
    'latex_ready': False,
    'pdf_ready': False,
    'current_latex_zip': None,
    'current_pdf_zip': None,
    'current_base_name': "verifica",
    'db_esercizi': None,
    'app_mode': "START",
    'data': None,
    'preview_indices': {}
}

for key, default_value in keys_to_init.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# Carichiamo i template all'avvio (Cache di 1 ora)
templates_db = load_templates_from_drive()

# --- CARICAMENTO DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_full = conn.read(ttl=600)
    df_full.columns = df_full.columns.str.lower()
    df_full = df_full.dropna(how="all")
    if 'livello' in df_full.columns:
        df_full['livello'] = pd.to_numeric(df_full['livello'], errors='coerce').fillna(0).astype(int)
    st.session_state.db_esercizi = df_full
    # st.write("DEBUG: Colonne presenti in df_full:", df_full.columns.tolist())
    # sample_val = df_full['immagine'].iloc[0] # Prendi la prima riga
    # url, name = parse_image_field(sample_val)
    # st.write(f"DEBUG: Input originale: {sample_val}")
    # st.write(f"DEBUG: URL estratto: {url}")
    # st.write(f"DEBUG: Nome file estratto: {name}")
except Exception as e:
    st.error("❌ Errore durante il collegamento a Google Sheets.")
    st.exception(e)
    st.stop()

# Da qui in poi il codice prosegue usando st.session_state.db_esercizi

def render_preview(row):
    """
    Renderizza il testo LaTeX e l'immagine associata (da URL o locale).
    Accetta l'intera riga (row) del DataFrame per avere accesso a 'IMMAGINE'.
    """
    comando_raw = row.get('comando', '')
    if pd.isna(comando_raw) or str(comando_raw).lower() == "nan":
        return
    # --- 1. Rendering del Testo (pulizia base) ---
    comando = str(comando_raw).replace('\\n', '\n')
    comando = re.sub(r'\\begin\{center\}|\\end\{center\}', '', comando)
    st.markdown(comando)

    esercizio_rav = row.get('esercizio', '')
    if pd.isna(esercizio_rav) or str(esercizio_rav).lower() == "nan":
        return
    # --- 1. Rendering del Testo (pulizia base) ---
    esercizio = str(esercizio_rav).replace('\\n', '\n')
    esercizio = re.sub(r'\\begin\{center\}|\\end\{center\}', '', esercizio)
    st.markdown(esercizio)

    # --- 2. Gestione Immagine (la vera modifica v0.4) ---
    valore_img = row.get('immagine') # O 'immagine', verifica il nome colonna
    
    if pd.notna(valore_img) and str(valore_img).strip() != "":
        url, filename = parse_image_field(valore_img)
        if url:
            st.image(url, width=300, caption=f"Immagine: {filename}")
        else:
            # Fallback: prova a vedere se esiste ancora localmente (retrocompatibilità)
            st.warning(f"Immagine non trovata su imgBB. URL estratto: {url}")

    soluzione_raw = row.get('soluzione', '')
    if pd.isna(soluzione_raw) or str(soluzione_raw).lower() == "nan":
        return
    # --- 1. Rendering del Testo (pulizia base) ---
    soluzione = str(soluzione_raw).replace('\\n', '\n')
    soluzione = re.sub(r'\\begin\{center\}|\\end\{center\}', '', soluzione)
    st.markdown(soluzione)

def add_new_exercise(data_store):
    unique_id = f"ex_{int(time.time() * 1000)}"
    data_store['esercizi'].append({"id_es": unique_id, "tipologia": []})
    # Quando aggiungi un nuovo esercizio, forziamo la sua apertura
    st.session_state[f"exp_{unique_id}"] = True
    st.rerun()

# --- GENERAZIONE LATEX (MODIFICATA PER USARE DRIVE) ---
def generate_latex_fila(data, df_full, fila="A", is_correttore=False):
    # 1. SELEZIONE DEL TEMPLATE
    if is_correttore:
        file_target = "tcorr.tex"
    else:
        id_t = data.get('idtemplate', 1)
        file_target = f"tver_{id_t}.tex"
    
    # Recuperiamo il testo dal database caricato all'avvio
    template_content = templates_db.get(file_target)
    if not template_content:
        return f"ERRORE: Template '{file_target}' non trovato su Google Drive.", set()

    final_tex = template_content

    # 2. SOSTITUZIONI GLOBALI (Nuovi placeholder [[...]])
    replacements = {
        "[[ID_VERIFICA]]": str(data.get('idver', '')),
        "[[DISCIPLINA]]": str(data.get('disciplina', '')),
        "[[ISTITUTO]]": str(data.get('istituto', '')),
        "[[CLASSE]]": str(data.get('classe', '')),
        "[[ANNOSC]]": str(data.get('annosc', '')),
        "[[ISTRUZIONI]]": str(data.get('istruzioni', '')).replace('\\n', '\n'),
        "[[FILA]]": fila,
        "[[DOCENTE]]": str(data.get('docente', '')) 
    }

    for placeholder, value in replacements.items():
        final_tex = final_tex.replace(placeholder, value)

    # 3. RICERCA BLOCCHI (Marcatori %<<...>>)
    try:
        ex_match = re.search(r'%<<SECESR>>(.*?)%<<SECESR>>', final_tex, re.DOTALL)
        ex_block_tmpl = ex_match.group(1)
        var_match = re.search(r'%<<SECTPL>>(.*?)%<<SECTPL>>', ex_block_tmpl, re.DOTALL)
        var_block_tmpl = var_match.group(1)
    except Exception:
        return f"ERRORE: Marcatori non trovati nel template {file_target}.", set()

    all_exercises_text = ""
    used_images = {} # Usiamo un dizionario {filename: url}
    # img_pattern = r'\\includegraphics(?:\[.*?\])?\{(.*?)\}'
    mappa_livelli = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}

    # 4. CICLO ESERCIZI (Logica v0.2 intatta)
    for i_es, es in enumerate(data['esercizi']):
        if fila == "A": current_logic = "A"
        elif fila == "B": current_logic = "B"
        elif fila == "C": current_logic = "A" if i_es % 2 == 0 else "B"
        elif fila == "D": current_logic = "B" if i_es % 2 == 0 else "A"

        eid = es['id_es']
        vars_text = ""
        
        for v_idx, var in enumerate(es['tipologia']):
            df_filtered = df_full[
                (df_full['disciplina'] == data['disciplina']) &
                (df_full['tipo'] == var['tipo']) &
                (df_full['argomento'] == var['argomento']) &
                (df_full['subargomento'] == var['subargomento']) &
                (df_full['livello'] == int(var['livello']))
            ]
            
            if not df_filtered.empty:
                # Gestione indici preview e varianti fila B
                s_key = f"nav_{eid}_{v_idx}"
                base_idx = st.session_state.preview_indices.get(s_key, 0)
                actual_idx = base_idx + 1 if (current_logic == "B" and len(df_filtered) > 1) else base_idx
                row = df_filtered.iloc[actual_idx % len(df_filtered)]

                livello_num = int(var['livello'])
                stringa_asterisco = "*" if (data.get('asterisco', False) and livello_num == 1) else ""

                # Raccolta immagini
                # st.write(f"DEBUG: Controllo riga es {eid}, colonna IMMAGINE: {row.get('immagine')}")
                valore_cella = row.get('immagine', "")
                if pd.notna(valore_cella) and valore_cella != "":
                    url, filename = parse_image_field(valore_cella)
                    if url and filename:
                        used_images[filename] = url

                # --- SOSTITUZIONE NEL BLOCCO VARIANTE (SECTPL) ---
                v_out = var_block_tmpl.replace("[[LIVELLO]]", f"[{mappa_livelli.get(livello_num, 'A')}]")
                v_out = v_out.replace("[[ASTERISCO]]", stringa_asterisco)
                v_out = v_out.replace("[[COMANDO]]", str(row['comando']).replace('\\n', '\n'))
                v_out = v_out.replace("[[TESTO_ESERCIZIO]]", str(row['esercizio']).replace('\\n', '\n'))
                v_out = v_out.replace("[[PUNTI]]", str(var['punti']))
                
                # Se è il correttore, aggiungiamo la soluzione
                if is_correttore:
                    col_sol = next((c for c in df_filtered.columns if 'soluzione' in c), None)
                    sol_val = str(row[col_sol]).replace('\\n', '\n') if col_sol and pd.notna(row[col_sol]) else "N/D"
                    v_out = v_out.replace("[[SOLUZIONE]]", sol_val)
                    if col_sol:
                        valore_cella = row.get('immagine', "")
                        if pd.notna(valore_cella) and valore_cella != "":
                            url, filename = parse_image_field(valore_cella)
                            if url and filename:
                                used_images[filename] = url                  
                
                vars_text += v_out

        # Ricomposizione blocco esercizio (SECESR)
        all_exercises_text += ex_block_tmpl.replace(var_match.group(0), vars_text)

    # Inserimento finale nel corpo del documento
    final_output = final_tex.replace(ex_match.group(0), all_exercises_text)
    
    return final_output, used_images
    
# --- GESTIONE STATO INIZIALE ---
if 'db_esercizi' not in st.session_state:
    st.session_state.db_esercizi = None

if 'app_mode' not in st.session_state:
    st.session_state.app_mode = "START" 

if 'data' not in st.session_state:
    st.session_state.data = None

if 'preview_indices' not in st.session_state:
    st.session_state.preview_indices = {}

# --- SCHERMATA DI AVVIO ---
if st.session_state.app_mode == "START":
    st.title("📂 Benvenuto nel Configuratore Verifiche")
    st.markdown("Scegli come vuoi iniziare a lavorare:")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("🆕 Inizia da Zero")
            if st.session_state.db_esercizi is not None:
                lista_disc_start = sorted(st.session_state.db_esercizi['disciplina'].unique().tolist())
                choosen_disc = st.selectbox("Seleziona la Disciplina", lista_disc_start)
            
            if st.button("🚀 Crea Nuovo", use_container_width=True):
                st.session_state.data = {
                    "disciplina": choosen_disc, "idver": "11", "classe": 1,
                    "idtemplate": 1, "asterisco": True, "esercizi": []
                }
                st.session_state.app_mode = "ACTIVE"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("📂 Carica Modello")
            uploaded_file = st.file_uploader("Seleziona file JSON", type="json")
            if uploaded_file is not None:
                if st.button("📥 Importa e Inizia", use_container_width=True):
                    try:
                        new_data = json.load(uploaded_file)
                        for idx, es in enumerate(new_data.get('esercizi', [])):
                            eid = es.get('id_es', f"ex_{int(time.time())}_{idx}")
                            es['id_es'] = eid
                            # DEFAULT: Tutti chiusi al caricamento
                            st.session_state[f"exp_{eid}"] = False
                        st.session_state.data = new_data
                        st.session_state.app_mode = "ACTIVE"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nel caricamento: {e}")

# --- INTERFACCIA DI LAVORO ATTIVA ---
elif st.session_state.app_mode == "ACTIVE":
    data = st.session_state.data

    # --- SIDEBAR: CONTROLLI VISUALIZZAZIONE ---
    st.sidebar.title("🛠️ Opzioni")
    st.sidebar.subheader("👁️ Visualizzazione")
    
    col_exp, col_col = st.sidebar.columns(2)
    if col_exp.button("↔️ Expand All", use_container_width=True):
        for es in data['esercizi']:
            st.session_state[f"exp_{es['id_es']}"] = True
        st.rerun()
    
    if col_col.button("↕️ Collapse All", use_container_width=True):
        for es in data['esercizi']:
            st.session_state[f"exp_{es['id_es']}"] = False
        st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("🔄 Reset Totale", type="secondary", use_container_width=True):
        # 1. Pulisce la cache di Streamlit (forza il ricaricamento di Sheets e Drive)
        st.cache_data.clear()
        
        # 2. Pulisce le variabili di stato che contengono i dati
        st.session_state.db_esercizi = None
        st.session_state.data = None
        st.session_state.current_latex_zip = None
        st.session_state.current_pdf_zip = None
        st.session_state.latex_ready = False
        st.session_state.pdf_ready = False
        
        # 3. Rimuove le chiavi dinamiche create (expander, indici)
        for key in list(st.session_state.keys()):
            if key.startswith("exp_") or key.startswith("nav_"):
                del st.session_state[key]
        
        # 4. Torna alla modalità iniziale
        st.session_state.app_mode = "START"
        st.rerun()

    st.title("🚀 Configuratore Verifiche")

    if st.session_state.db_esercizi is not None:
        df_full = st.session_state.db_esercizi

        # --- INTESTAZIONE AGGIORNATA ---
        st.header("⚙️ Intestazione")
        with st.container(border=True):
            # Prima riga
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                st.text_input("🎯 Disciplina", value=data.get('disciplina', ""), disabled=True)
                df_disc = df_full[df_full['disciplina'] == data['disciplina']]
            with c2:
                data['istituto'] = st.text_input("🏢 Istituto", data.get('istituto', "IIS Casimiri"), disabled=False)
            with c3: 
                cl_opts = [1, 2, 3, 4, 5]
                data['classe'] = st.selectbox("👥 Classe", cl_opts, index=cl_opts.index(data.get('classe', 1)) if data.get('classe') in cl_opts else 0)
            with c4:
                data['annosc'] = st.text_input("📅 Anno Scolastico", value=data.get('annosc', "2025-26"))
                            
            # Seconda riga
            c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
            with c5:
                data['idver'] = st.text_input("🆔 ID Verifica", data.get('idver', ""))
            with c6:
                tm_opts = [1, 2, 3, 4, 5, 6]
                data['idtemplate'] = st.selectbox("📄 ID Template", tm_opts, index=tm_opts.index(data.get('idtemplate', 1)) if data.get('idtemplate') in tm_opts else 0)
            with c7:
                data['docente'] = st.text_input("🆔 Docente", data.get('docente', ""))
            with c8:
                st.write("") # Spaziatore
                data['asterisco'] = st.checkbox("⭐ Asterisco (DSA)", value=data.get('asterisco', True))

            # Terza riga: Istruzioni
            st.divider()
            data['istruzioni'] = st.text_area(
                "📝 Istruzioni per gli studenti (Placeholder [[ISTRUZIONI]])", 
                value=data.get('istruzioni', ""),
                height=120
            )
        st.divider()

        # --- CORPO ESERCIZI ---
        col_add_up, col_clear = st.columns([0.8, 0.2])
        if col_add_up.button("➕ Aggiungi Nuovo Esercizio", key="add_up"):
            add_new_exercise(data)
        
        if col_clear.button("🗑️ Svuota Tutto", type="primary", use_container_width=True):
            data['esercizi'] = []
            st.rerun()

        indices_to_remove_ex = []

        for i, es_container in enumerate(data.get('esercizi', [])):
            eid = es_container.get('id_es')
            if f"exp_{eid}" not in st.session_state:
                st.session_state[f"exp_{eid}"] = False
            
            titolo_es = f"Esercizio {i+1}"
            if es_container.get('tipologia'):
                arg_preview = es_container['tipologia'][0].get('argomento', '...')
                titolo_es += f" - {arg_preview}"

            # L'expander usa lo stato salvato in session_state[f"exp_{eid}"]
            with st.expander(titolo_es, expanded=st.session_state[f"exp_{eid}"]):
                h1, h2 = st.columns([0.9, 0.1])
                # Nota: rimosso l'aggiornamento manuale dello stato qui per evitare loop infiniti, 
                # Streamlit gestisce l'interazione, i pulsanti Expand All forzano il valore.
                
                if h2.button("🗑️", key=f"del_ex_{eid}"):
                    indices_to_remove_ex.append(i)

                indices_to_remove_lev = []
                for j, variante in enumerate(es_container.get('tipologia', [])):
                    st.markdown(f"**Variante {j+1}**")
                    v1, v2, v3, v4, v5, v6 = st.columns([1, 2, 2, 1, 1, 0.5])
                    with v1:
                        tipi = sorted(df_disc['tipo'].unique().tolist()) if not df_disc.empty else ["A"]
                        variante['tipo'] = st.selectbox("Tipo", tipi, index=tipi.index(variante.get('tipo', 'A')) if variante.get('tipo') in tipi else 0, key=f"t_{eid}_{j}")
                        df_t = df_disc[df_disc['tipo'] == variante['tipo']]
                    with v2:
                        args = sorted(df_t['argomento'].unique().tolist()) if not df_t.empty else []
                        variante['argomento'] = st.selectbox("Argomento", args, index=args.index(variante.get('argomento', '')) if variante.get('argomento') in args else 0, key=f"a_{eid}_{j}")
                        df_a = df_t[df_t['argomento'] == variante['argomento']]
                    with v3:
                        subs = sorted(df_a['subargomento'].unique().tolist()) if not df_a.empty else []
                        variante['subargomento'] = st.selectbox("Subargomento", subs, index=subs.index(variante.get('subargomento', '')) if variante.get('subargomento') in subs else 0, key=f"s_{eid}_{j}")
                        df_s = df_a[df_a['subargomento'] == variante['subargomento']]
                    with v4:
                        livs = sorted(df_s['livello'].unique().tolist()) if not df_s.empty else []
                        variante['livello'] = st.selectbox("Livello", livs, index=livs.index(variante.get('livello', 1)) if variante.get('livello') in livs else 0, key=f"l_{eid}_{j}")
                        df_finale = df_s[df_s['livello'] == variante['livello']]
                        st.caption(f"📦 Disp: {len(df_finale)}")
                    with v5: 
                        variante['punti'] = st.text_input("Punti", value=variante.get('punti', "1"), key=f"p_{eid}_{j}")
                    with v6:
                        if st.button("❌", key=f"dlv_{eid}_{j}"): 
                            indices_to_remove_lev.append(j)

                    if not df_finale.empty:
                        state_key = f"nav_{eid}_{j}"
                        if state_key not in st.session_state.preview_indices: 
                            st.session_state.preview_indices[state_key] = 0
                        
                        row = df_finale.iloc[st.session_state.preview_indices[state_key] % len(df_finale)]
                        with st.expander("👁️ Visualizza Anteprima", expanded=False):
                            p1, p2, p3 = st.columns([0.1, 0.8, 0.1])
                            if len(df_finale) > 1:
                                if p1.button("⬅️", key=f"prev_{eid}_{j}"): 
                                    st.session_state.preview_indices[state_key] -= 1
                                    st.rerun()
                                if p3.button("➡️", key=f"next_{eid}_{j}"): 
                                    st.session_state.preview_indices[state_key] += 1
                                    st.rerun()
                            with p2:
                                render_preview(row)

                    st.divider()

                if st.button("✚ Variante", key=f"add_v_{eid}"):
                    if es_container['tipologia']:
                        last_v = es_container['tipologia'][-1]
                        new_v = {k: last_v.get(k, (1 if k=="livello" else ("A" if k=="tipo" else ""))) for k in ["tipo", "argomento", "subargomento", "livello", "punti"]}
                    else: 
                        new_v = {"tipo": "A", "argomento": "", "subargomento": "", "livello": 1, "punti": "1"}
                    es_container['tipologia'].append(new_v)
                    st.rerun()

                for idx in sorted(indices_to_remove_lev, reverse=True): 
                    es_container['tipologia'].pop(idx)
                    st.rerun()

        for idx in sorted(indices_to_remove_ex, reverse=True): 
            eid_rem = data['esercizi'][idx].get('id_es')
            if f"exp_{eid_rem}" in st.session_state: 
                del st.session_state[f"exp_{eid_rem}"]
            data['esercizi'].pop(idx)
            st.rerun()

        if st.button("➕ Aggiungi Nuovo Esercizio", key="add_down"):
            add_new_exercise(data)

        # --- EXPORT E SALVATAGGIO VERSIONE 6 (DEFINITIVA) ---
        st.divider()
        st.subheader("📦 Esportazione e Salvataggio")

        # Prepariamo i nomi file standard basati sui dati della verifica
        id_v = data.get('idver', '11')
        cl = data.get('classe', '1')
        disc = data.get('disciplina', 'Materia').replace(" ", "_").lower()
        base_name = f"{disc}_{cl}_{id_v}"

        # 1. SALVATAGGIO PROGETTO (JSON) - Sempre visibile
        st.download_button(
            label="💾 SALVA PROGETTO (.json)",
            data=json.dumps(data, indent=4, default=json_serialize_helper),
            file_name=f"progetto_{base_name}.json",
            mime="application/json",
            use_container_width=True,
            help="Scarica questo file per poter ricaricare l'intera configurazione in futuro."
        )

        st.write("") # Spaziatore

        # 2. STEP 1: GENERAZIONE PACCHETTO LATEX (Aggiornato V7) ---
        if st.button("🎁 GENERA PACCHETTO LATEX (VERIFICHE + CORRETTORI)", type="primary", use_container_width=True):
            with st.spinner("Generazione 4 verifiche e 2 correttori in corso..."):
                # 1. Generazione Verifiche
                tutte_immagini = {}
                tex_a, imgs_a = generate_latex_fila(data, df_full, fila="A")
                tutte_immagini.update(imgs_a) # Fondi le immagini della Fila A
                tex_b, imgs_b = generate_latex_fila(data, df_full, fila="B")
                tutte_immagini.update(imgs_b) # Fondi le immagini della Fila B
                tex_c, imgs_c = generate_latex_fila(data, df_full, fila="C")
                tutte_immagini.update(imgs_c) # Fondi le immagini della Fila C
                tex_d, imgs_d = generate_latex_fila(data, df_full, fila="D")
                tutte_immagini.update(imgs_d) # Fondi le immagini della Fila D
                
                # 2. Generazione Correttori (Solo A e B)
                corr_a, imgs_ca = generate_latex_fila(data, df_full, fila="A", is_correttore=True)
                tutte_immagini.update(imgs_ca)
                corr_b, imgs_cb = generate_latex_fila(data, df_full, fila="B", is_correttore=True)
                tutte_immagini.update(imgs_cb)
                
                # Unione immagini
                # tutte_immagini = imgs_a | imgs_b | imgs_c | imgs_d | imgs_ca | imgs_cb
                
                # st.write("tutte_immagini:")
                # st.write(tutte_immagini)
                time.sleep(10)

                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Scrittura Verifiche
                    for let, content in zip(["A", "B", "C", "D"], [tex_a, tex_b, tex_c, tex_d]):
                        zf.writestr(f"verifica_{base_name}_FILA_{let}.tex", content)
                    
                    # Scrittura Correttori
                    zf.writestr(f"correttore_{base_name}_FILA_A.tex", corr_a)
                    zf.writestr(f"correttore_{base_name}_FILA_B.tex", corr_b)
                    
                    # Scrittura Immagini
                    for filename, url in tutte_immagini.items():
                        img_bytes = download_image_from_url(url)
                        if img_bytes:
                            zf.writestr(f"images/{filename}", img_bytes)
                        else:
                            st.warning(f"Immagine {filename} non scaricata: compilazione incompleta.")
            
                st.session_state.current_latex_zip = zip_buf.getvalue()
                st.session_state.current_base_name = base_name
                st.session_state.latex_ready = True
                st.session_state.pdf_ready = False
                st.rerun()

        # 3. STEP 2: SCARICA LATEX O GENERA PDF (Visibili solo dopo lo Step 1)
        if st.session_state.get('latex_ready'):
            st.info("✅ Pacchetto sorgente pronto!")
            c1, c2 = st.columns(2)
            
            with c1:
                st.download_button(
                    "💾 SCARICA LATEX (.zip)", 
                    st.session_state.current_latex_zip, 
                    f"sorgenti_{st.session_state.current_base_name}.zip", 
                    "application/zip",
                    use_container_width=True
                )
            
            with c2:
                if st.button("🚀 GENERA PDF (Online)", type="secondary", use_container_width=True):
                    import threading
                    API_URL = "https://xfrancgh-compiletex.hf.space/compile-multiple"
                    TIMEOUT_MAX = 180
                    
                    # ESTRAZIONE DATI
                    zip_data = st.session_state.current_latex_zip
                    b_name = st.session_state.current_base_name
                    
                    # RECUPERO TOKEN
                    # Se sei in locale, Streamlit cerca in .streamlit/secrets.toml
                    hf_token = st.secrets.get("HF_TOKEN", "")
                    #st.write(st.secrets.to_dict())
                    
                    # DEBUG: Vediamo se il token viene letto (mostriamo solo i primi 4 caratteri per sicurezza)
                    # if not hf_token:
                    #     st.error("⚠️ Attenzione: HF_TOKEN non trovato nei secrets!")
                    # else:
                    #     st.write(f"DEBUG: Token caricato (inizia con: {hf_token[:5]}...)")
                    
                    prog_bar = st.progress(0)
                    status_msg = st.empty()
                    response_container = {"data": None, "error": None, "done": False}

                    def call_api(payload, filename, token):
                        try:
                            # MODIFICA 1: Usiamo l'header x-api-key come nel tuo test funzionante
                            headers = {"x-api-key": token}
                            
                            # MODIFICA 2: Usiamo la chiave "file" al singolare
                            files = {"file": (f"{filename}.zip", payload, "application/zip")}
                            
                            # Eseguiamo la POST all'URL di Hugging Face
                            res = requests.post(
                                API_URL, 
                                files=files, 
                                headers=headers, 
                                timeout=TIMEOUT_MAX
                            )
                            
                            if res.status_code != 200:
                                # Catturiamo l'errore per il debug
                                response_container["error"] = f"Errore {res.status_code}: {res.text}"
                            else:
                                response_container["data"] = res
                        except Exception as e:
                            response_container["error"] = str(e)
                        finally:
                            response_container["done"] = True

                    # Passiamo il token come argomento
                    api_thread = threading.Thread(target=call_api, args=(zip_data, b_name, hf_token))
                    api_thread.start()

                    # --- CICLO DI AVANZAMENTO ---
                    start_time = time.time()
                    while not response_container["done"]:
                        # Se il thread ha registrato un errore, usciamo subito dal loop
                        if response_container["error"]:
                            break
                            
                        elapsed = time.time() - start_time
                        percent = min(int((elapsed / TIMEOUT_MAX) * 100), 99)
                        prog_bar.progress(percent)
                        status_msg.info(f"⏳ Compilazione in corso... ({percent}%)")
                        time.sleep(1)
                        if elapsed > TIMEOUT_MAX: 
                            response_container["error"] = "Timeout della richiesta"
                            break

                    # --- GESTIONE RISULTATO ---
                    if response_container["error"]:
                        prog_bar.empty()
                        status_msg.error(f"⚠️ {response_container['error']}")
                    elif response_container["done"] and response_container["data"]:
                        res = response_container["data"]
                        prog_bar.progress(100)
                        status_msg.success("🚀 PDF generati!")
                        st.session_state.current_pdf_zip = res.content
                        st.session_state.pdf_ready = True
                        time.sleep(1)
                        st.rerun()
                        
        # 4. STEP 3: DOWNLOAD FINALE PDF (Visibile solo dopo lo Step 2)
        if st.session_state.get('pdf_ready'):
            st.success("✨ PDF compilati con successo!")
            st.download_button(
                label="📥 SCARICA PDF (.zip)",
                data=st.session_state.current_pdf_zip,
                file_name=f"verifiche_{st.session_state.current_base_name}_PDF.zip",
                mime="application/zip",
                use_container_width=True
            )
