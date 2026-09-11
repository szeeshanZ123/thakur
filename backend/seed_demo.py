"""
Demo Data Seeding Utility for Captain's Treasure Ledger.

Populates the database with realistic pirate economics data:
- Ranks with standard integer share weights (100 units = 1.0 share).
- Active and inactive crew members.
- Historical completed voyages with revenue, categorized expenses, and finalized dividends.
- Active in-progress voyage with operational expenses.

Usage:
    python -m backend.seed_demo
"""

import os
import sys
from datetime import datetime

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import SessionLocal, init_db
from backend.models.rank import Rank
from backend.models.crew import CrewMember
from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.payout import Payout
from backend.models.transaction import TransactionLog
from backend.services.financial_service import post_revenue_transaction, create_and_post_expense
from backend.services.payout_service import finalize_voyage_payouts


def seed_demo_data():
    """Seeds realistic demonstration data for development, testing, and presentation."""
    print("==================================================")
    print("CAPTAIN'S TREASURE LEDGER - DEMO DATA SEEDER")
    print("==================================================")

    init_db()
    db = SessionLocal()

    try:
        # Check if demo data already exists
        existing_ranks = db.query(Rank).count()
        if existing_ranks > 0:
            print(f"[*] Found {existing_ranks} existing ranks in database. Checking if full seed is needed...")
            existing_voyages = db.query(Voyage).count()
            if existing_voyages > 0:
                print(f"[!] Database already contains {existing_voyages} voyages. Skipping duplicate seed.")
                print("    (To re-seed, remove data/treasure_ledger.db and run again)")
                return

        print("[1/5] Seeding standard pirate ranks with integer share weights...")
        ranks_data = [
            {"name": "Captain", "share_weight_units": 200, "is_active": True},       # 2.0 shares
            {"name": "Quartermaster", "share_weight_units": 150, "is_active": True}, # 1.5 shares
            {"name": "First Mate", "share_weight_units": 150, "is_active": True},    # 1.5 shares
            {"name": "Gunner", "share_weight_units": 100, "is_active": True},        # 1.0 share
            {"name": "Deckhand", "share_weight_units": 50, "is_active": True},       # 0.5 share
            {"name": "Powder Monkey", "share_weight_units": 25, "is_active": True},  # 0.25 share
        ]

        rank_objects = {}
        for r_info in ranks_data:
            rank = Rank(**r_info)
            db.add(rank)
            db.flush()
            rank_objects[rank.name] = rank
            print(f"     + Rank: {rank.name:15} | Weight: {rank.share_weight_units:3} units ({rank.share_weight_units / 100:.2f}x)")

        print("\n[2/5] Seeding crew roster (active and inactive)...")
        crew_data = [
            {"name": "Edward 'Blackbeard' Teach", "rank_id": rank_objects["Captain"].id, "is_active": True},
            {"name": "Anne Bonny", "rank_id": rank_objects["Quartermaster"].id, "is_active": True},
            {"name": "'Calico Jack' Rackham", "rank_id": rank_objects["First Mate"].id, "is_active": True},
            {"name": "Bartholomew 'Black Bart' Roberts", "rank_id": rank_objects["Gunner"].id, "is_active": True},
            {"name": "Israel Hands", "rank_id": rank_objects["Deckhand"].id, "is_active": True},
            {"name": "Billy Bones", "rank_id": rank_objects["Deckhand"].id, "is_active": False}, # Retired
        ]

        crew_objects = []
        for c_info in crew_data:
            crew = CrewMember(**c_info)
            db.add(crew)
            db.flush()
            crew_objects.append(crew)
            status_label = "ACTIVE" if crew.is_active else "INACTIVE/RETIRED"
            print(f"     + Crew: {crew.name:32} | Rank ID: {crew.rank_id} | Status: {status_label}")

        db.commit()

        print("\n[3/5] Seeding Voyage 1: 'The Spanish Galleon Raid' (Completed & Finalized)...")
        voyage_1 = Voyage(
            name="The Spanish Galleon Raid",
            date=datetime(2026, 8, 15, 12, 0, 0),
            revenue_paise=10000000, # Rs. 100,000.00
            status="completed"
        )
        db.add(voyage_1)
        db.commit()
        db.refresh(voyage_1)

        # Post revenue ledger transaction
        post_revenue_transaction(db, voyage_1.id, voyage_1.revenue_paise)
        print(f"     + Revenue Posted: Rs. {voyage_1.revenue_paise / 100:,.2f} ({voyage_1.revenue_paise} paise)")

        # Add categorized expenses
        v1_expenses = [
            ("Provisions", 1200000, "Salt beef, hardtack, citrus lemons & 20 barrels of Tortuga rum"),
            ("Ammunition", 500000, "Chain shot, 50 kegs of black gunpowder & lead cannonballs"),
            ("Repairs", 300000, "Drydock hull caulking, tar coating & foremast replacement"),
        ]
        for cat, amt, desc in v1_expenses:
            exp, _ = create_and_post_expense(
                db=db,
                voyage_id=voyage_1.id,
                category=cat,
                amount_paise=amt,
                date=datetime(2026, 8, 16, 14, 0, 0),
                description=desc
            )
            print(f"     + Expense: [{cat}] Rs. {amt / 100:,.2f} - {desc[:40]}...")

        # Finalize dividends for Voyage 1
        _, v1_payouts = finalize_voyage_payouts(db, voyage_1.id, user_role="captain")
        v1_total_paid = sum(p.payout_paise for p in v1_payouts)
        print(f"     + Finalized Dividends: {len(v1_payouts)} crew shares distributed | Total = Rs. {v1_total_paid / 100:,.2f}")

        print("\n[4/5] Seeding Voyage 2: 'Isla de Muerta Expedition' (Completed & Finalized)...")
        voyage_2 = Voyage(
            name="Isla de Muerta Expedition",
            date=datetime(2026, 8, 28, 10, 0, 0),
            revenue_paise=6500000, # Rs. 65,000.00
            status="completed"
        )
        db.add(voyage_2)
        db.commit()
        db.refresh(voyage_2)

        post_revenue_transaction(db, voyage_2.id, voyage_2.revenue_paise)
        print(f"     + Revenue Posted: Rs. {voyage_2.revenue_paise / 100:,.2f} ({voyage_2.revenue_paise} paise)")

        v2_expenses = [
            ("Provisions", 800000, "Fresh Caribbean oranges & grog rations"),
            ("Equipment", 700000, "Brass navigational sextants, spyglasses & deep sea anchors"),
        ]
        for cat, amt, desc in v2_expenses:
            exp, _ = create_and_post_expense(
                db=db,
                voyage_id=voyage_2.id,
                category=cat,
                amount_paise=amt,
                date=datetime(2026, 8, 29, 9, 30, 0),
                description=desc
            )
            print(f"     + Expense: [{cat}] Rs. {amt / 100:,.2f} - {desc[:40]}...")

        _, v2_payouts = finalize_voyage_payouts(db, voyage_2.id, user_role="captain")
        v2_total_paid = sum(p.payout_paise for p in v2_payouts)
        print(f"     + Finalized Dividends: {len(v2_payouts)} crew shares distributed | Total = Rs. {v2_total_paid / 100:,.2f}")

        print("\n[5/5] Seeding Voyage 3: 'Siren's Cove Voyage' (In Progress)...")
        voyage_3 = Voyage(
            name="Siren's Cove Voyage",
            date=datetime(2026, 9, 10, 8, 0, 0),
            revenue_paise=0, # Planned/In Progress
            status="in_progress"
        )
        db.add(voyage_3)
        db.commit()
        db.refresh(voyage_3)

        exp3, _ = create_and_post_expense(
            db=db,
            voyage_id=voyage_3.id,
            category="Provisions",
            amount_paise=450000, # Rs. 4,500.00
            date=datetime(2026, 9, 10, 11, 0, 0),
            description="Outfitting expedition: fresh water barrels & medicinal herbs"
        )
        print(f"     + In-Progress Expense: [Provisions] Rs. {exp3.amount_paise / 100:,.2f}")

        # Summary Metrics
        total_tx = db.query(TransactionLog).count()
        total_payouts = db.query(Payout).count()
        total_crew = db.query(CrewMember).count()
        total_active_crew = db.query(CrewMember).filter(CrewMember.is_active == True).count()

        print("\n==================================================")
        print("[SUCCESS] DEMO SEEDING COMPLETED SUCCESSFULLY!")
        print("==================================================")
        print(f"  * Total Ranks:            {len(rank_objects)}")
        print(f"  * Total Crew Members:     {total_crew} ({total_active_crew} active, {total_crew - total_active_crew} retired)")
        print(f"  * Total Voyages:          3 (2 completed & finalized, 1 in-progress)")
        print(f"  * Total Ledger Entries:   {total_tx} immutable transactions")
        print(f"  * Total Finalized Shares: {total_payouts} crew dividend records")
        print("==================================================")

    except Exception as e:
        db.rollback()
        print(f"\n[!] Error during demo data seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
