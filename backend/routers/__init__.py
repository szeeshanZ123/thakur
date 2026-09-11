"""
API Routers package for Captain's Treasure Ledger.
"""

from backend.routers.ranks import router as ranks_router
from backend.routers.crew import router as crew_router
from backend.routers.voyages import router as voyages_router
from backend.routers.expenses import router as expenses_router
from backend.routers.transactions import router as transactions_router

__all__ = [
    "ranks_router",
    "crew_router",
    "voyages_router",
    "expenses_router",
    "transactions_router",
]
