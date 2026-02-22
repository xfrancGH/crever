import streamlit as st
import json
import pandas as pd
import os
import time
import numpy as np # Assicurati di averlo tra gli import
import zipfile
import io

def json_serialize_helper(obj):
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

st.set_page_config(page_title="Configuratore Verifiche", layout="wide")

CSV_FILENAME = os.path.join("CSV", "db_esercizi.csv")
# TEMPLATE_FILENAME = os.path.join("templates", "tver_1.tex")

# --- FUNZIONI DI SUPPORTO ---
def load_local_db():
    if os.path.exists(CSV_FILENAME):
        try:
            df = pd.read_csv(CSV_FILENAME, sep=';')
            df.columns = df.columns.str.lower().str.strip()
            return df
        except Exception as e:
            st.error(f"Errore caricamento CSV: {e}")
            return None
    return None

import re
import os

def render_preview(testo_raw):
    if pd.isna(testo_raw) or testo_raw == "" or str(testo_raw).lower() == "nan": 
        return
    
    testo = str(testo_raw).strip()
    if testo.startswith('"') and testo.endswith('"'): 
        testo = testo[1:-1]
    
    testo = testo.replace('\\n', '\n')
    testo = re.sub(r'\\begin\{center\}|\\end\{center\}', '', testo)

    # --- LOGICA GESTIONE IMMAGINI ---
    # Cerchiamo il pattern \includegraphics[...]{nome_file} o \includegraphics{nome_file}
    # Il pattern identifica il contenuto dentro le ultime parentesi graffe
    pattern_img = r'\\includegraphics(?:\[.*?\])?\{(.*?)\}'
    
    # Dividiamo il testo per processarlo: cerchiamo se ci sono riferimenti a immagini
    parts = re.split(pattern_img, testo)
    
    # Se re.split trova il pattern, le parti dispari della lista saranno i nomi dei file
    # Esempio: ["Testo prima", "nome_immagine", "Testo dopo"]
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Testo normale (renderizziamo LaTeX inline se presente)
            if part.strip():
                st.markdown(part)
        else:
            # È un nome di immagine
            nome_file = part.strip()
            # Proviamo diverse estensioni comuni
            estensioni = ['.png', '.jpg', '.jpeg', '.svg']
            found = False
            
            for est in estensioni:
                path_completo = os.path.join("images", nome_file + est)
                if os.path.exists(path_completo):
                    # Mostriamo l'immagine. 
                    # use_container_width=True la adatta alla colonna dell'anteprima
                    st.image(path_completo, caption=f"Immagine: {nome_file}")
                    found = True
                    break
            
            if not found:
                st.warning(f"⚠️ Immagine non trovata: {nome_file} (controlla la cartella /immagini)")

    # Rimuoviamo eventuali tag LaTeX di posizionamento rimasti (tipo \begin{center}) 
    # che darebbero fastidio alla lettura
    # (Opzionale: puoi aggiungere regex per pulire anche quelli)

def add_new_exercise(data_store):
    unique_id = f"ex_{int(time.time() * 1000)}"
    data_store['esercizi'].append({"id_es": unique_id, "tipologia": []})
    # Quando aggiungi un nuovo esercizio, forziamo la sua apertura
    st.session_state[f"exp_{unique_id}"] = True
    st.rerun()

def generate_latex_fila(data, df_full, fila="A"):
    # Recupera l'idtemplate dal JSON (default a 1 se non presente)
    id_t = data.get('idtemplate', 1)
    
    # Costruisce il percorso: templates/tver_1.tex, templates/tver_2.tex, ecc.
    template_path = os.path.join("templates", f"tver_{id_t}.tex")
    
    if not os.path.exists(template_path):
        return f"ERRORE: Template '{template_path}' non trovato."
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Sostituiamo IDV, MAT e IST
    final_tex = template.replace("IDV", str(data.get('idver', '11')))
    final_tex = final_tex.replace("{MAT}", str(data.get('disciplina', 'Materia')))
    final_tex = final_tex.replace("{IST}", str(data.get('istituto', 'Istituto')))

    try:
        # Estrazione blocchi dal template
        ex_match = re.search(r'%<<SECESR>>(.*?)%<<SECESR>>', final_tex, re.DOTALL)
        ex_block_tmpl = ex_match.group(1)
        var_match = re.search(r'%<<SECTPL>>(.*?)%<<SECTPL>>', ex_block_tmpl, re.DOTALL)
        var_block_tmpl = var_match.group(1)
    except:
        return "ERRORE: Marcatori %<<...>> non trovati nel template."

    all_exercises_text = ""
    used_images = set() # Per raccogliere i nomi delle immagini
    img_pattern = r'\\includegraphics(?:\[.*?\])?\{(.*?)\}'

    for es in data['esercizi']:
        eid = es['id_es']
        vars_text = ""
        for v_idx, var in enumerate(es['tipologia']):
            # Filtro dati
            df_filtered = df_full[
                (df_full['disciplina'] == data['disciplina']) &
                (df_full['tipo'] == var['tipo']) &
                (df_full['argomento'] == var['argomento']) &
                (df_full['subargomento'] == var['subargomento']) &
                (df_full['livello'] == int(var['livello']))
            ]
            
            if not df_filtered.empty:
                # 1. Mappatura Livello Numerico -> Lettera
                mappa_livelli = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
                livello_num = int(var['livello'])
                livello_lettera = mappa_livelli.get(livello_num, "A") # Default A per sicurezza
                
                # 2. Logica Asterisco: solo se livello è 1 (A) e asterisco è attivo nel progetto
                # Se il livello è > 1, l'asterisco non deve mai apparire
                stringa_asterisco = ""
                if data.get('asterisco', False) and livello_num == 1:
                    stringa_asterisco = "*"

                # Recupero l'indice dall'anteprima (navigazione V2)
                s_key = f"nav_{eid}_{v_idx}"
                idx_sel = st.session_state.preview_indices.get(s_key, 0)
                
                # Fila B: prende l'esercizio successivo nel database
                actual_idx = (idx_sel + 1) % len(df_filtered) if fila == "B" and len(df_filtered) > 1 else idx_sel % len(df_filtered)
                
                row = df_filtered.iloc[actual_idx]

                # RACCOLTA IMMAGINI
                used_images.update(re.findall(img_pattern, str(row['comando'])))
                used_images.update(re.findall(img_pattern, str(row['esercizio'])))

                # 3. Sostituzione nel template
                v_out = var_block_tmpl.replace("{LVL}", f"[{livello_lettera}]")
                v_out = v_out.replace("{ASR}", stringa_asterisco)
                v_out = v_out.replace("{CMD}", str(row['comando']).replace('\\n', '\n'))
                v_out = v_out.replace("{ESR}", str(row['esercizio']).replace('\\n', '\n'))
                v_out = v_out.replace("PNT", str(var['punti']))
                vars_text += v_out

        # Inserimento varianti nel blocco esercizio
        ex_out = ex_block_tmpl.replace(var_match.group(0), vars_text)
        all_exercises_text += ex_out

    # Inserimento finale nel template
    return final_tex.replace(ex_match.group(0), all_exercises_text), used_images

