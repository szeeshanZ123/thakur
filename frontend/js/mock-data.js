const MOCK_RANKS = [
  { id: 1, name: "Captain", share_weight_units: 200, status: "active" },
  { id: 2, name: "First Mate", share_weight_units: 150, status: "active" },
  { id: 3, name: "Quartermaster", share_weight_units: 120, status: "active" },
  { id: 4, name: "Sailing Master", share_weight_units: 110, status: "active" },
  { id: 5, name: "Boatswain", share_weight_units: 100, status: "active" },
  { id: 6, name: "Gunner", share_weight_units: 100, status: "active" },
  { id: 7, name: "Able Seaman", share_weight_units: 100, status: "active" },
  { id: 8, name: "Powder Monkey", share_weight_units: 50, status: "active" }
];

const MOCK_CREW = [
  { id: 1, name: "Captain Blackbeard", rank_id: 1, status: "active", joined_date: "2025-01-15" },
  { id: 2, name: "William Turner", rank_id: 2, status: "active", joined_date: "2025-02-01" },
  { id: 3, name: "Anne Bonny", rank_id: 3, status: "active", joined_date: "2025-02-10" },
  { id: 4, name: "Charles Vane", rank_id: 4, status: "active", joined_date: "2025-03-05" },
  { id: 5, name: "Edward Teach Jr.", rank_id: 5, status: "active", joined_date: "2025-03-20" },
  { id: 6, name: "Calico Jack", rank_id: 6, status: "active", joined_date: "2025-04-01" },
  { id: 7, name: "Israel Hands", rank_id: 7, status: "active", joined_date: "2025-04-15" },
  { id: 8, name: "Stede Bonnet", rank_id: 7, status: "active", joined_date: "2025-05-01" },
  { id: 9, name: "Mary Read", rank_id: 7, status: "active", joined_date: "2025-05-15" },
  { id: 10, name: "Samuel Bellamy", rank_id: 8, status: "active", joined_date: "2025-06-01" },
  { id: 11, name: "Bartholomew Roberts", rank_id: 8, status: "active", joined_date: "2025-06-15" },
  { id: 12, name: "Francis Drake", rank_id: 7, status: "inactive", joined_date: "2025-01-20" }
];

const MOCK_VOYAGES = [
  { id: 1, name: "Golden Reef", date: "2026-07-10", description: "Raided a merchant fleet near the Golden Reef passage", revenue_paise: 15000000, status: "completed" },
  { id: 2, name: "Crimson Cove", date: "2026-07-25", description: "Ambushed colonial transport at Crimson Cove", revenue_paise: 9500000, status: "completed" },
  { id: 3, name: "Serpent's Tooth", date: "2026-08-05", description: "Seized spice trade vessels at Serpent's Tooth strait", revenue_paise: 12000000, status: "completed" },
  { id: 4, name: "Stormbreaker Bay", date: "2026-08-18", description: "Quick raid on fishing fleet during storm cover", revenue_paise: 6500000, status: "completed" },
  { id: 5, name: "Black Sand Shoals", date: "2026-08-30", description: "Major fleet engagement near Black Sand Shoals", revenue_paise: 18000000, status: "completed" },
  { id: 6, name: "Iron Tide Passage", date: "2026-09-05", description: "Patrol and raid through the Iron Tide Passage", revenue_paise: 7200000, status: "completed" },
  { id: 7, name: "Coral Wreck", date: "2026-09-12", description: "Ongoing expedition near Coral Wreck reef system", revenue_paise: 0, status: "ongoing" },
  { id: 8, name: "Devil's Throat", date: "2026-09-25", description: "Planned raid on the heavily guarded Devil's Throat galleons", revenue_paise: 0, status: "planned" }
];

