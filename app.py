import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import plotly.graph_objects as go
from fpdf import FPDF
import os
import requests

# --- CONFIGURATION ÉLITE & DESIGN ---
st.set_page_config(page_title="MOANA LOGISTICS - COMMAND CENTER", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00ffcc;
    }
    .main {
        background-color: #0e1117;
    }
    h1 {
        color: #00ffcc;
        text-shadow: 2px 2px #000;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #00ffcc;
        color: black;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION MÉTÉO RÉELLE (Connexion Satellite Papeete) ---
def get_tahiti_weather():
    try:
        # Coordonnées de Papeete
        url = "https://api.open-meteo.com/v1/forecast?latitude=-17.53&longitude=-149.56&current_weather=true"
        response = requests.get(url, timeout=5).json()
        code = response['current_weather']['weathercode']
        # Codes 51+ correspondent à la pluie ou aux orages
        return 1 if code >= 51 else 0
    except:
        return 0

# --- FONCTION GÉNÉRATION PDF ---
def generer_pdf(produit, quantite, delai):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "BON DE COMMANDE AUTOMATISE", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Emetteur : Moana Logistics AI System", ln=True)
    pdf.cell(200, 10, f"Objet : Reapprovisionnement urgent", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, f"Produit : {produit}", ln=True)
    pdf.cell(200, 10, f"Quantite preconisee par l'IA : {int(quantite)} unites", ln=True)
    pdf.cell(200, 10, f"Delai de livraison attendu : {delai} jours", ln=True)
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, "Calcule sur la base des previsions meteo et du calendrier de Polynesie.", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIQUE CORE : LE MOTEUR DE DÉCISION ---
def engine_ia_pro(data, horizon, weather, event, calendar_impact):
    df_train = data.copy()
    df_train['lag_1'] = df_train['ventes'].shift(1).fillna(df_train['ventes'].mean())
    X = df_train[['jour', 'meteo', 'evenement', 'lag_1', 'impact_attendu']].values
    y = df_train['ventes'].values
    model = GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=6)
    model.fit(X, y)
    last_sales = y[-1]
    preds = []
    current_day = df_train['jour'].max()
    for i in range(horizon):
        current_day += 1
        p = model.predict([[current_day, weather, event, last_sales, calendar_impact]])[0]
        preds.append(max(0, p))
        last_sales = p 
    return preds

# --- INTERFACE DE COMMANDEMENT ---
st.title("🛡️ MOANA COMMAND CENTER v1.6")
st.write(f"📍 **Statut :** Opérationnel | **Zone :** Polynésie Française")

with st.sidebar:
    st.header("📥 DATA FEED")
    uploaded_file = st.file_uploader("Importer CSV", type="csv")
    st.divider()
    st.header("🌡️ PARAMÈTRES")
    lead_time = st.number_input("Délai Livraison Normal (Jours)", value=10)
    service_level = st.select_slider("Niveau de Sécurité", options=[0.80, 0.90, 0.95, 0.99], value=0.95)
    
    st.divider()
    st.header("🚢 LOGISTIQUE")
    retard_bateau = st.slider("Retard Transport (Jours)", 0, 20, 0)
    
    st.divider()
    st.header("🌦️ FACTEURS EXTERNES")
    flux_direct = st.checkbox("Activer Flux Météo Direct", value=False)
    sim_meteo = st.checkbox("Simuler Pluie Forte", value=False)
    sim_event = st.checkbox("Événement / Promo", value=False)

# Données par défaut ou Upload
if uploaded_file is None:
    data = pd.DataFrame({
        'jour': range(1, 31),
        'ventes': [np.random.randint(40, 100) + (i*1.2) for i in range(30)],
        'meteo': [np.random.choice([0, 1]) for _ in range(30)],
        'evenement': [0]*29 + [1],
        'impact_attendu': [1.0]*30,
        'produit': ['Riz Parfumé']*30
    })
else:
    data = pd.read_csv(uploaded_file)

# --- ANALYSE ---
for p in data['produit'].unique():
    df_p = data[data['produit'] == p]
    with st.container():
        st.markdown(f"---")
        st.markdown(f"### 📦 Analyse de Stock : {p}")
        
        # Météo : Fusion entre simulateur et flux satellite
        meteo_active = 1 if (sim_meteo or (flux_direct and get_tahiti_weather())) else 0
        
        # Ajustement du délai total (Lead time + Retard)
        delai_total = lead_time + retard_bateau
        
        # Prédiction IA (horizon de 21 jours pour couvrir les retards)
        preds = engine_ia_pro(df_p, 21, meteo_active, 1 if sim_event else 0, 1.5 if sim_event else 1.0)
        total_pred = sum(preds[:delai_total])
        
        # Calcul du Stock de Sécurité ajusté au nouveau délai
        std_dev = np.std(df_p['ventes'])
        z_score = {0.80: 1.28, 0.90: 1.64, 0.95: 1.96, 0.99: 2.33}[service_level]
        safety_stock = z_score * std_dev * np.sqrt(delai_total)
        
        # Point de commande
        reorder_point = total_pred + safety_stock
        
        # Gestion dynamique du stock
        stock_actuel = st.number_input(f"Stock Physique Actuel ({p})", value=350, key=f"stock_{p}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("DEMANDE PRÉVUE", f"{int(total_pred)} un.")
        c2.metric("STOCK SÉCURITÉ", f"{int(safety_stock)} un.")
        c3.metric("POINT DE COMMANDE", f"{int(reorder_point)} un.")
        
        if stock_actuel < reorder_point:
            qte = int(reorder_point - stock_actuel)
            c4.error(f"⚠️ COMMANDE : {qte}")
            
            pdf_bytes = generer_pdf(p, qte, delai_total)
            st.download_button(
                label=f"📄 Générer Bon de Commande - {p}",
                data=pdf_bytes,
                file_name=f"commande_moana_{p}.pdf",
                mime="application/pdf"
            )
        else:
            c4.success("✅ STOCK OPTIMAL")

        # Graphique
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_p['jour'], y=df_p['ventes'], name="Historique", line=dict(color='#00ffcc', width=3)))
        fig.add_trace(go.Scatter(x=list(range(df_p['jour'].max()+1, df_p['jour'].max()+15)), y=preds[:14], name="Prédiction IA", line=dict(dash='dot', color='#ff0066', width=3)))
        
        fig.update_layout(
            template="plotly_dark", 
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("Moana Logistics Engine v1.6 | Algorithme : Gradient Boosting Regressor | Propriété de tomolostboard-sys")