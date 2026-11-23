"""This module provides a repository for calculation configs."""

from sqlalchemy import select
from sqlalchemy.orm import joinedload, Session


from db.schemas.calculation import CalculationConfig
from db.schemas.stats import AtomTypeCount, MoleculeSetStats


class MoleculeSetStatsRepository:
    """Repository for managing MoleculeSetStats."""

    def get(self, session: Session, file_hash: str) -> MoleculeSetStats | None:
        """Get info about a file based on file hash.

        Args:
            file_hash (str): Hash of the file.

        Returns:
            MoleculeSetStats | None: Information about the file or None if not found.
        """

        statement = (
            select(MoleculeSetStats)
            .options(joinedload(MoleculeSetStats.atom_type_counts))
            .execution_options(populate_existing=True)
            .where(MoleculeSetStats.file_hash == file_hash)
        )

        info = (session.execute(statement)).scalars().first()

        return info

    def store(self, session: Session, info: MoleculeSetStats) -> CalculationConfig:
        """Store info about a file in the database.

        A file stored before gets the new counts: they are those of the engine that
        reads the file now, which may count other atoms than a former one did.

        Args:
            config (CalculationConfig): Calculation config.

        Raises:
            ValueError: If the calculation set to which the calculation config belongs is not found.

        Returns:
            CalculationConfig: Stored calculation config.
        """

        # Uploads of one file at the same time wait for each other here: each would
        # otherwise replace the counts the other one read, and both sets would stay.
        session.execute(
            select(MoleculeSetStats.file_hash)
            .where(MoleculeSetStats.file_hash == info.file_hash)
            .with_for_update()
        )
        exists = self.get(session, info.file_hash)

        if exists is not None:
            if _counts(exists) == _counts(info):
                return exists
            exists.total_molecules = info.total_molecules
            exists.total_atoms = info.total_atoms
            for count in list(exists.atom_type_counts):
                session.delete(count)
            # New rows: those of `info` would bring it into the session with them.
            exists.atom_type_counts = [
                AtomTypeCount(symbol=count.symbol, count=count.count)
                for count in info.atom_type_counts
            ]
            return exists

        session.add(info)
        return info


def _counts(info: MoleculeSetStats) -> tuple:
    return (
        info.total_molecules,
        info.total_atoms,
        sorted((count.symbol, count.count) for count in info.atom_type_counts),
    )
