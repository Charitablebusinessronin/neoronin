"""
BMAD Distribution Builder

Creates downloadable packages for agents, workflows, containers, and complete bundles.
"""

__version__ = "1.0.0"

from .build_release import BMADDistributionBuilder

__all__ = ["BMADDistributionBuilder"]
