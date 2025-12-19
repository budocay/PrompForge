"""
DEPRECATED: This module is kept for backward compatibility.
Please use promptforge.web package instead.

Usage:
    from promptforge.web import create_interface, launch_web
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "promptforge.web module is deprecated. "
    "Use 'from promptforge.web import create_interface, launch_web' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new package for backward compatibility
from .web import (
    create_interface,
    launch_web,
    set_base_path,
    get_forge,
)

__all__ = [
    "create_interface",
    "launch_web",
    "set_base_path",
    "get_forge",
]
