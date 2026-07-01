"""add booking_code to bookings

Revision ID: a1c2e3d4f5a6
Revises: 83f5a19b7a78
Create Date: 2026-06-30 17:20:00.000000

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c2e3d4f5a6'
down_revision: Union[str, Sequence[str], None] = '83f5a19b7a78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Self-contained (migrations shouldn't import app code that may change later).
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def upgrade() -> None:
    """Add booking_code, backfill existing rows, then enforce unique + not null."""
    op.add_column('bookings', sa.Column('booking_code', sa.String(length=12), nullable=True))

    conn = op.get_bind()
    bookings = sa.table(
        'bookings',
        sa.column('id', sa.Uuid()),
        sa.column('booking_code', sa.String()),
    )
    used: set[str] = set()
    for (booking_id,) in conn.execute(sa.select(bookings.c.id)).fetchall():
        while True:
            code = "".join(secrets.choice(_ALPHABET) for _ in range(8))
            if code not in used:
                used.add(code)
                break
        conn.execute(
            bookings.update().where(bookings.c.id == booking_id).values(booking_code=code)
        )

    op.alter_column('bookings', 'booking_code', existing_type=sa.String(length=12), nullable=False)
    op.create_index('ix_bookings_booking_code', 'bookings', ['booking_code'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_bookings_booking_code', table_name='bookings')
    op.drop_column('bookings', 'booking_code')
