from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.repositories.moleculeset_stats_repository import MoleculeSetStatsRepository
from db.schemas import Base
from db.schemas.calculation import CalculationSet  # noqa: F401
from db.schemas.stats import AtomTypeCount, MoleculeSetStats
from db.schemas.user import User  # noqa: F401


def stats(total_atoms: int, counts: dict[str, int]) -> MoleculeSetStats:
    return MoleculeSetStats(
        file_hash="hash",
        total_molecules=1,
        total_atoms=total_atoms,
        atom_type_counts=[AtomTypeCount(symbol=s, count=c) for s, c in counts.items()],
    )


def test_a_file_stored_before_gets_the_new_counts():
    # The same file read by another engine: it may count other atoms, such as alternate
    # locations, and the file list must agree with the upload.
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        repository = MoleculeSetStatsRepository()
        with Session(engine) as session:
            repository.store(session, stats(1, {"N": 1}))
            session.commit()
            repository.store(session, stats(2, {"N": 1, "C": 1}))
            session.commit()

        with Session(engine) as session:
            stored = repository.get(session, "hash")
            assert stored.total_atoms == 2
            assert {c.symbol: c.count for c in stored.atom_type_counts} == {"N": 1, "C": 1}
            assert session.execute(select(func.count()).select_from(AtomTypeCount)).scalar() == 2
    finally:
        engine.dispose()


def test_unchanged_counts_are_left_as_they_are():
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        repository = MoleculeSetStatsRepository()
        with Session(engine) as session:
            repository.store(session, stats(2, {"N": 1, "C": 1}))
            session.commit()
            ids = set(session.execute(select(AtomTypeCount.id)).scalars())
            repository.store(session, stats(2, {"C": 1, "N": 1}))
            session.commit()

            assert set(session.execute(select(AtomTypeCount.id)).scalars()) == ids
    finally:
        engine.dispose()
