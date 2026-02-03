"""
Procurement service.

Ce module orchestre les flux d'achat (PO, réception, etc.)
mais ne contient AUCUNE logique de calcul de stock.

Toute la logique stock est centralisée dans :
    backend.services.inventory
"""

from backend.services.inventory import rebuild_qty_on_order

__all__ = ["rebuild_qty_on_order"]
