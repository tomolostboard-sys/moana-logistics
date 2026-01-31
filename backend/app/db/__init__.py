# Import side-effects so Alembic can "see" models
from backend.app.db.models import core_types  # noqa: F401
from backend.app.db.models import models_v1   # noqa: F401
