import streamlit as st
import json
import pandas as pd
import os
import time

st.set_page_config(page_title="Configuratore Verifiche PRO", layout="wide")

CSV_FILENAME = "db_esercizi.csv"

# --- FUNZIONI DI SUPPORTO ---
def load_local_db():
    if os.path.exists(CSV_FILENAME):
        try:
            df = pd.read_csv(CSV_FILENAME, sep=';')
            df.columns = df.columns.str.lower().str.strip()
            if 'diciplina' in df.columns:
                df = df.rename(columns={'diciplina': 'disciplina'})
            return df
        except Exception as e:
            st.error(f"Errore caricamento CSV: {e}")
            return None
    return None

def render_preview(testo_raw):
    if pd.isna(testo_raw) or testo_raw == "" or str(testo_raw).lower() == "nan": 
        return
    testo = str(testo_raw).strip()
    if testo.startswith('"') and testo.endswith('"'): testo = testo[1:-1]
    
    if "$" in testo:
        parti = testo.split('$')
        for i, parte in enumerate(parti):
            if i % 2 == 1:
                if parte.strip(): st.latex(parte)
            else:
                if parte.strip(): st.markdown(parte.replace('\\n', '\n'))
    elif "\\" in testo:
        st.latex(testo)
    else:
        st.markdown(testo.replace('\\n', '\n'))

def add_new_exercise(data_store):
    unique_id = f"ex_{int(time.time() * 1000)}"
    data_store['esercizi'].append({"id_es": unique_id, "tipologia": []})
    # Quando aggiungi un nuovo esercizio, forziamo la sua apertura
    st.session_state[f"exp_{unique_id}"] = True
    st.rerun()

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
                    "disciplina": choosen_disc, "idver": "NEW_01", "classe": 1,
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
    if col_exp.button("↔️ Expand All"):
        for es in data['esercizi']:
            st.session_state[f"exp_{es['id_es']}"] = True
        st.rerun()
    
    if col_col.button("↕️ Collapse All"):
        for es in data['esercizi']:
            st.session_state[f"exp_{es['id_es']}"] = False
        st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("🔄 Reset Totale"):
        for key in list(st.session_state.keys()):
            if key.startswith("exp_"): del st.session_state[key]
        st.session_state.app_mode = "START"
        st.session_state.data = None
        st.rerun()

    st.title("🚀 Configuratore Verifiche PRO")

    if st.session_state.db_esercizi is not None:
        df_full = st.session_state.db_esercizi

        # --- INTESTAZIONE ---
        st.header("⚙️ Intestazione")
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.text_input("🎯 Disciplina", value=data.get('disciplina', ""), disabled=True)
                df_disc = df_full[df_full['disciplina'] == data['disciplina']]
            with c2: data['idver'] = st.text_input("ID Verifica", data.get('idver', ""))
            with c3:
                cl_opts = [1, 2, 3, 4, 5]
                data['classe'] = st.selectbox("Classe", cl_opts, index=cl_opts.index(data.get('classe', 1)) if data.get('classe') in cl_opts else 0)
            with c4: data['idtemplate'] = st.number_input("ID Template", value=data.get('idtemplate', 1))
            with c5: data['asterisco'] = st.checkbox("Asterisco (DSA)", value=data.get('asterisco', True))

        st.divider()

        # --- CORPO ESERCIZI ---
        col_add_up, col_clear = st.columns([0.8, 0.2])
        if col_add_up.button("➕ Aggiungi Nuovo Esercizio", key="add_up"):
            add_new_exercise(data)
        
        if col_clear.button("🗑️ Svuota Tutto", type="primary"):
            data['esercizi'] = []
            st.rerun()

        indices_to_remove_ex = []

        for i, es_container in enumerate(data.get('esercizi', [])):
            eid = es_container.get('id_es')
            # DEFAULT: Se non esiste ancora uno stato (nuovo caricamento), impostiamo False (chiuso)
            if f"exp_{eid}" not in st.session_state:
                st.session_state[f"exp_{eid}"] = False
            
            titolo_es = f"Esercizio {i+1}"
            if es_container.get('tipologia'):
                titolo_es += f" - {es_container['tipologia'][0].get('argomento', '...')}"

            with st.expander(titolo_es, expanded=st.session_state[f"exp_{eid}"]):
                h1, h2 = st.columns([0.9, 0.1])
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
                    with v5: variante['punti'] = st.text_input("Punti", value=variante.get('punti', "1"), key=f"p_{eid}_{j}")
                    with v6:
                        if st.button("❌", key=f"dlv_{eid}_{j}"): indices_to_remove_lev.append(j)

                    if not df_finale.empty:
                        state_key = f"nav_{eid}_{j}"
                        if state_key not in st.session_state.preview_indices: st.session_state.preview_indices[state_key] = 0
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
                                    with st.expander("🔎 Vedi Soluzione"): render_preview(row[col_sol])
                    st.divider()

                if st.button("✚ Variante", key=f"add_v_{eid}"):
                    if es_container['tipologia']:
                        last_v = es_container['tipologia'][-1]
                        new_v = {k: last_v.get(k, (1 if k=="livello" else ("A" if k=="tipo" else ""))) for k in ["tipo", "argomento", "subargomento", "livello", "punti"]}
                    else: new_v = {"tipo": "A", "argomento": "", "subargomento": "", "livello": 1, "punti": "1"}
                    es_container['tipologia'].append(new_v)
                    st.rerun()

                for idx in sorted(indices_to_remove_lev, reverse=True): 
                    es_container['tipologia'].pop(idx)
                    st.rerun()

        for idx in sorted(indices_to_remove_ex, reverse=True): 
            eid_rem = data['esercizi'][idx].get('id_es')
            if f"exp_{eid_rem}" in st.session_state: del st.session_state[f"exp_{eid_rem}"]
            data['esercizi'].pop(idx)
            st.rerun()

        if st.button("➕ Aggiungi Nuovo Esercizio", key="add_down"):
            add_new_exercise(data)

        # --- EXPORT ---
        st.divider()
        json_export = json.dumps(data, indent=4, ensure_ascii=False)
        st.download_button("📥 SCARICA JSON", data=json_export, file_name="verifica.json")
        with st.expander("🔍 Anteprima JSON"): st.code(json_export, language="json")
    else:
        st.error(f"File {CSV_FILENAME} non trovato.")