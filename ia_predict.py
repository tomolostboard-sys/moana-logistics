import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime
import warnings

# On ignore les messages d'alerte de formatage pour garder un terminal propre
warnings.filterwarnings("ignore", category=UserWarning)

# --- 1. CONFIGURATION DU STOCK ACTUEL ---
# Dans un vrai business, ces données viendraient de ton logiciel de caisse
stocks = {
    'Riz': 300,
    'Farine': 100
}
DELAI_BATEAU = 5  # Nombre de jours avant la prochaine livraison (ex: Taporo)

def envoyer_alerte(produit, manquant):
    """Gère l'affichage, l'envoi d'email simulé et l'archivage de l'alerte"""
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_log = f"[{horodatage}] ALERTE RUPTURE : {produit} - Manque {int(manquant)} unités."
    
    # Affichage dans le terminal
    print(f"  🚨 {message_log}")
    print(f"  📧 Email d'urgence généré automatiquement pour le fournisseur.")
    
    # Sauvegarde dans un fichier d'historique (La mémoire de ton IA)
    with open("historique_alertes.txt", "a", encoding="utf-8") as f:
        f.write(message_log + "\n")

# --- 2. ANALYSE IA MULTI-PRODUITS ---

try:
    df = pd.read_csv('ventes_fenua.csv')
except FileNotFoundError:
    print("Erreur : Le fichier 'ventes_fenua.csv' est introuvable. Vérifie le nom du fichier.")
    exit()

# Liste des produits uniques (Riz, Farine, etc.)
liste_produits = df['produit'].unique()

print(f"--- 🌊 MOANA LOGISTICS : RAPPORT GLOBAL ---")
print(f"Analyse prédictive sur {len(liste_produits)} produits...\n")

for p in liste_produits:
    # Filtrage des données par produit
    df_produit = df[df['produit'] == p]
    
    # Entraînement de l'IA (Tendance des ventes)
    X = df_produit[['jour']]
    y = df_produit['ventes']
    model = LinearRegression()
    model.fit(X.values, y)

    # Prédiction pour les jours restants avant le bateau (Jours 6 à 10)
    jours_futurs = np.array([[6], [7], [8], [9], [10]])
    ventes_predites = model.predict(jours_futurs)
    conso_totale_prevue = sum(ventes_predites)
    
    # Calcul du bilan de stock
    stock_actuel = stocks.get(p, 0)
    bilan_final = stock_actuel - conso_totale_prevue

    print(f"📦 PRODUIT : {p}")
    print(f"   Ventes prévues d'ici le bateau : {int(conso_totale_prevue)} unités")
    
    if bilan_final < 0:
        envoyer_alerte(p, abs(bilan_final))
    else:
        print(f"   ✅ Stock suffisant (Reste estimé : {int(bilan_final)})")
    print("-" * 45)

print("\nAnalyse terminée. L'historique a été mis à jour dans 'historique_alertes.txt'.")