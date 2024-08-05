from typing import Iterable, Iterator, Literal

from packaging.version import Version

from . import __version__

CURRENT_VERSION = Version(__version__)
SYNC_VERSIONS = (
    Version("0.1.0"),
    Version("0.2.0"),
    Version("0.3.0"),
    Version("0.5.0"),
)


def versions_in_range(
    versions: Iterable[Version],
    start: Version,
    end: Version,
    *,
    include_start: bool = False,
    include_end: bool = True,
) -> Iterator[Version]:
    for v in versions:
        if include_start and v == start:
            yield v
        elif include_end and v == end:
            yield v
        elif start < v < end:
            yield v


def upgrade_or_downgrade(
    versions: Iterable[Version], a: Version, b: Version
) -> Literal[-1, 0, 1]:
    if a == b:
        return 0
    elif a < b:
        return 1 if any(versions_in_range(versions, a, b)) else 0
    elif any(versions_in_range(versions, b, a, include_start=True, include_end=False)):
        return -1
    else:
        return 0


def sync_upgrade_or_downgrade(a: Version, b: Version) -> Literal[-1, 0, 1]:
    return upgrade_or_downgrade(SYNC_VERSIONS, a, b)
