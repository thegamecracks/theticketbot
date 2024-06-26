"""
This setup.py handles compiling .po (portable object) files into their
appropriate .mo (machine object) results.

Reference: https://setuptools.pypa.io/en/latest/userguide/extension.html#setuptools.command.build.SubCommand
Original: https://github.com/thegamecracks/discord.py-i18n-demo/blob/main/setup.py
"""

# pyright: strict
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterator
import warnings

from setuptools import Command, setup
from setuptools.command.build import SubCommand, build  # type: ignore  # missing stub


class build_mo(Command, SubCommand):
    """Builds machine object translation files."""

    build_lib = "build/lib"
    editable_mode = False  # shouldn't be necessary but pyright wants this

    _source_root = Path("src")

    # SubCommand protocol

    def initialize_options(self) -> None:
        """
        Set or (reset) all options/attributes/caches used by the command
        to their default values. Note that these values may be overwritten during
        the build.
        """

    def finalize_options(self) -> None:
        """
        Set final values for all options/attributes used by the command.
        Most of the time, each option/attribute/cache should only be set if it does not
        have any value yet (e.g. ``if self.attr is None: self.attr = val``).
        """

    def run(self) -> None:
        """
        Execute the actions intended by the command.
        (Side effects **SHOULD** only take place when ``run`` is executed,
        for example, creating new files or writing to the terminal output).
        """
        msgfmt = shutil.which("msgfmt")
        if msgfmt is None:
            if os.getenv("LOCALE_MANDATORY") == "1":
                raise RuntimeError(
                    "msgfmt not available for building localizations, "
                    "but is required due to LOCALE_MANDATORY=1"
                )

            return warnings.warn(
                "msgfmt is not available, building .mo files will be skipped",
                RuntimeWarning,
            )

        for source_po in self._find_po_files():
            output_po = self._get_output_path(source_po)
            output_mo = output_po.with_suffix(".mo")

            if not self.editable_mode:
                # Parent directory required for msgfmt to work correctly
                output_mo.parent.mkdir(parents=True, exist_ok=True)

            subprocess.check_call(["msgfmt", "-o", output_mo, output_po])

            if not self.editable_mode:
                # Space savings
                output_po.unlink()

    def get_source_files(self) -> list[str]:
        """
        Return a list of all files that are used by the command to create
        the expected outputs. For example, if your build command transpiles
        Java files into Python, you should list here all the Java files.
        The primary purpose of this function is to help populating the ``sdist``
        with all the files necessary to build the distribution.
        All files should be strings relative to the project root directory.
        """
        return list(self.get_output_mapping().values())

    def get_outputs(self) -> list[str]:
        """
        Return a list of files intended for distribution as they would have been
        produced by the build.
        These files should be strings in the form of
        ``"{build_lib}/destination/file/path"``.

        .. note::
           The return value of ``get_output()`` should include all files used as keys
           in ``get_output_mapping()`` plus files that are generated during the build
           and don't correspond to any source file already present in the project.
        """
        return list(self.get_output_mapping().keys())

    def get_output_mapping(self) -> dict[str, str]:
        """
        Return a mapping between destination files as they would be produced by the
        build (dict keys) into the respective existing (source) files (dict values).
        Existing (source) files should be represented as strings relative to the project
        root directory.
        Destination files should be strings in the form of
        ``"{build_lib}/destination/file/path"``.
        """
        mapping: dict[str, str] = {}
        for source_po in self._find_po_files():
            output_po = self._get_output_path(source_po)
            output_mo = output_po.with_suffix(".mo")
            mapping[str(output_mo)] = str(source_po)
        return mapping

    # Utility methods

    def _find_po_files(self) -> Iterator[Path]:
        """Yields all PO files in the project source directory."""
        for package_path in self._source_root.iterdir():
            if not package_path.is_dir():
                continue

            for po_path in package_path.rglob("*.po"):
                yield po_path

    def _get_output_path(self, path: Path) -> Path:
        if self.editable_mode:
            return path
        path = path.relative_to(self._source_root)
        return Path(self.build_lib) / path

    # Subcommand registration

    build.sub_commands.append(("build_mo", None))


setup(cmdclass={"build_mo": build_mo})
