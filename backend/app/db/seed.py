from __future__ import annotations

from datetime import datetime
from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.db.models.models_v1 import Site, User
from backend.app.db.models.core_types import Role


def run_seed():
    db = SessionLocal()
    try:
        # 1) Site "Tahiti"
        site = db.scalar(select(Site).where(Site.name == "Tahiti"))
        if not site:
            site = Site(id=1, name="Tahiti", timezone="Pacific/Tahiti", active=True)
            db.add(site)
            db.commit()

        # 2) Admin user (PIN HASH à faire proprement plus tard)
        # Pour l’instant: on stocke le PIN en clair (rude mais efficace pour démarrer).
        # On le remplacera par un hash argon2/bcrypt à l’étape "auth".
        user = db.scalar(select(User).where(User.name == "ADMIN"))
        if not user:
            user = User(
                id=1,
                site_id=site.id,
                name="ADMIN",
                pin_hash="Moana2026",   # TODO: hash
                role=Role.admin,
                active=True,
                created_at=datetime.utcnow(),
            )
            db.add(user)
            db.commit()

        print("SEED OK: site=Tahiti, user=ADMIN")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
