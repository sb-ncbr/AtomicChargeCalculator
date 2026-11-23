"""Problems that the charge engine reports, with the engine's own types."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# Where the engine reports the issue:
# - "import": reading the file, such as atoms of a residue without bonds;
# - "input": the molecules as a calculation takes them, such as missing hydrogens;
# - "charge": the calculated charges, such as charges far from the formal charges;
# - "plan": how the calculation ran;
# - "rejection": why the method or parameter set does not apply to the molecules;
# - "failure": why the calculation failed;
# - "output": why the charges cannot be written, such as charges outside the range of mmCIF;
# - "acc": ACC's own checks.
IssueSource = Literal["import", "input", "charge", "plan", "rejection", "failure", "output", "acc"]


class IssueDto(BaseModel):
    """One problem of a file or calculation.

    `kind` is ChargeFW's code of the issue, such as "unbonded_residue_atoms"; the kinds of
    ACC's own checks are in `integrations.chargefw.base`. ACC keeps every issue the engine
    reports; what is shown to users is chosen where it is shown.
    """

    kind: str
    message: str
    source: IssueSource
    # ACC's name of the molecule, when the issue is about one.
    molecule: str | None = None
    # Positions of the atoms in the molecule, which are the positions of their charges.
    atom_indices: list[int] = []

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class FileIssueDto(IssueDto):
    """An issue of one uploaded file."""

    file: str
