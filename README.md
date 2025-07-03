**OpenACC Pragma Replacer**

This tool recursively scans Fortran .F90 source files in a directory, replacing specified OpenACC pragmas with custom macros or OpenMP pragmas as defined in a YAML mapping file. It is especially useful for porting or adapting code to new GPU programming models or for code modernization.

**Features**
    
    Recursive processing: All .F90 files in the specified directory and subdirectories are processed.
    
    Flexible mapping: Easily configure pragma replacements via a YAML file.
    
    Safe editing: Only files with actual replacements are modified.
    
    Macro header insertion: Optionally inserts a macro header at the top of modified files.
    
    Encoding robust: Handles various file encodings automatically.

**Requirements**

    Python 3.7+
    
    PyYAML
    
    chardet
    

**Install dependencies with:**

     pip install pyyaml chardet
     
**Usage**

    python replace_pragms.py [base_directory] [yaml_mapping_file]
    
    base_directory (optional): Directory to search for .F90 files. Default: ./src
    
    yaml_mapping_file (optional): Path to YAML mapping file. Default: ./acc_to_omp.yaml
    

**Examples:**

    python replace_pragms.py
    
    python replace_pragms.py ./my_fortran_src ./my_mapping.yaml
    

**YAML Mapping File**

The YAML file defines how each OpenACC pragma should be replaced.
Example (acc_to_omp.yaml):

acc_to_omp:

  enter data create: GPU_ENTER_DATA_CREATE
  
  parallel loop: GPU_PARALLEL_LOOP
  
  kernels: GPU_KERNELS
  
  data: GPU_DATA
  
  enter data copyin: GPU_ENTER_DATA_COPYIN
  
  exit data copyout: GPU_EXIT_DATA_COPYOUT
  
  update host: GPU_UPDATE_HOST
  
  update device: GPU_UPDATE_DEVICE
  
  wait: GPU_WAIT


**Macro Header**

If a file is modified, a macro header (e.g., #include "macros.h") is inserted at the top, unless it is already present. You can customize this header in the script.


**How it Works**

The script scans each .F90 file, line by line.

When it finds an OpenACC pragma matching a key in the YAML, it replaces just that pragma with the mapped value, preserving arguments and formatting.
If any pragma is replaced, the macro header is inserted at the top of the file (if not already present).

The script preserves the original file's line endings and does not introduce spurious changes.

