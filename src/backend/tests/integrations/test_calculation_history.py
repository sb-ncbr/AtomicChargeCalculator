from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.repositories.calculation_set_repository import (
    CalculationSetFilters,
    CalculationSetRepository,
)
from db.schemas import Base
from db.schemas.calculation import AdvancedSettings, CalculationConfig, CalculationSet
from db.schemas.stats import MoleculeSetStats  # noqa: F401
from db.schemas.user import User


@pytest.mark.parametrize(
    "user_id,page,expected_ids,total_count",
    [(100, 1, [1, 2], 3), (100, 2, [3], 3), (100, 3, [], 3), (999, 1, [], 0)],
)
def test_history_pagination_counts_sets_not_joined_configs(
    user_id, page, expected_ids, total_count
):
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            owner = User(id=UUID(int=100), openid="history-owner")
            other = User(id=UUID(int=101), openid="other-owner")
            settings = AdvancedSettings(
                read_hetatm=True, ignore_water=False, permissive_types=False
            )
            configs = [
                CalculationConfig(method="eem", parameters="example"),
                CalculationConfig(method="eqeq", parameters=None),
            ]
            for number in range(1, 6):
                session.add(
                    CalculationSet(
                        id=UUID(int=number),
                        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        user=other if number == 4 else owner,
                        advanced_settings=settings,
                        configs=[] if number == 5 else configs,
                    )
                )
            session.commit()

            result = CalculationSetRepository().get_all(
                session,
                CalculationSetFilters(
                    page=page, page_size=2, order_by="id", order="asc",
                    user_id=UUID(int=user_id),
                ),
            )

            assert result.total_count == total_count
            assert [item.id for item in result.items] == [UUID(int=n) for n in expected_ids]
            assert all(len(item.configs) == 2 for item in result.items)
    finally:
        engine.dispose()
