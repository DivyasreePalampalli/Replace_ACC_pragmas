import os
import re
import argparse
import chardet

def find_files(root_dir):
    """Find all .f90 and .F90 files recursively"""
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(".f90"):
                yield os.path.join(dirpath, filename)

def extract_temp_declarations(lines):
    """
    Extracts variable names and full argument strings from temp(...) calls.
    Returns a dictionary: {variable_name: full_argument_string}
    """
    pattern = re.compile(
        r'temp\s*\(\s*(REAL|INTEGER)\s*\(KIND\s*=\s*(\w+)\)\s*,\s*(\w+)\s*,\s*\((.*?)\)\s*\)'
        r'|temp\s*\(\s*(LOGICAL)\s*,\s*(\w+)\s*,\s*\((.*?)\)\s*\)',
        re.IGNORECASE
    )

    temp_map = {}

    for line in lines:
        match = pattern.search(line)
        if match:
            if match.group(1):  # REAL or INTEGER match
                type_base = match.group(1).upper()           # REAL or INTEGER
                kind = match.group(2).upper()                # JPRB or JPIM
                var_name = match.group(3)
                dims = match.group(4)
                full_args = f"({type_base} (KIND={kind}), {var_name}, ({dims}))"
            else:  # LOGICAL match
                var_name = match.group(6)
                dims = match.group(7)
                full_args = f"(LOGICAL, {var_name}, ({dims}))"

            temp_map[var_name] = full_args

    return temp_map
    
def update_alloc_lines(lines, temp_map):
    """
    Replace alloc8/alloc4 lines if matching variable is in temp_map.
    """
    updated_lines = []
    inside_if_block = False
    current_var = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect the start of KIND-based block
        kind_match = re.match(r'IF\s*\(\s*KIND\s*\(\s*(\w+)\s*\)\s*==\s*(\d+)\s*\)\s*THEN', stripped, re.IGNORECASE)
        elseif_match = re.match(r'ELSEIF\s*\(\s*KIND\s*\(\s*(\w+)\s*\)\s*==\s*(\d+)\s*\)\s*THEN', stripped, re.IGNORECASE)

        if kind_match or elseif_match:
            current_var = kind_match.group(1) if kind_match else elseif_match.group(1)
            inside_if_block = True
            updated_lines.append(line)
            continue

        if inside_if_block and current_var and current_var in temp_map:
            alloc_match = re.match(r'\s*(alloc(8|4))\s*\(\s*.*?\)', line, re.IGNORECASE)
            if alloc_match:
                func = alloc_match.group(1)
                # Replace with the full temp-style declaration
                new_line = re.sub(r'\(.*\)', f'{temp_map[current_var]}', line)
                updated_lines.append(new_line)
                continue

        if stripped.upper() == 'ENDIF':
            inside_if_block = False
            current_var = None

        updated_lines.append(line)
    return updated_lines

def detect_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read(4096)
    result = chardet.detect(raw)
    return result['encoding'] or 'utf-8'

def process_file(file_path):
    encoding = detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        lines = f.readlines()

    temp_map = extract_temp_declarations(lines)
    updated_lines = update_alloc_lines(lines, temp_map)

    if lines != updated_lines:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        print(f"Updated: {file_path}")

def main():

    '''
    Description:
        This script scans .f90/.F90 files to update alloc8(var) and alloc4(var) calls by replacing them with the full argument list from matching temp(REAL(KIND=JPRB), var, (...)) declarations.

    Purpose:
        In large Fortran codebases, allocation blocks often repeat argument declarations already defined in temp(...) helper macros. This tool:

        Finds all .f90 / .F90 files in a specified directory (recursively).
        Identifies temp(REAL(KIND=JPRB), VAR, (DIM)) declarations.
        Locates matching alloc8(VAR) / alloc4(VAR) blocks.
        Replaces them with the full argument list from the original temp(...) call.

    Usage:
        python3 update_alloc_calls.py [directory] 
        
    Example:
        python3 update_alloc_calls.py ./src
    '''


    parser = argparse.ArgumentParser(description="Update alloc calls based on temp declarations.")
    parser.add_argument("directory", nargs="?", default=".", help="Root directory to search (default: current directory)")
    args = parser.parse_args()

    for file_path in find_files(args.directory):
        process_file(file_path)

if __name__ == "__main__":
    main()

