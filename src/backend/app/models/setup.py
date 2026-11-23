from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Setup(BaseModel):
    """Setup model."""

    computation_id: str


# The atoms of PDB and mmCIF files that ChargeFW reads; each selection adds to the next:
# "polymers" are protein and nucleic acid chains with their modified residues,
# "polymers-and-ligands" adds ligands and ions, and "all" adds water.
Selection = Literal["all", "polymers-and-ligands", "polymers"]


class AdvancedSettingsDto(BaseModel):
    """Settings of a computation."""

    selection: Selection = "all"
    permissive_types: bool = True

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        # Settings ACC no longer has, such as readHetatm, are refused, not ignored.
        extra="forbid",
    )


# Before ChargeFW 3, ACC could leave out HETATM records, modified residues of polymers
# included. Computations stored with that setting keep it, so the history shows them as
# they were made, but ACC calculates with it no more.
LEGACY_SELECTION = "without-hetatm"
StoredSelection = Literal["all", "polymers-and-ligands", "polymers", "without-hetatm"]


class StoredSettingsDto(BaseModel):
    """Settings of a stored computation, made by this or an earlier version of ACC."""

    selection: StoredSelection
    permissive_types: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class LegacySettingsError(ValueError):
    """A stored computation has settings ACC no longer calculates with; the message is for
    users."""


def settings_for_calculation(stored) -> AdvancedSettingsDto:
    """The settings to calculate a stored computation with.

    Raises:
        LegacySettingsError: The computation left out HETATM records.
    """

    if stored.selection == LEGACY_SELECTION:
        raise LegacySettingsError(
            "This computation left out HETATM records, as ACC did before it used ChargeFW 3, "
            "and ACC no longer calculates that way. Its charges stay available; start a new "
            "computation to calculate other ones."
        )
    return AdvancedSettingsDto(selection=stored.selection, permissive_types=stored.permissive_types)
