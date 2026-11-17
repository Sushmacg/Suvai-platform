from pathlib import Path

from app.core.config import settings


def media_root() -> Path:
    """Folder for uploaded files. A relative MEDIA_DIR is resolved from the backend folder."""
    root = Path(settings.MEDIA_DIR)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[3] / root
    (root / "products").mkdir(parents=True, exist_ok=True)
    return root