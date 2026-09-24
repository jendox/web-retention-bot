"""SQLAdmin ops panel (optional, gated by ADMIN__ENABLED)."""

from app.admin.setup import ADMIN_BASE_URL, mount_admin

__all__ = ["ADMIN_BASE_URL", "mount_admin"]
