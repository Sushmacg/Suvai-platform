# Import every model here so Alembic can detect it.
from app.modules.users.models import User  # noqa: F401
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.products.models import Product  # noqa: F401
from app.modules.stalls.models import StallLocation, StallSession  # noqa: F401
from app.modules.inventory.models import SessionStock  # noqa: F401