const MOCK_EXPENSES = [
  { id: 1, voyage_id: 1, category: "Ship Repair", amount_paise: 3000000, date: "2026-07-08", description: "Hull repair before Golden Reef voyage" },
  { id: 2, voyage_id: 1, category: "Gunpowder", amount_paise: 2500000, date: "2026-07-09", description: "Gunpowder stock for cannons" },
  { id: 3, voyage_id: 1, category: "Provisions", amount_paise: 1500000, date: "2026-07-09", description: "Food and water for 2 week voyage" },
  { id: 4, voyage_id: 2, category: "Ship Repair", amount_paise: 1200000, date: "2026-07-24", description: "Rigging repair after storm" },
  { id: 5, voyage_id: 2, category: "Gunpowder", amount_paise: 1800000, date: "2026-07-24", description: "Fresh gunpowder supplies" },
  { id: 6, voyage_id: 2, category: "Medical", amount_paise: 800000, date: "2026-07-26", description: "Medical supplies for crew injuries" },
  { id: 7, voyage_id: 3, category: "Ship Repair", amount_paise: 2000000, date: "2026-08-04", description: "Anchor and chain replacement" },
  { id: 8, voyage_id: 3, category: "Gunpowder", amount_paise: 1500000, date: "2026-08-04", description: "Cannonball and powder resupply" },
  { id: 9, voyage_id: 3, category: "Provisions", amount_paise: 1000000, date: "2026-08-04", description: "Fresh provisions and rum" },
  { id: 10, voyage_id: 4, category: "Gunpowder", amount_paise: 900000, date: "2026-08-17", description: "Quick powder reload" },
  { id: 11, voyage_id: 4, category: "Supplies", amount_paise: 400000, date: "2026-08-17", description: "Ropes and tackle" },
  { id: 12, voyage_id: 5, category: "Ship Repair", amount_paise: 4500000, date: "2026-08-29", description: "Major hull and mast repair" },
  { id: 13, voyage_id: 5, category: "Gunpowder", amount_paise: 3000000, date: "2026-08-29", description: "Full gunpowder magazine reload" },
  { id: 14, voyage_id: 5, category: "Provisions", amount_paise: 1500000, date: "2026-08-29", description: "Extended voyage provisions" },
  { id: 15, voyage_id: 5, category: "Other", amount_paise: 500000, date: "2026-08-30", description: "Bribe for harbor pilot" },
  { id: 16, voyage_id: 6, category: "Ship Repair", amount_paise: 800000, date: "2026-09-04", description: "Sail replacement" },
  { id: 17, voyage_id: 6, category: "Gunpowder", amount_paise: 1200000, date: "2026-09-04", description: "Powder charges" },
  { id: 18, voyage_id: 6, category: "Provisions", amount_paise: 700000, date: "2026-09-04", description: "Standard provisions pack" }
];

