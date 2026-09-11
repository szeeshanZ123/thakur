"""
API Routers package for Captain's Treasure Ledger.
"""

from backend.routers.ranks import router as ranks_router
from backend.routers.crew import router as crew_router
from backend.routers.voyages import router as voyages_router
from backend.routers.expenses import router as expenses_router
from backend.routers.transactions import router as transactions_router
from backend.routers.payouts import router as payouts_router
from backend.routers.analytics import router as analytics_router
from backend.routers.exports import router as exports_router

__all__ = [
    "ranks_router",
    "crew_router",
    "voyages_router",
    "expenses_router",
    "transactions_router",
    "payouts_router",
    "analytics_router",
    "exports_router",
]
