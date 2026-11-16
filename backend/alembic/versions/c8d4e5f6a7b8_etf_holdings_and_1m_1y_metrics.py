"""etf holdings and 1m/1y metrics

Revision ID: c8d4e5f6a7b8
Revises: b7c1d2e3f4a5
Create Date: 2026-11-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("metrics_snapshot", sa.Column("chg_1m_pct", sa.Float(), nullable=True))
    op.add_column("metrics_snapshot", sa.Column("chg_1m_abs", sa.Float(), nullable=True))
    op.add_column("metrics_snapshot", sa.Column("chg_1y_pct", sa.Float(), nullable=True))
    op.add_column("metrics_snapshot", sa.Column("chg_1y_abs", sa.Float(), nullable=True))
    op.create_index("ix_metrics_snapshot_chg_1m_pct", "metrics_snapshot", ["chg_1m_pct"])
    op.create_index("ix_metrics_snapshot_chg_1y_pct", "metrics_snapshot", ["chg_1y_pct"])

    op.create_table(
        "etf_holdings_snapshot",
        sa.Column("ticker", sa.String(length=12), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("holdings", sa.JSON(), nullable=False),
        sa.Column("aum", sa.Float(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ticker"], ["companies.ticker"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ticker"),
    )
    op.create_table(
        "holding_return_cache",
        sa.Column("ticker", sa.String(length=24), nullable=False),
        sa.Column("chg_1w_pct", sa.Float(), nullable=True),
        sa.Column("chg_1m_pct", sa.Float(), nullable=True),
        sa.Column("chg_1y_pct", sa.Float(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("ticker"),
    )


def downgrade() -> None:
    op.drop_table("holding_return_cache")
    op.drop_table("etf_holdings_snapshot")
    op.drop_index("ix_metrics_snapshot_chg_1y_pct", table_name="metrics_snapshot")
    op.drop_index("ix_metrics_snapshot_chg_1m_pct", table_name="metrics_snapshot")
    op.drop_column("metrics_snapshot", "chg_1y_abs")
    op.drop_column("metrics_snapshot", "chg_1y_pct")
    op.drop_column("metrics_snapshot", "chg_1m_abs")
    op.drop_column("metrics_snapshot", "chg_1m_pct")
