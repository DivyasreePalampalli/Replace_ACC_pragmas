import os
import re
import argparse
import chardet

import pragma.pragma_transformer as pt


MACROS_INCLUDE_LINE = "include 'macros.h'\n"


def join_multiline_pragma(lines):
    """Yields logical lines, combining continued !$ACC lines, preserving indentation."""
    buffer = ""
    leading_ws = ""

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("!$ACC"):
            # Capture and preserve the leading whitespace of the first line
            if not buffer:
                leading_ws = re.match(r"^(\s*)", line).group(1)

            # Remove !$ACC and trailing &
            content = re.sub(r"^\s*!\$ACC\s*", "", line).rstrip("& \n")

            if buffer:
                buffer += " " + content
            else:
                buffer = content

            if line.strip().endswith("&"):
                continue  # Continue collecting
            else:
                yield leading_ws + "!$ACC " + buffer.strip()
                buffer = ""
                leading_ws = ""
        else:
            if buffer:
                yield leading_ws + "!$ACC " + buffer.strip()
                buffer = ""
                leading_ws = ""
            yield line.rstrip("\n")  # Preserve non-pragma lines
    if buffer:
        yield leading_ws + "!$ACC " + buffer.strip()


def detect_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read(4096)
    result = chardet.detect(raw)
    return result['encoding'] or 'utf-8'


def process_file(filepath, transformers):
    encoding = detect_encoding(filepath)
    with open(filepath, encoding=encoding, errors="replace") as f:
        raw_lines = f.readlines()

    transformed = False
    new_lines = []
    has_macros_include = any("include 'macros.h'" in line.lower() for line in raw_lines)

    for line in join_multiline_pragma(raw_lines):
        transformed_line = line
        for transformer in transformers:
            if transformer.match(line):
                transformed_line = transformer.transform(line)
                transformed = True
                break  # Only one transformer should handle each line
        new_lines.append(transformed_line + "\n")  # Add back line breaks

    if transformed:
        print(f"Updated: {filepath}")
        if not has_macros_include:
            # Insert macros include after any initial comments or empty lines
            insert_at = 0
            while insert_at < len(new_lines) and (new_lines[insert_at].strip().startswith("!") or new_lines[insert_at].strip() == ""):
                insert_at += 1
            new_lines.insert(insert_at, MACROS_INCLUDE_LINE)
        with open(filepath, 'w') as f:
            f.writelines(new_lines)


def walk_and_process(root_dir, transformers):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(".f90"):
                filepath = os.path.join(dirpath, filename)
                process_file(filepath, transformers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Replace OpenACC pragmas in Fortran files according to a YAML mapping."
    )
    parser.add_argument(
        "base_directory",
        nargs='?',
        default="./src",
        help="Base directory to search for .F90 files (default: ./src)"
    )
    args = parser.parse_args()
    base_directory = args.base_directory
    if not os.path.exists(base_directory):
        print(f"File Not Exists : {base_directory}")
    transformers = []

    for name, cls in pt.__dict__.items():
        if (
            isinstance(cls, type) and
            issubclass(cls, pt.PragmaTransformer) and
            cls is not pt.PragmaTransformer
        ):
            transformers.append(cls())  # instantiate the subclass

    walk_and_process(base_directory, transformers)
