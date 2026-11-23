"""Interface of the charge engine, implemented for ChargeFW."""

from dataclasses import dataclass, field
from typing import Any, TypeAlias
from abc import ABC, abstractmethod

from models.calculation import Charges
from models.issue import IssueDto
from models.method import Method
from models.parameters import Parameters
from models.setup import Selection

# Molecules read by an engine; only the engine that read them uses them.
Molecules: TypeAlias = Any


# Kinds of the failures that ACC finds itself; the others are the engine's.
# A method with parameter sets named without one; ChargeFW would choose one itself.
PARAMETER_SET_REQUIRED = "parameter_set_required"
ATOM_IDS_UNSUPPORTED = "atom_ids_unsupported"
NOT_APPLICABLE = "not_applicable"
UNEXPECTED_ERROR = "unexpected_error"
# The server ran out of memory reading the file or calculating its charges.
OUT_OF_MEMORY = "out_of_memory"


class EngineError(RuntimeError):
    """A failure that the engine explains; the message is for users.

    kind: the engine's code of the first issue, or one of ACC's kinds above.
    issues: every issue the engine gave as a reason.
    """

    def __init__(self, message: str, kind: str, issues: list[IssueDto] | None = None):
        super().__init__(message)
        self.kind = kind
        self.issues = issues or []


class MoleculeReadError(EngineError):
    """A file that the engine cannot read."""


class ChargeCalculationError(EngineError):
    """A calculation of one method and parameter set that failed."""


@dataclass(frozen=True)
class CalculatedCharges:
    """Charges of each molecule and what the engine warns about in the calculation."""

    charges: Charges
    warnings: list[IssueDto] = field(default_factory=list)


class ChargeEngine(ABC):
    """Reads molecules, lists methods, and calculates charges."""

    @abstractmethod
    def molecules(
        self,
        file_path: str,
        selection: Selection = "all",
        permissive_types: bool = True,
    ) -> Molecules:
        """Load molecules from a file

        Args:
            file_path (str): File path from which to load molecules.
            selection (Selection, optional): Atoms of PDB/mmCIF files to read. Defaults to "all".
            permissive_types (bool, optional): Use similar parameters for similar atom/bond types if no exact match is found. Defaults to True.

        Returns:
            Molecules: Parsed molecules
        """
        raise NotImplementedError()

    @abstractmethod
    def info(self, molecules: Molecules) -> dict:
        """Counts of molecules, atoms, and atoms of each element.

        Returns:
            dict: "total_molecules", "total_atoms", and "atom_type_counts", a list of
                {"symbol", "count"}.
        """
        raise NotImplementedError()

    @abstractmethod
    def warnings(self, molecules: Molecules) -> list[IssueDto]:
        """Every problem the engine found when it read the molecules, such as atoms without
        bonds."""
        raise NotImplementedError()

    @abstractmethod
    def config_error(self, method: str, parameters: str | None) -> str | None:
        """Why a method and parameter set cannot be calculated, or None if they can."""
        raise NotImplementedError()

    @abstractmethod
    def get_available_methods(
        self,
    ) -> list[Method]:
        """Get all available methods.

        Returns:
            list[str]: List of method names.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_available_parameters(self, method: str) -> list[Parameters]:
        """Get all parameters available for provided method.

        Args:
            method (str): Method name.

        Returns:
            list[str]: List of parameter names.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_best_parameters(self, molecules: Molecules, method: str) -> Parameters | None:
        """Get best parameters for provided method.

        Args:
            method (str): Method name.
            molecules (Molecules): Set of molecules.

        Returns:
            Parameters | None: Best parameters for provided method; None if the method has
            no parameters or none of them apply to the molecules.

        """
        raise NotImplementedError()

    @abstractmethod
    def get_suitable_methods(self, molecules: Molecules) -> list[tuple[Method, list[Parameters]]]:
        """Get methods and parameters that are suitable for a given set of molecules.

        Args:
            molecules (Molecules): Set of molecules.

        Returns:
            list[tuple[str, list[str]]]: List of tuples containing method name and parameters for that method.
        """
        raise NotImplementedError()

    @abstractmethod
    def calculate_charges(
        self,
        molecules: Molecules,
        method_name: str,
        parameters_name: str | None = None,
        chg_out_dir: str | None = None,
    ) -> CalculatedCharges:
        """Calculate partial atomic charges for a given molecules and method.

        Args:
            molecules (Molecules): Set of molecules.
            method_name (str): Method name to be used.
            parameters_name (Optional[str], optional):Parameters to be used with provided method. Defaults to None.

        Returns:
            CalculatedCharges: Charges by molecule name, and the engine's warnings about the
            calculation.
        """
        raise NotImplementedError()
