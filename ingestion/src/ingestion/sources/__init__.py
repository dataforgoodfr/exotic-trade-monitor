from collections.abc import Callable

from ingestion.sources import cites, eurostat

SOURCES: dict[str, Callable[[], None]] = {
    "cites": cites.run,
    "eurostat": eurostat.run,
}
