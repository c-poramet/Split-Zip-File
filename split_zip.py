#!/usr/bin/env python3
"""
split_zip.py - Compress a file or folder into a ZIP and split it into
fixed-size parts (default 10 MB) so it can be sent over platforms with
small upload limits. Can also join the parts back together.

Usage:
    # Compress + split (default 10 MB parts)
    python split_zip.py big_file.iso
    python split_zip.py my_folder -s 8
    python split_zip.py big_file.iso -s 25 -o output_dir

    # Join the parts back into the original zip
    python split_zip.py --join big_file.iso.zip.001
    python split_zip.py --join big_file.iso.zip.001 -o restored.zip

Parts are named  <name>.zip.001, <name>.zip.002, ...
After joining you get a normal .zip you can open with any unzip tool.
(On Windows you can also join manually:  copy /b name.zip.* name.zip
 On Linux/macOS:  cat name.zip.* > name.zip)
"""

import argparse
import os
import re
import sys
import tempfile
import zipfile

MB = 1024 * 1024
BUFFER = 1024 * 1024  # 1 MB copy buffer


def build_zip(source: str, zip_path: str, level: int) -> None:
    """Create a zip at zip_path from a file or directory."""
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=level,
        allowZip64=True,
    ) as zf:
        if os.path.isfile(source):
            zf.write(source, arcname=os.path.basename(source))
        else:
            base = os.path.dirname(os.path.abspath(source))
            for root, _dirs, files in os.walk(source):
                for name in files:
                    full = os.path.join(root, name)
                    zf.write(full, arcname=os.path.relpath(full, base))


def split_file(path: str, part_size: int, out_dir: str, base_name: str) -> list:
    """Split `path` into numbered parts of at most `part_size` bytes."""
    parts = []
    index = 1
    with open(path, "rb") as src:
        while True:
            part_path = os.path.join(out_dir, f"{base_name}.{index:03d}")
            written = 0
            with open(part_path, "wb") as dst:
                while written < part_size:
                    chunk = src.read(min(BUFFER, part_size - written))
                    if not chunk:
                        break
                    dst.write(chunk)
                    written += len(chunk)
            if written == 0:  # nothing left; remove empty trailing part
                os.remove(part_path)
                break
            parts.append(part_path)
            index += 1
    return parts


def compress_and_split(source: str, size_mb: float, out_dir: str, level: int) -> None:
    source = os.path.normpath(source)
    if not os.path.exists(source):
        sys.exit(f"Error: '{source}' does not exist.")
    if size_mb <= 0:
        sys.exit("Error: part size must be greater than 0.")

    os.makedirs(out_dir, exist_ok=True)
    base_name = os.path.basename(source) + ".zip"
    part_size = int(size_mb * MB)

    # Build the zip in a temp file, then split it.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_zip = os.path.join(tmp, base_name)
        print(f"Compressing '{source}' ...")
        build_zip(source, tmp_zip, level)
        zip_size = os.path.getsize(tmp_zip)
        print(f"Zip size: {zip_size / MB:.2f} MB")

        if zip_size <= part_size:
            # Fits in one piece: no need to split, just save the plain zip.
            final = os.path.join(out_dir, base_name)
            os.replace(tmp_zip, final) if os.path.splitdrive(tmp)[0] == os.path.splitdrive(final)[0] else _copy(tmp_zip, final)
            print(f"Smaller than {size_mb:g} MB, no split needed -> {final}")
            return

        parts = split_file(tmp_zip, part_size, out_dir, base_name)

    print(f"Created {len(parts)} parts of up to {size_mb:g} MB in '{out_dir}':")
    for p in parts:
        print(f"  {os.path.basename(p)}  ({os.path.getsize(p) / MB:.2f} MB)")
    print("\nTo restore:  python split_zip.py --join "
          f"{os.path.basename(parts[0])}")


def _copy(src: str, dst: str) -> None:
    with open(src, "rb") as s, open(dst, "wb") as d:
        while True:
            chunk = s.read(BUFFER)
            if not chunk:
                break
            d.write(chunk)


def join_parts(first_part: str, output: str = None) -> None:
    """Join <name>.zip.001, .002, ... back into <name>.zip."""
    m = re.match(r"^(.*)\.(\d{3,})$", first_part)
    if not m:
        sys.exit("Error: give the first part, e.g. name.zip.001")
    prefix, _ = m.groups()
    width = len(m.group(2))
    output = output or prefix

    if os.path.exists(output):
        sys.exit(f"Error: '{output}' already exists. Choose another with -o.")

    count = 0
    with open(output, "wb") as dst:
        n = 1
        while True:
            part = f"{prefix}.{n:0{width}d}"
            if not os.path.exists(part):
                break
            with open(part, "rb") as src:
                while True:
                    chunk = src.read(BUFFER)
                    if not chunk:
                        break
                    dst.write(chunk)
            count += 1
            n += 1

    if count == 0:
        os.remove(output)
        sys.exit(f"Error: could not find '{prefix}.{1:0{width}d}'.")
    print(f"Joined {count} parts -> {output}")
    if zipfile.is_zipfile(output):
        print("Zip file looks valid.")
    else:
        print("Warning: result is not a valid zip. Are all parts present?")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Zip a file/folder and split it into N MB parts (default 10).")
    p.add_argument("path", help="File or folder to compress "
                                "(or the first part when using --join)")
    p.add_argument("-s", "--size", type=float, default=10,
                   help="Max size of each part in MB (default: 10)")
    p.add_argument("-o", "--output", default=None,
                   help="Output directory for parts (default: current dir), "
                        "or output zip path when using --join")
    p.add_argument("-l", "--level", type=int, default=6, choices=range(0, 10),
                   metavar="0-9", help="Compression level (default: 6)")
    p.add_argument("--join", action="store_true",
                   help="Join parts back into one zip file")
    args = p.parse_args()

    if args.join:
        join_parts(args.path, args.output)
    else:
        compress_and_split(args.path, args.size, args.output or ".", args.level)


if __name__ == "__main__":
    main()