const MOCK_TRANSACTIONS = [
  { id: 1, voyage_id: 1, crew_id: null, type: "credit", description: "Captured merchant cargo", amount_paise: 15000000, date: "2026-07-10", time: "10:00 AM" },
  { id: 2, voyage_id: 1, crew_id: null, type: "debit", description: "Hull repair", amount_paise: 3000000, date: "2026-07-08", time: "09:15 AM" },
  { id: 3, voyage_id: 1, crew_id: null, type: "debit", description: "Gunpowder stock", amount_paise: 2500000, date: "2026-07-09", time: "08:30 AM" },
  { id: 4, voyage_id: 1, crew_id: null, type: "debit", description: "Provisions", amount_paise: 1500000, date: "2026-07-09", time: "11:00 AM" },
  { id: 5, voyage_id: 1, crew_id: 1, type: "payout", description: "Crew dividend — Captain", amount_paise: 2666666, date: "2026-07-12", time: "02:00 PM" },
  { id: 6, voyage_id: 1, crew_id: 2, type: "payout", description: "Crew dividend — First Mate", amount_paise: 2000000, date: "2026-07-12", time: "02:00 PM" },
  { id: 7, voyage_id: 1, crew_id: 3, type: "payout", description: "Crew dividend — Quartermaster", amount_paise: 1600000, date: "2026-07-12", time: "02:01 PM" },
  { id: 8, voyage_id: 2, crew_id: null, type: "credit", description: "Seized colonial transport", amount_paise: 9500000, date: "2026-07-25", time: "14:30 PM" },
  { id: 9, voyage_id: 2, crew_id: null, type: "debit", description: "Rigging repair", amount_paise: 1200000, date: "2026-07-24", time: "10:00 AM" },
  { id: 10, voyage_id: 2, crew_id: null, type: "debit", description: "Gunpowder supplies", amount_paise: 1800000, date: "2026-07-24", time: "11:30 AM" },
  { id: 11, voyage_id: 2, crew_id: null, type: "debit", description: "Medical supplies", amount_paise: 800000, date: "2026-07-26", time: "09:00 AM" },
  { id: 12, voyage_id: 3, crew_id: null, type: "credit", description: "Spice cargo seized", amount_paise: 12000000, date: "2026-08-05", time: "16:00 PM" },
  { id: 13, voyage_id: 3, crew_id: null, type: "debit", description: "Anchor and chain", amount_paise: 2000000, date: "2026-08-04", time: "08:00 AM" },
  { id: 14, voyage_id: 3, crew_id: null, type: "debit", description: "Cannonball supply", amount_paise: 1500000, date: "2026-08-04", time: "09:30 AM" },
  { id: 15, voyage_id: 3, crew_id: null, type: "debit", description: "Fresh provisions", amount_paise: 1000000, date: "2026-08-04", time: "10:45 AM" },
  { id: 16, voyage_id: 4, crew_id: null, type: "credit", description: "Fishing fleet cargo", amount_paise: 6500000, date: "2026-08-18", time: "11:00 AM" },
  { id: 17, voyage_id: 4, crew_id: null, type: "debit", description: "Powder reload", amount_paise: 900000, date: "2026-08-17", time: "07:00 AM" },
  { id: 18, voyage_id: 4, crew_id: null, type: "debit", description: "Ropes and tackle", amount_paise: 400000, date: "2026-08-17", time: "08:30 AM" },
  { id: 19, voyage_id: 5, crew_id: null, type: "credit", description: "Galleon treasure", amount_paise: 18000000, date: "2026-08-30", time: "15:00 PM" },
  { id: 20, voyage_id: 5, crew_id: null, type: "debit", description: "Hull and mast repair", amount_paise: 4500000, date: "2026-08-29", time: "06:00 AM" },
  { id: 21, voyage_id: 5, crew_id: null, type: "debit", description: "Full magazine reload", amount_paise: 3000000, date: "2026-08-29", time: "08:00 AM" },
  { id: 22, voyage_id: 5, crew_id: null, type: "debit", description: "Extended provisions", amount_paise: 1500000, date: "2026-08-29", time: "10:00 AM" },
  { id: 23, voyage_id: 5, crew_id: null, type: "debit", description: "Harbor pilot bribe", amount_paise: 500000, date: "2026-08-30", time: "12:00 PM" },
  { id: 24, voyage_id: 6, crew_id: null, type: "credit", description: "Patrol route capture", amount_paise: 7200000, date: "2026-09-05", time: "13:00 PM" },
  { id: 25, voyage_id: 6, crew_id: null, type: "debit", description: "Sail replacement", amount_paise: 800000, date: "2026-09-04", time: "07:30 AM" },
  { id: 26, voyage_id: 6, crew_id: null, type: "debit", description: "Powder charges", amount_paise: 1200000, date: "2026-09-04", time: "09:00 AM" },
  { id: 27, voyage_id: 6, crew_id: null, type: "debit", description: "Standard provisions", amount_paise: 700000, date: "2026-09-04", time: "10:30 AM" }
];

