from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Method:
    """Method model."""

    name: str
    internal_name: str
    full_name: str
    publication: str | None
    type: Literal["2D", "3D", "other"]
    has_parameters: bool
    # What users should know about the method, such as the molecules it supports.
    notes: str | None = None
