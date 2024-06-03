"""Re-invokes xgettext on source packages and merges them into .po/.pot files."""

import argparse
import subprocess
from contextlib import contextmanager, nullcontext
from pathlib import Path, PurePosixPath
from typing import Generator, Iterable


@contextmanager
def temporary_po_from_source(
    source_files: Iterable[Path],
    output_path: Path,
) -> Generator[Path, None, None]:
    subprocess.check_call(
        [
            "xgettext",
            # Extract comments from source
            # https://www.gnu.org/software/gettext/manual/gettext.html#index-_002dc_002c-xgettext-option
            "--add-comments",
            "-o",
            # Normalize generated source file references in POSIX style
            PurePosixPath(output_path),
            *(PurePosixPath(p) for p in source_files),
        ],
    )

    try:
        # Hide CHARSET warning by defaulting to utf-8
        content_type_temp = rb'"Content-Type: text/plain; charset=CHARSET\n"'
        content_type_utf8 = rb'"Content-Type: text/plain; charset=UTF-8\n"'
        content_pot = output_path.read_bytes()
        content_pot = content_pot.replace(content_type_temp, content_type_utf8)
        output_path.write_bytes(content_pot)

        yield output_path
    finally:
        output_path.unlink(missing_ok=True)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "-t",
    "--template",
    action="store_true",
    dest="merge_template",
    help="Instead of generating from source, use the POT file to merge",
)
args = parser.parse_args()

for package_path in Path("src").iterdir():
    if not package_path.is_dir():
        continue

    pot_files = tuple(package_path.glob("*.pot"))
    if not pot_files:
        continue

    print(package_path)

    source_files: list[Path] = []
    source_files.extend(package_path.rglob("*.py"))
    if not source_files:
        continue

    po_paths: list[Path] = []
    po_paths.extend(package_path.rglob("*.po"))
    if not args.merge_template:
        po_paths.extend(package_path.rglob("*.pot"))
    if not po_paths:
        continue

    if args.merge_template:
        merging_po_cm = nullcontext(pot_files[0])
        print(f"Merging from {pot_files[0]}...")
    else:
        merging_po_cm = temporary_po_from_source(
            source_files,
            output_path=package_path / "messages.po.merging",
        )
        print("Generating PO from source to merge...")

    with merging_po_cm as merging_po:
        for po_path in po_paths:
            print(po_path)
            subprocess.check_call(["msgmerge", po_path, merging_po, "-o", po_path])