const MOCK_PAYOUTS = [
  { id: 1,  voyage_id: 1, crew_id: 1,  share_weight_units: 200, payout_paise: 2666666, status: "paid", date: "2026-07-12" },
  { id: 2,  voyage_id: 1, crew_id: 2,  share_weight_units: 150, payout_paise: 2000000, status: "paid", date: "2026-07-12" },
  { id: 3,  voyage_id: 1, crew_id: 3,  share_weight_units: 120, payout_paise: 1600000, status: "paid", date: "2026-07-12" },
  { id: 4,  voyage_id: 1, crew_id: 4,  share_weight_units: 110, payout_paise: 1466666, status: "paid", date: "2026-07-12" },
  { id: 5,  voyage_id: 1, crew_id: 5,  share_weight_units: 100, payout_paise: 1333333, status: "paid", date: "2026-07-12" },
  { id: 6,  voyage_id: 1, crew_id: 6,  share_weight_units: 100, payout_paise: 1333333, status: "paid", date: "2026-07-12" },
  { id: 7,  voyage_id: 1, crew_id: 7,  share_weight_units: 100, payout_paise: 1333333, status: "paid", date: "2026-07-12" },
  { id: 8,  voyage_id: 1, crew_id: 8,  share_weight_units: 100, payout_paise: 1333333, status: "paid", date: "2026-07-12" },
  { id: 9,  voyage_id: 1, crew_id: 9,  share_weight_units: 100, payout_paise: 1333333, status: "paid", date: "2026-07-12" },
  { id: 10, voyage_id: 1, crew_id: 10, share_weight_units: 50,  payout_paise: 666666,  status: "paid", date: "2026-07-12" },
  { id: 11, voyage_id: 1, crew_id: 11, share_weight_units: 50,  payout_paise: 666666,  status: "paid", date: "2026-07-12" },
  { id: 12, voyage_id: 2, crew_id: 1,  share_weight_units: 200, payout_paise: 1727272, status: "paid", date: "2026-07-28" },
  { id: 13, voyage_id: 2, crew_id: 2,  share_weight_units: 150, payout_paise: 1295454, status: "paid", date: "2026-07-28" },
  { id: 14, voyage_id: 2, crew_id: 3,  share_weight_units: 120, payout_paise: 1036363, status: "paid", date: "2026-07-28" },
  { id: 15, voyage_id: 3, crew_id: 1,  share_weight_units: 200, payout_paise: 2181818, status: "paid", date: "2026-08-08" },
  { id: 16, voyage_id: 3, crew_id: 2,  share_weight_units: 150, payout_paise: 1636363, status: "paid", date: "2026-08-08" },
  { id: 17, voyage_id: 4, crew_id: 1,  share_weight_units: 200, payout_paise: 1625000, status: "paid", date: "2026-08-21" },
  { id: 18, voyage_id: 5, crew_id: 1,  share_weight_units: 200, payout_paise: 3000000, status: "paid", date: "2026-09-02" },
  { id: 19, voyage_id: 5, crew_id: 2,  share_weight_units: 150, payout_paise: 2250000, status: "paid", date: "2026-09-02" },
  { id: 20, voyage_id: 6, crew_id: 1,  share_weight_units: 200, payout_paise: 1500000, status: "calculated", date: "2026-09-08" },
  { id: 21, voyage_id: 6, crew_id: 2,  share_weight_units: 150, payout_paise: 1125000, status: "calculated", date: "2026-09-08" },
  { id: 22, voyage_id: 6, crew_id: 6,  share_weight_units: 100, payout_paise: 750000,  status: "pending", date: null },
  { id: 23, voyage_id: 6, crew_id: 7,  share_weight_units: 100, payout_paise: 750000,  status: "pending", date: null }
];

const MOCK_INSIGHTS = [
  { type: "success", icon: "treasure", title: "Strongest Voyage", text: "\"Black Sand Shoals\" — highest net profit this quarter at \u20B98,50,000.", action: "View Voyages" },
  { type: "warning", icon: "alert", title: "Expense Alert", text: "Ship repairs account for 37% of total expenses. Consider scheduling bulk maintenance.", action: "Review Expenses" },
  { type: "info", icon: "trendUp", title: "Revenue Trend", text: "Revenue is trending upward across the last 3 completed voyages.", action: "View Analytics" },
  { type: "success", icon: "flag", title: "Fleet Strength", text: "11 active crew members across 8 ranks. All positions filled.", action: "View Crew" },
  { type: "warning", icon: "ship", title: "Maintenance Due", text: "Coral Wreck expedition vessel needs inspection upon return.", action: "View Voyages" }
];