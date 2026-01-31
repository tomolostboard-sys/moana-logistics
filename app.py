import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingRegressor
import plotly.graph_objects as go
from fpdf import FPDF
import os

# =========================================================
# 🏗️ ARCHITECTURE ERP V6 : MOTEUR HYBRIDE (STOCK + FINANCE)
# =========================================================

class MoanaERP:
    """
    Système ERP complet.
    Gère le stock physique (Logistique) ET la valorisation (Finance).
    """
    def __init__(self, db_name="moana_erp_v6.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._init_structure()

    def _init_structure(self):
        cur = self.conn.cursor()
        
        # 1. Table INVENTAIRE VALORISÉ
        cur.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                sku TEXT PRIMARY KEY,
                nom TEXT,
                stock_reel INTEGER DEFAULT 0,
                cout_achat REAL DEFAULT 0.0,
                prix_vente REAL DEFAULT 0.0,
                fournisseur TEXT DEFAULT 'Inconnu',
                last_update TIMESTAMP
            )
        ''')
        
        # 2. Table JOURNAL FINANCIER
        cur.execute('''
            CREATE TABLE IF NOT EXISTS finance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                sku TEXT,
                action TEXT,
                delta_qty INTEGER,
                impact_financier REAL,
                user TEXT
            )
        ''')
        self.conn.commit()

    def init_demo_data(self):
        """Injecte des données de démonstration corrigées."""
        cur = self.conn.cursor()
        cur.execute("SELECT count(*) FROM inventory")
        if cur.fetchone()[0] == 0:
            # Structure : (sku, nom, stock_reel, cout_achat, prix_vente, fournisseur)
            data = [
                ("RIZ-001", "Riz Parfumé 25kg", 150, 2500.0, 3200.0, "Asian Import Corp"),
                ("FAR-002", "Farine Blé T45", 400, 850.0, 1100.0, "Grands Moulins"),
                ("HUI-003", "Huile Tournesol 1L", 1200, 180.0, 290.0, "Oceana Oil"),
                ("SUC-004", "Sucre Roux 50kg", 80, 4200.0, 5500.0, "Sucrerie Locale")
            ]
            for sku, nom, qte, cout, prix, fourn in data:
                cur.execute("""
                    INSERT INTO inventory (sku, nom, stock_reel, cout_achat, prix_vente, fournisseur, last_update) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sku, nom, qte, cout, prix, fourn, datetime.now()))
            self.conn.commit()

    def get_stock_valorise(self):
        df = pd.read_sql("SELECT * FROM inventory", self.conn)
        df['valeur_totale_stock'] = df['stock_reel'] * df['cout_achat']
        df['marge_unitaire'] = df['prix_vente'] - df['cout_achat']
        df['marge_totale_potentielle'] = df['stock_reel'] * df['marge_unitaire']
        return df

    def transaction_smart(self, sku, new_qty, user="ADMIN"):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT stock_reel, cout_achat FROM inventory WHERE sku = ?", (sku,))
            res = cur.fetchone()
            if not res: return False
            
            old_qty, cout = res
            delta = new_qty - old_qty
            if delta == 0: return True

            impact_cash = delta * cout 
            cur.execute("UPDATE inventory SET stock_reel = ?, last_update = ? WHERE sku = ?", 
                        (new_qty, datetime.now(), sku))
            
            cur.execute("""
                INSERT INTO finance_log (timestamp, sku, action, delta_qty, impact_financier, user)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now(), sku, "CORRECTION_STOCK", delta, impact_cash, user))
            
            self.conn.commit()
            return True
        except:
            self.conn.rollback()
            return False

# Moteur Singleton
erp = MoanaERP()
erp.init_demo_data()

# =========================================================
# 🔐 SÉCURITÉ
# =========================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if not st.session_state["password_correct"]:
        st.markdown("<div style='text-align: center; margin-top: 50px;'><h1 style='color:#00ffcc;'>💎 MOANA ERP V6</h1><p>Industrial & Financial Edition</p></div>", unsafe_allow_html=True)
        pwd = st.text_input("Code Directeur", type="password")
        if pwd == "Moana2026":
            st.session_state["password_correct"] = True
            st.rerun()
        return False
    return True

# =========================================================
# 🧠 IA FINANCIÈRE
# =========================================================
def predict_budget(df_sales, cout_unitaire, horizon=30):
    df = df_sales.copy()
    df['lag'] = df['ventes'].shift(1).fillna(df['ventes'].mean())
    X = df[['jour', 'lag']].values
    y = df['ventes'].values
    
    model = GradientBoostingRegressor(n_estimators=100)
    model.fit(X, y)
    
    future_sales = []
    curr = df['jour'].max()
    last = y[-1]
    
    for _ in range(horizon):
        curr += 1
        pred = model.predict([[curr, last]])[0]
        future_sales.append(max(0, pred))
        last = pred
        
    total_qty = sum(future_sales)
    budget_needed = total_qty * cout_unitaire
    return total_qty, budget_needed, future_sales

def generer_pdf_commande(sku, qty, budget, fournisseur):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 15, "ORDRE D'ACHAT INDUSTRIEL", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Fournisseur : {fournisseur}", ln=True)
    pdf.cell(0, 10, f"Date : {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.line(10, 50, 200, 50)
    pdf.ln(10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(100, 10, "Designation", 1, 0, 'L', 1)
    pdf.cell(40, 10, "Qte", 1, 0, 'C', 1)
    pdf.cell(50, 10, "Montant (XPF)", 1, 1, 'C', 1)
    pdf.cell(100, 10, f"{sku}", 1)
    pdf.cell(40, 10, f"{int(qty)}", 1, 0, 'C')
    pdf.cell(50, 10, f"{budget:,.2f}", 1, 1, 'R')
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"TOTAL A PAYER : {budget:,.2f} XPF", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 🖥️ DASHBOARD
# =========================================================
if check_password():
    st.set_page_config(page_title="MOANA ERP V6", layout="wide")

    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; }
        .metric-card { background: #1f2937; border: 1px solid #374151; padding: 20px; border-radius: 10px; text-align: center; }
        .metric-val { font-size: 24px; font-weight: bold; color: #00ffcc; }
        </style>
    """, unsafe_allow_html=True)

    df_stock = erp.get_stock_valorise()
    
    st.title("🏭 MOANA ERP | Financial Command")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-val'>{df_stock['valeur_totale_stock'].sum():,.0f} XPF</div><div>Valeur Stock</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-val'>{df_stock['marge_totale_potentielle'].sum():,.0f} XPF</div><div>Marge Latente</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_stock)}</div><div>SKUs</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-val'>{len(df_stock[df_stock['stock_reel']<100])}</div><div>Alertes</div></div>", unsafe_allow_html=True)

    tab_gestion, tab_tresorerie, tab_config = st.tabs(["📦 GESTION", "💰 TRÉSORERIE", "⚙️ SYSTEM"])

    with tab_gestion:
        st.dataframe(df_stock[['sku', 'nom', 'fournisseur', 'stock_reel', 'cout_achat', 'valeur_totale_stock']], use_container_width=True)
        st.subheader("⚡ Correction")
        c_sel, c_val, c_btn = st.columns([2, 1, 1])
        sel_prod = c_sel.selectbox("Produit", df_stock['sku'].tolist())
        
        # Récupération sécurisée du stock actuel
        current_val = int(df_stock.loc[df_stock['sku']==sel_prod, 'stock_reel'].values[0])
        new_q = c_val.number_input("Nouveau Stock", value=current_val)
        
        if c_btn.button("Mettre à jour"):
            erp.transaction_smart(sel_prod, new_q)
            st.rerun()

    with tab_tresorerie:
        sku_buy = st.selectbox("Analyse Achat", df_stock['sku'].tolist())
        row = df_stock[df_stock['sku'] == sku_buy].iloc[0]
        sim_sales = pd.DataFrame({'jour': range(1, 61), 'ventes': np.random.randint(5, 25, 60)})
        qty_n, cash_n, forecast = predict_budget(sim_sales, row['cout_achat'])
        
        col1, col2 = st.columns(2)
        col1.metric("Besoin Estimé", f"{int(qty_n)} u.")
        col1.metric("Budget requis", f"{cash_n:,.0f} XPF")
        if col1.button("Générer Bon de Commande"):
            pdf = generer_pdf_commande(sku_buy, qty_n, cash_n, row['fournisseur'])
            st.download_button("Télécharger PDF", pdf, f"PO_{sku_buy}.pdf")
            
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sim_sales['ventes'], name="Historique"))
        # Correction list(range(...)) ici pour Plotly
        fig.add_trace(go.Scatter(x=list(range(60, 90)), y=forecast, name="Prévision", line=dict(dash='dot')))
        fig.update_layout(template="plotly_dark", height=300)
        col2.plotly_chart(fig, use_container_width=True)

    with tab_config:
        if st.button("🔴 Réinitialiser Base de Données"):
            if os.path.exists("moana_erp_v6.db"):
                os.remove("moana_erp_v6.db")
                st.rerun()