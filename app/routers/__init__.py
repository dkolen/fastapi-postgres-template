"""HTTP routers, registered automatically.

Every module in this package that defines a module-level `router`
(an `APIRouter`) is included in `api_router`. Set the prefix and tags on the
router itself, e.g. `router = APIRouter(prefix="/items", tags=["items"])`.
"""

import importlib
import pkgutil

from fastapi import APIRouter

api_router = APIRouter()

for _module_info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
    _module = importlib.import_module(f"{__name__}.{_module_info.name}")
    _router = getattr(_module, "router", None)
    if isinstance(_router, APIRouter):
        api_router.include_router(_router)
