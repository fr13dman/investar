from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

BATCH = 500


def upsert(session: Session, model, rows: list[dict], keys: list[str]) -> None:
    """INSERT ... ON CONFLICT DO UPDATE for SQLite, in batches (SQLite caps bound params)."""
    if not rows:
        return
    for i in range(0, len(rows), BATCH):
        chunk = rows[i : i + BATCH]
        stmt = insert(model).values(chunk)
        update_cols = {c: stmt.excluded[c] for c in chunk[0] if c not in keys}
        if update_cols:
            stmt = stmt.on_conflict_do_update(index_elements=keys, set_=update_cols)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=keys)
        session.execute(stmt)
