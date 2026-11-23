from dataclasses import dataclass, field

from models.issue import FileIssueDto
from models.method import Method
from models.parameters import Parameters


@dataclass
class SuitableMethods:
    """Result of suitable methods calculation."""

    methods: list[Method]
    parameters: dict[str, list[Parameters]]
    # Everything the engine warns about in the files as they will be calculated, such as
    # missing hydrogens, known before any calculation.
    warnings: list[FileIssueDto] = field(default_factory=list)
