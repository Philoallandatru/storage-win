from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-Source", type=Path, required=True)
    parser.add_argument("-Output", type=Path, required=True)
    args = parser.parse_args()
    source = args.Source.resolve()
    output = args.Output.resolve()
    files = [path for path in source.rglob("*") if path.is_file()]
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
        for index, path in enumerate(files, start=1):
            archive.write(path, path.relative_to(source).as_posix())
            if index % 1000 == 0:
                print(f"archived={index}/{len(files)}", flush=True)
    print(f"archived={len(files)}/{len(files)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
