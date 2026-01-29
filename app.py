import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import plotly.graph_objects as go
from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- CONFIGURATION FICHIERS ---
DB_FILE = "stocks_db.csv"
LOG_FILE = "historique_commandes.csv"

# --- SYSTÈME DE SÉCURITÉ ---
def check_password():
    """Retourne True si l'utilisateur a saisi le bon mot de passe."""
    def password_entered():
        if st.session_state["password"] == "Moana2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("""
            <div style='text-align: center; padding: 50px;'>
                <h1 style='color: #00ffcc;'>🔐 MOANA SECURITY</h1>
                <p style='color: #888;'>Veuillez entrer le code d'accès pour déverrouiller le Command Center.</p>
            </div>
        """, unsafe_allow_html=True)
        st.text_input("Code d'accès", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.error("🔒 Code incorrect. Accès refusé.")
        st.text_input("Réessayez le code", type="password", on_change=password_entered, key="password")
        return False
    else:
        return True

# --- FONCTIONS DE PERSISTANCE & LOGS ---
def charger_stocks_locaux(produits):
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, index_col=0)
            return df['stock'].to_dict()
        except:
            return {p: 300 for p in produits}
    return {p: 300 for p in produits}

def sauvegarder_stock(produit, quantite):
    stocks = charger_stocks_locaux([])
    stocks[produit] = quantite
    pd.DataFrame.from_dict(stocks, orient='index', columns=['stock']).to_csv(DB_FILE)

def log_commande(produit, quantite):
    """Inscrit la commande dans le journal de bord."""
    nouveau_log = pd.DataFrame([{
        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Produit": produit,
        "Quantité": int(quantite),
        "Statut": "Bon Généré"
    }])
    if os.path.exists(LOG_FILE):
        nouveau_log.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else:
        nouveau_log.to_csv(LOG_FILE, index=False)

# --- LANCEMENT DE L'APPLICATION ---
if check_password():

    st.set_page_config(page_title="MOANA LOGISTICS - COMMAND CENTER", layout="wide", page_icon="🌊")

    # --- DESIGN CSS ---
    st.markdown("""
        <style>
        .main { background: linear-gradient(180deg, #0e1117 0%, #1e2130 100%); color: white; }
        .stMetric { background-color: rgba(30, 33, 48, 0.7); padding: 20px; border-radius: 15px; border: 1px solid rgba(0, 255, 204, 0.3); }
        h1 { color: #00ffcc; font-family: 'Helvetica Neue', sans-serif; letter-spacing: 2px; text-transform: uppercase; }
        .stButton>button { background: linear-gradient(90deg, #00ffcc 0%, #0099ff 100%); color: black; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

    # --- FONCTIONS CŒUR ---
    def get_tahiti_weather():
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=-17.53&longitude=-149.56&current_weather=true"
            response = requests.get(url, timeout=5).json()
            return 1 if response['current_weather']['weathercode'] >= 51 else 0
        except: return 0

    def generer_pdf(produit, quantite, delai):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "BON DE COMMANDE AUTOMATISE MOANA", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.cell(200, 10, f"Produit : {produit}", ln=True)
        pdf.cell(200, 10, f"Quantite : {int(quantite)} unites", ln=True)
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(200, 10, "Document certifie par le systeme Moana AI.", ln=True)
        
        # Action de Log
        log_commande(produit, quantite)
        return pdf.output(dest='S').encode('latin-1')

    def engine_ia_pro(data, horizon, weather, event, calendar_impact):
        df_train = data.copy()
        df_train['lag_1'] = df_train['ventes'].shift(1).fillna(df_train['ventes'].mean())
        X = df_train[['jour', 'meteo', 'evenement', 'lag_1', 'impact_attendu']].values
        y = df_train['ventes'].values
        model = GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=6)
        model.fit(X, y)
        last_sales, preds, current_day = y[-1], [], df_train['jour'].max()
        for i in range(horizon):
            current_day += 1
            p = model.predict([[current_day, weather, event, last_sales, calendar_impact]])[0]
            preds.append(max(0, p))
            last_sales = p 
        return preds

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h1 style='color: #00ffcc;'>MOANA 🚢</h1>", unsafe_allow_html=True)
        with st.expander("⚙️ PARAMÈTRES RÉSEAU", expanded=True):
            lead_time = st.number_input("Délai Livraison (Jours)", value=10)
            retard_bateau = st.slider("Retard Bateau", 0, 15, 0)
            service_level = st.select_slider("Taux de Service", options=[0.80, 0.90, 0.95, 0.99], value=0.95)
        
        uploaded_file = st.file_uploader("📂 Charger Ventes", type=['csv', 'xlsx'])
        
        if st.button("🚪 Se déconnecter"):
            del st.session_state["password_correct"]
            st.rerun()

    # --- GESTION DES DONNÉES ---
    produits_catalogue = ['Riz Parfumé 5kg', 'Farine T45', 'Sucre Blanc 1kg']
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.xlsx'):
            data = pd.read_excel(uploaded_file)
        else:
            data = pd.read_csv(uploaded_file, sep=None, engine='python')
        # Mapping automatique
        for col in data.columns:
            if col.lower() in ['ventes', 'qty']: data = data.rename(columns={col: 'ventes'})
            if col.lower() in ['produit', 'item']: data = data.rename(columns={col: 'produit'})
            if col.lower() in ['jour', 'date']: data = data.rename(columns={col: 'jour'})
        produits_catalogue = data['produit'].unique().tolist()
    else:
        all_data = []
        for prod in produits_catalogue:
            p_data = pd.DataFrame({'jour': range(1, 31), 'ventes': np.random.randint(40, 100, 30), 'meteo': [0]*30, 'evenement': [0]*30, 'impact_attendu': [1.0]*30, 'produit': [prod]*30})
            all_data.append(p_data)
        data = pd.concat(all_data)

    if 'stocks_moana' not in st.session_state:
        st.session_state['stocks_moana'] = charger_stocks_locaux(produits_catalogue)

    # --- NAVIGATION PAR ONGLETS ---
    tab_command, tab_history = st.tabs(["🚀 COMMAND CENTER", "📜 JOURNAL DE BORD"])

    with tab_command:
        st.title("🌊 MOANA COMMAND CENTER")
        
        # Radar
        delai_total = lead_time + retard_bateau
        
        choix_produit = st.selectbox("🔍 Sélectionner une référence", produits_catalogue)
        df_p = data[data['produit'] == choix_produit].copy()

        # Persistance du Stock
        val_init = int(st.session_state['stocks_moana'].get(choix_produit, 300))
        stock_physique = st.number_input(f"Stock Réel : {choix_produit}", value=val_init)
        if stock_physique != val_init:
            st.session_state['stocks_moana'][choix_produit] = stock_physique
            sauvegarder_stock(choix_produit, stock_physique)
            st.toast("Stock sauvegardé !", icon="💾")

        # Calcul IA
        with st.spinner('IA en cours...'):
            preds = engine_ia_pro(df_p, 21, get_tahiti_weather(), 0, 1.0)
        
        reorder_point = sum(preds[:delai_total]) + (df_p['ventes'].std() * 1.96 * np.sqrt(delai_total))

        c1, c2, c3 = st.columns(3)
        c1.metric("POINT D'ALERTE", f"{int(reorder_point)} u.")
        c2.metric("PRÉVISION ({}) J".format(delai_total), f"{int(sum(preds[:delai_total]))} u.")
        
        if stock_physique < reorder_point:
            qte = int(reorder_point - stock_physique)
            c3.error(f"🚨 CMD : {qte}")
            st.download_button("📥 Générer & Logger le Bon", generer_pdf(choix_produit, qte, delai_total), f"Moana_{choix_produit}.pdf")
        else:
            c3.success("✅ STOCK OK")

        # Graphique
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_p['jour'], y=df_p['ventes'], name="Historique", line=dict(color='#00ffcc', width=3)))
        fig.add_trace(go.Scatter(x=list(range(31, 46)), y=preds[:15], name="Futur IA", line=dict(dash='dot', color='#ff0066', width=3)))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with tab_history:
        st.subheader("📋 Historique des Commandes")
        if os.path.exists(LOG_FILE):
            df_log = pd.read_csv(LOG_FILE)
            st.dataframe(df_log.sort_index(ascending=False), use_container_width=True)
            if st.button("🗑️ Effacer l'historique"):
                os.remove(LOG_FILE)
                st.rerun()
        else:
            st.info("Aucune commande dans le journal pour le moment.")

    st.divider()
    st.caption("© 2026 Moana Logistics | V3.2 The Beast Edition | tomolostboard-sys")