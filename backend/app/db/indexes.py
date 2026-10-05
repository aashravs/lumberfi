"""
MongoDB index definitions.

Unique indexes are what make the import / calculation pipeline idempotent:
re-running either operation can only ever update existing documents.
"""


def ensure_indexes(database) -> None:
    """Create all required indexes (safe to call repeatedly)."""
    # One deal per business identifier.
    database.deals.create_index("deal_id", unique=True)

    # Exactly one commission document per deal.
    database.commissions.create_index("deal_id", unique=True)

    # A deal can have several payouts, and a component can repeat
    # (e.g. monthly commissions), so `sequence` is the position of the payout
    # among the deal's payouts of the same component.
    database.payouts.create_index(
        [("deal_id", 1), ("component", 1), ("sequence", 1)],
        unique=True,
        name="uniq_deal_component_sequence",
    )

    # One audit record per upload.
    database.imports.create_index("import_id", unique=True)

    # Unique email per user.
    database.users.create_index("email", unique=True)