# --- GESTIONE STATO INIZIALE ---
if 'db_esercizi' not in st.session_state:
    st.session_state.db_esercizi = load_local_db()

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
        for key in list(st.session_state.keys()):
            if key.startswith("exp_"): del st.session_state[key]
        st.session_state.app_mode = "START"
        st.session_state.data = None
        st.rerun()

    st.title("🚀 Configuratore Verifiche")

    if st.session_state.db_esercizi is not None:
        df_full = st.session_state.db_esercizi

        # --- INTESTAZIONE AGGIORNATA ---
        st.header("⚙️ Intestazione")
        with st.container(border=True):
            # Passiamo a 6 colonne per includere l'Istituto
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            with c1:
                st.text_input("🎯 Disciplina", value=data.get('disciplina', ""), disabled=True)
                df_disc = df_full[df_full['disciplina'] == data['disciplina']]
            with c2:
                # Nuovo campo Istituto
                data['istituto'] = st.text_input("🏢 Istituto", data.get('istituto', "IIS Casimiri"), disabled=True)
            with c3: 
                data['idver'] = st.text_input("ID Verifica", data.get('idver', ""))
            with c4:
                cl_opts = [1, 2, 3, 4, 5]
                data['classe'] = st.selectbox("Classe", cl_opts, index=cl_opts.index(data.get('classe', 1)) if data.get('classe') in cl_opts else 0)
            with c5: 
                data['idtemplate'] = st.number_input("ID Template", value=data.get('idtemplate', 1))
            with c6: 
                data['asterisco'] = st.checkbox("Asterisco (DSA)", value=data.get('asterisco', True))

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
                                render_preview(row['comando'])
                                render_preview(row['esercizio'])
                                col_sol = next((c for c in df_finale.columns if 'soluzione' in c), None)
                                if col_sol and pd.notna(row[col_sol]):
                                    with st.expander("🔎 Vedi Soluzione"): 
                                        render_preview(row[col_sol])
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

        # --- EXPORT FINALE ---
        st.divider()
        st.subheader("📦 Esportazione")
        if st.button("🎁 GENERA PACCHETTO ZIP (CON IMMAGINI)", type="primary", use_container_width=True):
            tex_a, imgs_a = generate_latex_fila(data, df_full, fila="A")
            tex_b, imgs_b = generate_latex_fila(data, df_full, fila="B")
            tutte_immagini = imgs_a.union(imgs_b)
            
            id_v = data.get('idver', '11')
            cl = data.get('classe', '1')
            disc = data.get('disciplina', 'Materia').replace(" ", "_").lower()
            base_name = f"{disc}_{cl}_{id_v}"
            
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                zf.writestr(f"verifica_{base_name}_FILA_A.tex", tex_a)
                zf.writestr(f"verifica_{base_name}_FILA_B.tex", tex_b)
                zf.writestr(f"configurazione_{base_name}.json", json.dumps(data, indent=4, default=json_serialize_helper))
                
                # AGGIUNTA IMMAGINI
                for img_n in tutte_immagini:
                    for est in ['.png', '.jpg', '.jpeg', '.svg']:
                        f_path = os.path.join("images", img_n + est)
                        if os.path.exists(f_path):
                            zf.write(f_path, arcname=os.path.join("images", img_n + est))
                            break
            
            st.success(f"Pacchetto per {data['disciplina']} generato!")
            st.download_button("💾 SCARICA ARCHIVIO ZIP", zip_buf.getvalue(), f"verifica_{base_name}_pack.zip", "application/zip", use_container_width=True)
    else:
        st.error(f"File {CSV_FILENAME} non trovato.")