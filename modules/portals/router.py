from __future__ import annotations

from config.settings import external_apply_portals, external_apply_generic_fallback

from .generic import GenericExternalAdapter
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .workday import WorkdayAdapter


def _get_enabled_portals() -> set[str]:
    try:
        return {str(item).strip().lower() for item in external_apply_portals}
    except Exception:
        return {"workday", "greenhouse", "lever"}


def detect_portal_adapter(url: str):
    enabled = _get_enabled_portals()
    adapters = []
    if "workday" in enabled:
        adapters.append(WorkdayAdapter())
    if "greenhouse" in enabled:
        adapters.append(GreenhouseAdapter())
    if "lever" in enabled:
        adapters.append(LeverAdapter())

    for adapter in adapters:
        try:
            if adapter.detect(url):
                return adapter
        except Exception:
            continue
    if external_apply_generic_fallback:
        return GenericExternalAdapter(url)
    return None
