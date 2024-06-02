import importlib.resources
import logging
import re
import sqlite3
from contextlib import contextmanager
from typing import Iterable, Iterator, NamedTuple, Self


log = logging.getLogger(__name__)


class Migration(NamedTuple):
    version: int
    sql: str


class Migrations(tuple[Migration, ...]):
    def after_version(self, version: int) -> Self:
        """Return a copy of self with only migrations after the given version."""
        return type(self)(m for m in self if m.version > version)

    def version_exists(self, version: int) -> bool:
        return any(m.version == version for m in self)

    @classmethod
    def from_iterable_unsorted(cls, it: Iterable[Migration]) -> Self:
        return cls(sorted(it, key=lambda m: m.version))


class MigrationFinder:
    _FILE_PATTERN = re.compile(r"(\d+)-(.+)\.sql")

    def discover(self) -> Migrations:
        migrations: list[Migration] = [Migration(version=-1, sql="")]

        assert __package__ is not None
        path = importlib.resources.files(__package__).joinpath("migrations/")

        for file in path.iterdir():
            if not file.is_file():
                continue

            m = self._FILE_PATTERN.fullmatch(file.name)
            if m is None:
                continue

            version = int(m[1])
            sql = file.read_text("utf-8")
            migrations.append(Migration(version=version, sql=sql))

        return Migrations.from_iterable_unsorted(migrations)


class Migrator:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def run_migrations(self, migrations: Migrations) -> None:
        version = self.get_version()
        if version > 0 and not migrations.version_exists(version):
            log.warning(
                "Unrecognized database version %d, skipping migrations",
                version,
            )
            return

        with self.begin() as conn:
            for version, script in migrations.after_version(version):
                log.info("Migrating database to v%d", version)
                conn.executescript(script)

            conn.execute(f"PRAGMA user_version = {version:d}")

    def get_version(self) -> int:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        log.debug("PRAGMA user_version returned %d", version)
        return version

    @contextmanager
    def begin(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN")
        try:
            yield self.conn
        except BaseException:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()


def run_default_migrations(conn: sqlite3.Connection) -> None:
    migrations = MigrationFinder().discover()
    migrator = Migrator(conn)
    migrator.run_migrations(migrations)
