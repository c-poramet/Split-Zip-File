# split_zip

A small Python script that compresses a file or folder into a ZIP and splits it into fixed-size parts (default **10 MB**), so you can send large files over platforms with small upload limits. It can also join the parts back together.

No dependencies: it uses only the Python standard library (Python 3.6+).

## Usage

### Compress and split

```
python split_zip.py <file_or_folder> [-s SIZE_MB] [-o OUTPUT_DIR] [-l LEVEL]
```

Examples:

```
python split_zip.py big_file.iso              # 10 MB parts, in the current folder
python split_zip.py big_file.iso -s 25        # 25 MB parts
python split_zip.py my_folder -s 8 -o parts   # 8 MB parts, saved in ./parts
```

This produces:

```
big_file.iso.zip.001
big_file.iso.zip.002
big_file.iso.zip.003
...
```

### Restore the original

Put all the parts in the same folder and run, pointing at the first part:

```
python split_zip.py --join big_file.iso.zip.001
```

This creates `big_file.iso.zip`, which you can open with any normal unzip tool. Use `-o name.zip` to choose a different output name.

No Python on the receiving side? Join the parts manually instead:

- **Windows (cmd):** `copy /b big_file.iso.zip.* big_file.iso.zip`
- **Linux / macOS:** `cat big_file.iso.zip.* > big_file.iso.zip`

## Options

| Option | Description | Default |
| --- | --- | --- |
| `path` | File or folder to compress (or the first part when using `--join`) | required |
| `-s`, `--size` | Maximum size of each part, in MB | `10` |
| `-o`, `--output` | Output folder for parts (or output zip path with `--join`) | current folder |
| `-l`, `--level` | Compression level, 0 (none) to 9 (max) | `6` |
| `--join` | Join parts back into a single zip | off |

## Notes

- **Parts can't be opened individually.** They are raw slices of a single zip, so the receiver needs all of them and must join them before unzipping.
- **Small files:** if the zip is already smaller than the part size, you get a normal single `.zip` with no splitting.
- **Part size:** 1 MB here means 1,048,576 bytes (1024 × 1024).
- **Disk space:** the full zip is built in a temporary folder before it is split, so you need roughly twice the source size in free space.
- **Already-compressed files** (video, JPEG, existing archives) won't shrink much; splitting still works as normal.
- **Existing output:** `--join` refuses to overwrite an existing file. Remove it or pick another name with `-o`.
- Make sure every part is present when joining. The script checks that the result is a valid zip and warns if it isn't.
