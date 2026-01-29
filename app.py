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

# --- FONCTIONS UTILES ---
def get_tahiti_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-17.53&longitude=-149.56&current_weather=true"
        response = requests.get(url, timeout=5).json()
        code = response['current_weather']['weathercode']
        return 1 if code >= 51 else 0
    except: return 0

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

# --- SIDEBAR & IMPORTATION BLINDÉE ---
with st.sidebar:
    st.image("https://www.pngall.com/wp-content/uploads/2/Ship-PNG-Clipart.png", width=100)
    st.header("🎛️ PILOTAGE GLOBAL")
    lead_time = st.number_input("Délai Livraison (Jours)", value=10)
    retard_bateau = st.slider("Retard Bateau (Jours)", 0, 15, 0)
    service_level = st.select_slider("Taux de Service", options=[0.80, 0.90, 0.95, 0.99], value=0.95)
    
    st.divider()
    st.header("📂 IMPORTATION DONNÉES")
    uploaded_file = st.file_uploader("Charger Ventes (Excel ou CSV)", type=['csv', 'xlsx'])
    
    # Bouton de modèle
    template_data = pd.DataFrame({'jour': [1], 'produit': ['Riz'], 'ventes': [50], 'meteo': [0], 'evenement': [0], 'impact_attendu': [1.0]})
    st.download_button("📥 Modèle CSV", template_data.to_csv(index=False).encode('utf-8'), "modele_moana.csv", "text/csv")
    
    st.divider()
    st.header("🌦️ EXTERNE")
    flux_direct = st.checkbox("Météo Direct (Papeete)", value=True)
    sim_event = st.checkbox("Campagne Promo", value=False)

# --- PRÉPARATION DES DONNÉES ---
produits_catalogue = ['Riz Parfumé 5kg', 'Farine T45', 'Sucre Blanc 1kg']

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.xlsx'):
            excel = pd.ExcelFile(uploaded_file)
            onglet = st.sidebar.selectbox("Choisir l'onglet", excel.sheet_names)
            df_brut = pd.read_excel(uploaded_file, sheet_name=onglet)
        else:
            df_brut = pd.read_csv(uploaded_file, sep=None, engine='python')

        mapping = {'ventes': ['ventes', 'sales', 'qty', 'quantité'], 'produit': ['produit', 'item', 'article'], 'jour': ['jour', 'day', 'date']}
        for officiel, synonymes in mapping.items():
            for col in df_brut.columns:
                if col.lower() in synonymes: df_brut = df_brut.rename(columns={col: officiel})
        
        data = df_brut.dropna(subset=['ventes', 'produit'])
        data['ventes'] = pd.to_numeric(data['ventes'], errors='coerce').fillna(0)
        produits_catalogue = data['produit'].unique().tolist()
    except Exception as e:
        st.sidebar.error(f"Erreur : {e}")
        uploaded_file = None

if uploaded_file is None:
    all_data = []
    for prod in produits_catalogue:
        base = np.random.randint(40, 80)
        p_data = pd.DataFrame({
            'jour': range(1, 31),
            'ventes': [base + np.random.randint(-15, 25) + (i*0.8) for i in range(30)],
            'meteo': [np.random.choice([0, 1]) for _ in range(30)],
            'evenement': [0]*30, 'impact_attendu': [1.0]*30, 'produit': [prod] * 30
        })
        all_data.append(p_data)
    data = pd.concat(all_data)

# --- INTERFACE PRINCIPALE ---
st.title("🌊 MOANA COMMAND CENTER")
st.write(f"🌐 **Logistics Intelligence System** | Polynésie Française")

# --- RADAR GLOBAL ---
st.subheader("📡 RADAR DES STOCKS")
delai_total = lead_time + retard_bateau
etat_stocks = []

for prod in produits_catalogue:
    df_temp = data[data['produit'] == prod].copy()
    vitesse = df_temp['ventes'].tail(7).mean()
    seuil_alerte = (vitesse * delai_total) + (np.std(df_temp['ventes']) * 1.96 * np.sqrt(delai_total))
    s_actuel = st.session_state.get(f"in_{prod}", 300)
    statut = "🔴 COMMANDE" if s_actuel < seuil_alerte else "🟢 OK"
    etat_stocks.append({"Produit": prod, "Stock": int(s_actuel), "Seuil": int(seuil_alerte), "Statut": statut})

st.table(pd.DataFrame(etat_stocks))

# --- ANALYSE DÉTAILLÉE ---
st.divider()
choix_produit = st.selectbox("🔍 ANALYSE PAR RÉFÉRENCE", produits_catalogue)
df_p = data[data['produit'] == choix_produit].copy()

# --- ÉTAPE 13 : DATA GUARD (ANOMALIES) ---
moyenne = df_p['ventes'].mean()
std_dev_p = df_p['ventes'].std()
seuil_max = moyenne + (3 * std_dev_p)
anomalies = df_p[df_p['ventes'] > seuil_max]

if not anomalies.empty:
    st.warning(f"⚠️ **DATA GUARD** : {len(anomalies)} pic(s) de vente détecté(s). L'IA a lissé ces valeurs pour la prévision.")
    df_p.loc[df_p['ventes'] > seuil_max, 'ventes'] = seuil_max

meteo_active = get_tahiti_weather() if flux_direct else 0
preds = engine_ia_pro(df_p, 21, meteo_active, 1 if sim_event else 0, 1.5 if sim_event else 1.0)

total_pred = sum(preds[:delai_total])
safety_stock = np.std(df_p['ventes']) * {0.80: 1.28, 0.90: 1.64, 0.95: 1.96, 0.99: 2.33}[service_level] * np.sqrt(delai_total)
reorder_point = total_pred + safety_stock

st.markdown(f"## 📦 Focus : {choix_produit}")
stock_actuel = st.number_input(f"Stock Physique : {choix_produit}", value=300, key=f"in_{choix_produit}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("BESOIN IA", f"{int(total_pred)} u.")
c2.metric("SÉCURITÉ", f"{int(safety_stock)} u.")
c3.metric("ALERTE", f"{int(reorder_point)} u.")

if stock_actuel < reorder_point:
    qte = int(reorder_point - stock_actuel)
    c4.error(f"🚨 CMD : {qte}")
    st.download_button(f"📥 Bon de Commande", generer_pdf(choix_produit, qte, delai_total), f"Moana_{choix_produit}.pdf")
else:
    c4.success("✅ OK")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_p['jour'], y=df_p['ventes'], name="Réel (Lissé)", line=dict(color='#00ffcc', width=4)))
fig.add_trace(go.Scatter(x=list(range(31, 46)), y=preds[:15], name="IA", line=dict(dash='dot', color='#ff0066', width=4)))
fig.update_layout(template="plotly_dark", height=400)
st.plotly_chart(fig, use_container_width=True)

st.caption("© 2026 Moana Logistics | V2.1 Data Guard Activated | tomolostboard-sys")