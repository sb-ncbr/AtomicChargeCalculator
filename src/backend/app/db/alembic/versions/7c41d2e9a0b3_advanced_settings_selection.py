"""AdvancedSettings selection replaces read_hetatm and ignore_water

Revision ID: 7c41d2e9a0b3
Revises: 2be8d29189d7
Create Date: 2026-11-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c41d2e9a0b3'
down_revision: Union[str, None] = '2be8d29189d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Without HETATM records, ACC left out the modified residues of polymers too, which no
# selection of ChargeFW does; such computations keep "without-hetatm", which ACC shows but
# calculates with no more. The water setting made no difference then, so both such
# settings are one.
SELECTIONS = {
    (True, False): "all",
    (True, True): "polymers-and-ligands",
    (False, False): "without-hetatm",
    (False, True): "without-hetatm",
}
# The former settings closest to each selection.
FORMER_SETTINGS = {
    "all": (True, False),
    "polymers-and-ligands": (True, True),
    "polymers": (False, False),
    "without-hetatm": (False, False),
}
REFERENCING_TABLES = ("calculation_sets", "calculations")


def _merge(bind, rows, update) -> None:
    """Keeps one row of each key; the computations of the others move to it.

    rows: (id, key, values) in the order of preference; update(id, values) sets the new
    columns of a kept row.
    """

    kept = {}
    for settings_id, key, values in rows:
        if key not in kept:
            kept[key] = settings_id
            update(settings_id, values)
            continue

        for table in REFERENCING_TABLES:
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET advanced_settings_id = :kept "
                    "WHERE advanced_settings_id = :id"
                ),
                {"kept": kept[key], "id": settings_id},
            )
        bind.execute(sa.text("DELETE FROM advanced_settings WHERE id = :id"), {"id": settings_id})


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('advanced_settings', sa.Column('selection', sa.String(length=32), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, read_hetatm, ignore_water, permissive_types FROM advanced_settings "
            "ORDER BY read_hetatm DESC, ignore_water"
        )
    ).all()

    def keyed():
        for settings_id, read_hetatm, ignore_water, permissive_types in rows:
            selection = SELECTIONS[(bool(read_hetatm), bool(ignore_water))]
            yield settings_id, (selection, bool(permissive_types)), selection

    _merge(
        bind,
        keyed(),
        lambda settings_id, selection: bind.execute(
            sa.text("UPDATE advanced_settings SET selection = :selection WHERE id = :id"),
            {"selection": selection, "id": settings_id},
        ),
    )

    with op.batch_alter_table('advanced_settings') as batch:
        batch.alter_column('selection', existing_type=sa.String(length=32), nullable=False)
        # Dropping the columns drops their unique constraint.
        batch.drop_column('read_hetatm')
        batch.drop_column('ignore_water')
        batch.create_unique_constraint(
            'advanced_settings_selection_permissive_types_key', ['selection', 'permissive_types']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('advanced_settings') as batch:
        batch.drop_constraint('advanced_settings_selection_permissive_types_key', type_='unique')
        batch.add_column(sa.Column('read_hetatm', sa.Boolean(), nullable=True))
        batch.add_column(sa.Column('ignore_water', sa.Boolean(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, selection, permissive_types FROM advanced_settings "
            "ORDER BY selection = 'polymers'"
        )
    ).all()

    def keyed():
        for settings_id, selection, permissive_types in rows:
            former = FORMER_SETTINGS[selection]
            yield settings_id, (*former, bool(permissive_types)), former

    # "polymers" and "without-hetatm" are both the former settings without HETATM records.
    _merge(
        bind,
        keyed(),
        lambda settings_id, former: bind.execute(
            sa.text(
                "UPDATE advanced_settings SET read_hetatm = :read_hetatm, "
                "ignore_water = :ignore_water WHERE id = :id"
            ),
            {"read_hetatm": former[0], "ignore_water": former[1], "id": settings_id},
        ),
    )

    with op.batch_alter_table('advanced_settings') as batch:
        batch.alter_column('read_hetatm', existing_type=sa.Boolean(), nullable=False)
        batch.alter_column('ignore_water', existing_type=sa.Boolean(), nullable=False)
        batch.drop_column('selection')
        batch.create_unique_constraint(
            'advanced_settings_read_hetatm_ignore_water_permissive_types_key',
            ['read_hetatm', 'ignore_water', 'permissive_types'],
        )
