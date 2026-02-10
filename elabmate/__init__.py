"""Public API for elabmate.

@author Thibaut Jacqmin
"""

from .bridge import ElabBridge
from .client import ElabClient
from .experiment import ElabExperiment
from .exceptions import (
    DeletedExperiment,
    DuplicateTitle,
    ElabException,
    InvalidCategory,
    InvalidID,
    InvalidStatus,
    InvalidTag,
    InvalidTemplate,
    InvalidTitle,
)

__all__ = [
    "ElabBridge",
    "ElabClient",
    "ElabExperiment",
    "DeletedExperiment",
    "DuplicateTitle",
    "ElabException",
    "InvalidCategory",
    "InvalidID",
    "InvalidStatus",
    "InvalidTag",
    "InvalidTemplate",
    "InvalidTitle",
]

__version__ = "0.1.0"
