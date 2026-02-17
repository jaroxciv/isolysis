"""Path resolution with traversal protection."""

import os
from typing import Optional

from loguru import logger


def resolve_project_path(path: str, must_exist: bool = True) -> Optional[str]:
    """
    Normalize and resolve a file path (absolute or relative) within the project.

    Ensures consistent behavior between Streamlit (frontend) and FastAPI (backend)
    when working with uploaded files stored under `data/tmp`.

    Args:
        path (str): The input file path (absolute or relative).
        must_exist (bool): If True, logs a warning when the resolved path does not exist.

    Returns:
        str: The absolute, normalized path, or None if the path escapes the project root.
    """
    if not path:
        return None

    try:
        # Normalize slashes and collapse redundant parts
        p = os.path.normpath(path)

        # Convert to absolute if relative
        if not os.path.isabs(p):
            p = os.path.join(os.getcwd(), p)

        # Containment check: block path traversal outside project root
        project_root = os.getcwd()
        if not p.startswith(project_root + os.sep) and p != project_root:
            logger.error(
                f"Path traversal blocked: '{path}' resolves outside project root"
            )
            return None

        # Warn if missing
        if must_exist and not os.path.exists(p):
            logger.warning(f"File not found or inaccessible: {p}")

        return p
    except Exception as e:
        logger.error(f"Failed to resolve path '{path}': {e}")
        return path
