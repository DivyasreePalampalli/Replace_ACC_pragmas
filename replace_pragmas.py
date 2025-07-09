import os
import re
import argparse
import chardet

MACROS_INCLUDE_LINE = "include 'macros.h'\n"

class PragmaTransformer:
    def match(self, line):
        """Return True if the line matches the pragma handled by this transformer."""
        raise NotImplementedError

    def transform(self, line):
        """Transform the matching pragma line into macro form."""
        raise NotImplementedError


class AccDataPresentTransformer(PragmaTransformer):
    # Pattern to match !$ACC DATA PRESENT(...) [COPYIN(...)] [COPY(...)] [IF(...)]
    pattern = re.compile(
        r"""^\s*!\$ACC\s+DATA
             \s+PRESENT\s*\(([^)]+)\)              # group 1: PRESENT
             (?:\s+COPYIN\s*\(([^)]+)\))?          # group 2: COPYIN
             (?:\s+COPY\s*\(([^)]+)\))?            # group 3: COPY
             (?:\s+IF\s*\(([^)]+)\))?              # group 4: IF
         """, re.IGNORECASE | re.VERBOSE)

    def match(self, line):
        return bool(self.pattern.match(line))

    def transform(self, line):
        match = self.pattern.match(line)
        if not match:
            return line  # unchanged

        present = match.group(1).strip()
        copyin = match.group(2).strip() if match.group(2) else ""
        copy = match.group(3).strip() if match.group(3) else ""
        condition = match.group(4).strip() if match.group(4) else ""

        present_vars = [var.strip() for var in present.split(",")]

        # Case 1: COPYIN or COPY is present → use GPU_DATA_PRESENT_COPY
        if copyin or copy:
            args = [condition, copyin, copy] + present_vars
            args_cleaned = ", ".join(arg for arg in args if arg)
            return f"GPU_DATA_PRESENT_COPY({args_cleaned})\n"

        # Case 2: IF condition only → GPU_DATA_PRESENT_IF
        if condition:
            present_args = ", ".join(present_vars)
            return f"GPU_DATA_PRESENT_IF({condition}, {present_args})\n"

        # Case 3: Default → GPU_DATA_PRESENT_SIMPLE
        present_args = ", ".join(present_vars)
        return f"GPU_DATA_PRESENT_SIMPLE({present_args})\n"

class AccCreateDataTransformer(PragmaTransformer):
    # Match: !$acc enter data create (something)
    pattern = re.compile(r"^\s*!\$acc\s+enter\s+data\s+create\s*\(([^)]+)\)", re.IGNORECASE)

    def match(self, line):
        return bool(self.pattern.match(line))

    def transform(self, line):
        match = self.pattern.match(line)
        if not match:
            return line

        args = match.group(1).strip()
        return f"GPU_DATA_ALLOC({args})\n"

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
    transformers = [
        AccDataPresentTransformer(),
        # In future: Other transformers like AccKernelsTransformer(), AccLoopTransformer(), etc.
    ]
    walk_and_process(base_directory, transformers)
