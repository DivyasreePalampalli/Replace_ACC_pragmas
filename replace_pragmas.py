import os
import re
import yaml
import argparse
import chardet

def load_mapping(yaml_path):
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("acc_to_omp", {})

def replace_acc_pragmas_in_text(text, mapping):
    # Sort keys by length (longest first) to avoid partial matches
    sorted_keys = sorted(mapping.keys(), key=len, reverse=True)
    key_pattern = '|'.join(re.escape(k) for k in sorted_keys)
    pragma_pattern = re.compile(
        rf'(!\$acc\s*)({key_pattern})(?=\s*\(|\s+|$)',  # Lookahead for ( or whitespace or end of line
        re.IGNORECASE
    )

    replaced = False

    def repl(match):
        nonlocal replaced
        acc_key = match.group(2)
        replacement = mapping.get(acc_key.lower(), mapping.get(acc_key, None))
        if replacement:
            replaced = True
            return f"{replacement}"
        return match.group(0)

    # Use re.sub on the whole text, but only modify lines containing !$acc
    # To preserve original line endings, split using splitlines(keepends=True)
    lines = text.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        if "!$acc" in line.lower():
            new_line = pragma_pattern.sub(repl, line)
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    new_text = "".join(new_lines)
    return new_text, replaced

def detect_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read(4096)
    result = chardet.detect(raw)
    return result['encoding'] or 'utf-8'

def process_file(filepath, mapping):
    header = '#include "macros.h"\n'
    encoding = detect_encoding(filepath)
    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        content = f.read()
    new_content, replaced = replace_acc_pragmas_in_text(content, mapping)
    if replaced:
        # Only add header if not already present
        if header not in new_content:
            new_content = header + new_content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated: {filepath}")


def process_directory(base_directory, mapping):
    for root, dirs, files in os.walk(base_directory):
        for filename in files:
            if  any(filename.lower().endswith(x) for x in (".f90", ".f", ".fypp", ".h", ".c", ".cc")):
                process_file(os.path.join(root, filename), mapping)

def main():
    parser = argparse.ArgumentParser(
        description="Replace OpenACC pragmas in Fortran files according to a YAML mapping."
    )
    parser.add_argument(
        "base_directory",
        nargs='?',
        default="./src",
        help="Base directory to search for .F90 files (default: ./src)"
    )
    parser.add_argument(
        "yaml_mapping_file",
        nargs='?',
        default="./acc_to_omp.yaml",
        help="YAML file with acc_to_omp mapping (default: ./acc_to_omp.yaml)"
    )
    args = parser.parse_args()

    mapping = load_mapping(args.yaml_mapping_file)
    process_directory(args.base_directory, mapping)

if __name__ == "__main__":
    main()


