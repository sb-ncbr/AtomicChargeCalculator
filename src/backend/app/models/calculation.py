"""Calculation models"""

from datetime import datetime
from enum import Enum
from typing import Dict
import uuid

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from models.molecule_info import MoleculeSetStats

from models.issue import IssueDto
from models.setup import StoredSettingsDto

Charges = Dict[str, list[float]]


class CalculationState(Enum):
    CALCULATING = ".calculating"
    FAILED = ".failed"
    COMPLETED = ".completed"


class CalculationConfigDto(BaseModel):
    """Calculation configuration data transfer object"""

    method: str | None = None
    parameters: str | None = None

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )

    def __hash__(self) -> int:
        # Configurations are dictionary keys; equal ones (pydantic compares field values)
        # must hash equally, so that a configuration requested twice is calculated once.
        return hash((self.method, self.parameters))


class CalculationDto(BaseModel):
    """Calculation data transfer object"""

    file: str
    file_hash: str
    charges: Charges
    config: CalculationConfigDto
    # Everything the engine warns about: the file's molecules, such as atoms without bonds,
    # and this calculation, such as charges far from the formal charges.
    warnings: list[IssueDto] = []

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class CalculationFailureDto(BaseModel):
    """A configuration whose charges are not available for a file, and why."""

    file: str
    file_hash: str
    message: str
    # The engine's code of the reason, or one of ACC's kinds in integrations.chargefw.base.
    kind: str
    # Every reason the engine gave, with its kind.
    issues: list[IssueDto] = []
    # What the engine warns about in the file's molecules, when it could read them.
    warnings: list[IssueDto] = []

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class CalculationPreviewDto(BaseModel):
    """Calculation preview data transfer object"""

    file: str

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class CalculationSetDto(BaseModel):
    """Calculation set data transfer object"""

    id: uuid.UUID
    calculations: list[CalculationDto]
    configs: list[CalculationConfigDto]
    settings: StoredSettingsDto

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class CalculationSetPreviewDto(BaseModel):
    """Calculation set preview data transfer object"""

    id: uuid.UUID
    files: dict[str, MoleculeSetStats]
    configs: list[CalculationConfigDto]
    settings: StoredSettingsDto
    created_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class CalculationResultDto(BaseModel):
    """Result of charge calculation"""

    config: CalculationConfigDto
    calculations: list[CalculationDto]
    # Files for which the calculation of this configuration failed; the other
    # configurations of the computation are not affected.
    failures: list[CalculationFailureDto] = []

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )
