#!/usr/bin/env python3
"""
Patch to ensure Annotated is available globally for LangChain/LangGraph.
"""

# Import Annotated and make it available globally
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

# Make it available in the global namespace for any module that might need it
import builtins
builtins.Annotated = Annotated

# Also patch common modules that might need it
import sys

# Add Annotated to the typing module if it's not there
import typing
if not hasattr(typing, 'Annotated'):
    typing.Annotated = Annotated

# Add it to typing_extensions as well
try:
    import typing_extensions
    if not hasattr(typing_extensions, 'Annotated'):
        typing_extensions.Annotated = Annotated
except ImportError:
    pass

print("✅ Annotated patch applied successfully!")
print(f"Annotated available in builtins: {hasattr(builtins, 'Annotated')}")
print(f"Annotated available in typing: {hasattr(typing, 'Annotated')}")
