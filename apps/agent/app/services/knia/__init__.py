from __future__ import annotations

__all__ = ["match_knia_charts"]


def match_knia_charts(*args, **kwargs):
    from app.services.knia.knia_matcher import match_knia_charts as _match_knia_charts
    return _match_knia_charts(*args, **kwargs)
