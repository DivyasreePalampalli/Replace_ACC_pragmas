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

def update_temp_lines(lines):
    """
    Extracts variable names and alloc-style argument strings from temp(...) calls.
    Returns a dictionary: {variable_name: alloc_arg_string}
    """
    updated_lines = []
    
    pattern = re.compile(
        r'temp\s*\(\s*(REAL|INTEGER)\s*\(\s*KIND\s*=\s*(\w+)\s*\)\s*,\s*(\w+)\s*,\s*\((.*?)\)\s*\)'  # REAL/INTEGER with KIND
        r'|temp\s*\(\s*(REAL|INTEGER)\s*,\s*(\w+)\s*,\s*\((.*?)\)\s*\)'                              # REAL/INTEGER without KIND
        r'|temp\s*\(\s*(LOGICAL)\s*,\s*(\w+)\s*,\s*\((.*?)\)\s*\)',                                  # LOGICAL
        re.IGNORECASE
    )

    temp_map = {}

    for line in lines:
        match = pattern.search(line)
        if match:
            if match.group(1):  # REAL/INTEGER with KIND
                type_base = match.group(1).upper()
                kind = match.group(2).upper()
                var_name = match.group(3)
                dims = match.group(4)
                dim_list = extract_dims(dims)
                line = f"{type_base} (KIND={kind}), pointer :: {var_name}({','.join(dim_list)})\n"
                # line = alloc_args

            elif match.group(5):  # REAL/INTEGER without KIND
                type_base = match.group(5).upper()
                var_name = match.group(6)
                dims = match.group(7)
                dim_list = extract_dims(dims)
                line = f"{type_base}, pointer :: {var_name}({','.join(dim_list)})\n"
                # temp_map[var_name] = alloc_args

            elif match.group(8):  # LOGICAL
                var_name = match.group(9)
                dims = match.group(10)
                dim_list = extract_dims(dims)
                line = f"{type_base}, pointer :: {var_name}({','.join(dim_list)})"
                # temp_map[var_name] = alloc_args
        updated_lines.append(line)

    return updated_lines



def extract_dims(dim_str):
    """
    Process dimension string: strips spaces, removes `0:` ranges to just upper bound, and adds (0, 0, 0) padding if needed.
    """
    raw_dims = [d.strip() for d in dim_str.split(',')]
    clean_dims = []
    add_padding = False

    for d in raw_dims:
        if ':' in d:
            parts = d.split(':')
            clean_dims.append(parts[-1].strip())  # Keep upper bound only
            add_padding = True
        else:
            clean_dims.append(d)

    clean_dims_with_colon = [":" for _ in range(len(clean_dims))]

    return clean_dims_with_colon

def detect_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read(4096)
    result = chardet.detect(raw)
    return result['encoding'] or 'utf-8'

def process_file(file_path):
    encoding = detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        lines = f.readlines()

    updated_lines = update_temp_lines(lines)

    if lines != updated_lines:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        print(f"Updated: {file_path}")

def main():

    '''
    Description:
        This script scans .f90/.F90 files to update temp declaration lines

    Purpose:
        In large Fortran codebases, allocation blocks often repeat argument declarations already defined in temp(...) helper macros. This tool:

        Finds all .f90 / .F90 files in a specified directory (recursively).
        Identifies temp(REAL(KIND=JPRB), VAR, (DIM)) declarations.
        Replaces them with temp (TYPE, NAME, (DIM1, DIM2, DIM3)) -> type, pointer :: NAME(:,:,:)

    Usage:
        python3 update_temp_declarations.py [directory] 
        
    Example:
        python3 update_temp_declarations ./src
    '''


    parser = argparse.ArgumentParser(description="Update alloc calls based on temp declarations.")
    parser.add_argument("directory", nargs="?", default=".", help="Root directory to search (default: current directory)")
    args = parser.parse_args()

    for file_path in find_files(args.directory):
        process_file(file_path)

if __name__ == "__main__":
    main()

