"""
gallery_ui.py
-------------
Backwards-compatibility shim. The UI was rewritten in `panel.py`;
`LightspeedGallery` is kept as an alias for any external scripts.
"""

from .panel import LightspeedPanel

LightspeedGallery = LightspeedPanel

__all__ = ["LightspeedGallery", "LightspeedPanel"]
