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

# Injection CSS Avancée (Look Dark Mode & Glassmorphism)
st.markdown("""
    <style>
    .main {
        background: linear-gradient(180deg, #0e1117 0%, #1e2130 100%);
        color: white;
    }
    .stMetric {
        background-color: rgba(30, 33, 48, 0.7);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(0, 255, 204, 0.3);
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    h1 {
        color: #00ffcc;
        font-family: 'Helvetica Neue', sans-serif;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .stButton>button {
        background: linear-gradient(90deg, #00ffcc 0%, #0099ff 100%);
        color: black;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px #00ffcc;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION MÉTÉO RÉELLE ---
def get_tahiti_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-17.53&longitude=-149.56&current_weather=true"
        response = requests.get(url, timeout=5).json()
        code = response['current_weather']['weathercode']
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
    pdf.cell(200, 10, f"Date : {pd.Timestamp.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, f"Produit : {produit}", ln=True)
    pdf.cell(200, 10, f"Quantite : {int(quantite)} unites", ln=True)
    pdf.cell(200, 10, f"Lead Time Total : {delai} jours", ln=True)
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, "Document genere par l'intelligence artificielle Moana Logistics.", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- MOTEUR IA ---
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

# --- HEADER ---
st.title("🌊 MOANA COMMAND CENTER")
st.write(f"🌐 **Logistics Intelligence System** | Polynésie Française")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.pngall.com/wp-content/uploads/2/Ship-PNG-Clipart.png", width=100) # Image d'appoint
    st.header("🎛️ PILOTAGE")
    lead_time = st.number_input("Délai Livraison (Jours)", value=10)
    retard_bateau = st.slider("Retard Bateau (Jours)", 0, 15, 0)
    service_level = st.select_slider("Taux de Service", options=[0.80, 0.90, 0.95, 0.99], value=0.95)
    
    st.divider()
    st.header("🌦️ EXTERNE")
    flux_direct = st.checkbox("Météo Direct (Papeete)", value=True)
    sim_event = st.checkbox("Campagne Promo", value=False)

# Données simulées
data = pd.DataFrame({
    'jour': range(1, 31),
    'ventes': [np.random.randint(40, 100) + (i*1.1) for i in range(30)],
    'meteo': [np.random.choice([0, 1]) for _ in range(30)],
    'evenement': [0]*29 + [1 if sim_event else 0],
    'impact_attendu': [1.5 if sim_event else 1.0]*30,
    'produit': ['Riz Parfumé 5kg']
})

# --- ANALYSE ---
for p in data['produit'].unique():
    df_p = data[data['produit'] == p]
    
    # Calculs Logistiques
    meteo_active = get_tahiti_weather() if flux_direct else 0
    delai_total = lead_time + retard_bateau
    preds = engine_ia_pro(df_p, 21, meteo_active, 1 if sim_event else 0, 1.5 if sim_event else 1.0)
    
    total_pred = sum(preds[:delai_total])
    std_dev = np.std(df_p['ventes'])
    z_score = {0.80: 1.28, 0.90: 1.64, 0.95: 1.96, 0.99: 2.33}[service_level]
    safety_stock = z_score * std_dev * np.sqrt(delai_total)
    reorder_point = total_pred + safety_stock
    
    # Interface de Stock
    st.markdown(f"### 📦 Suivi de Stock : **{p}**")
    stock_actuel = st.number_input("Saisir Stock Physique", value=300, key=f"in_{p}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BESOIN IA (15j)", f"{int(total_pred)} u.")
    c2.metric("SÉCURITÉ", f"{int(safety_stock)} u.")
    c3.metric("POINT D'ALERTE", f"{int(reorder_point)} u.")
    
    if stock_actuel < reorder_point:
        qte_commande = int(reorder_point - stock_actuel)
        c4.error(f"🚨 COMMANDE : {qte_commande}")
        pdf_bytes = generer_pdf(p, qte_commande, delai_total)
        st.download_button(f"📥 Télécharger Bon de Commande", pdf_bytes, f"Moana_{p}.pdf")
    else:
        c4.success("✅ STOCK OK")

    # Graphique futuriste
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_p['jour'], y=df_p['ventes'], name="Ventes Réelles", line=dict(color='#00ffcc', width=4)))
    fig.add_trace(go.Scatter(x=list(range(31, 46)), y=preds[:15], name="Prévision IA", line=dict(dash='dot', color='#ff0066', width=4)))
    fig.update_layout(template="plotly_dark", height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("© 2024 Moana Logistics | Système de Prescription Prédictive | tomolostboard-sys")