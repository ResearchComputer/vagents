"""
VAgents Package Manager

This module provides functionality for managing and executing code packages from remote git repositories.
"""

from .package import (
    PackageManager,
    PackageConfig,
    PackageMetadata,
    PackageExecutionContext,
    GitRepository,
    PackageRegistry,
)

__all__ = [
    "PackageManager",
    "PackageConfig",
    "PackageMetadata",
    "PackageExecutionContext",
    "GitRepository",
    "PackageRegistry",
]
