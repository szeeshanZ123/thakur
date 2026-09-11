"""
FastAPI Dependencies package for Captain's Treasure Ledger.
"""

from backend.dependencies.auth import (
    security_scheme,
    get_current_user,
    get_current_active_user,
    require_role,
    require_admin,
    require_captain,
    require_crew_or_above,
    require_financial_access,
)

__all__ = [
    "security_scheme",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_admin",
    "require_captain",
    "require_crew_or_above",
    "require_financial_access",
]
