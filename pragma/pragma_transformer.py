import re
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
    # Pattern to match CREATE(...) [IF(...)] [ASYNC(...)]
    pattern = re.compile(
        r"^\s*!\$acc\s+enter\s+data\s+create\s*\(([^)]+)\)"
        r"(?:\s+if\s*\(([^)]+)\))?"
        r"(?:\s+async\s*\(([^)]+)\))?",
        re.IGNORECASE
    )

    def match(self, line):
        return bool(self.pattern.match(line))

    def transform(self, line):
        match = self.pattern.match(line)
        if not match:
            return line

        args = match.group(1).strip()
        condition = match.group(2).strip() if match.group(2) else None
        async_clause = match.group(3).strip() if match.group(3) else None

        if condition and async_clause:
            return f"GPU_DATA_ALLOC_IF_ASYNC({condition}, {async_clause}, {args})\n"
        elif condition:
            return f"GPU_DATA_ALLOC_IF({condition}, {args})\n"
        elif async_clause:
            return f"GPU_DATA_ALLOC_ASYNC({async_clause}, {args})\n"
        else:
            return f"GPU_DATA_ALLOC({args})\n"
