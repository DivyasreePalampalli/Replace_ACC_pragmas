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
        if not match or line,startswith("!!"):
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
    pragma_start_pattern = re.compile(r"^(\s*)!\$acc\s+enter\s+data\s+create\s*\(([^)]+)\)", re.IGNORECASE)

    def match(self, line):
        return bool(self.pragma_start_pattern.match(line))

    def extract_clauses(self, rest):
        """Extract IF(...) and ASYNC(...) from rest of the line, handling nested parentheses."""
        condition = None
        async_clause = None

        def find_balanced_clause(prefix, s):
            start = s.lower().find(prefix.lower())
            if start == -1:
                return None, s

            i = start + len(prefix)
            if i >= len(s) or s[i] != '(':
                return None, s

            depth = 1
            i += 1
            begin = i
            while i < len(s):
                if s[i] == '(':
                    depth += 1
                elif s[i] == ')':
                    depth -= 1
                    if depth == 0:
                        return s[begin:i].strip(), s[i + 1:].strip()
                i += 1
            return None, s  # unmatched

        condition, rest = find_balanced_clause("if", rest)
        async_clause, _ = find_balanced_clause("async", rest)
        return condition, async_clause

    def transform(self, line):
        match = self.pragma_start_pattern.match(line)
        if not match or line,startswith("!!"):
            return line

        indent = match.group(1)
        args = match.group(2).strip()
        rest_of_line = line[match.end():].strip()

        condition, async_clause = self.extract_clauses(rest_of_line)

        if condition and async_clause:
            return f"{indent}GPU_DATA_ALLOC_IF_ASYNC({condition}, {async_clause}, {args})\n"
        elif condition:
            return f"{indent}GPU_DATA_ALLOC_IF({condition}, {args})\n"
        elif async_clause:
            return f"{indent}GPU_DATA_ALLOC_ASYNC({async_clause}, {args})\n"
        else:
            return f"{indent}GPU_DATA_ALLOC({args})\n"


class AccDataHostTransformer(PragmaTransformer):
    pattern = re.compile(
        r"""^\s*!\$ACC\s+
            (?P<type>UPDATE|DATA)\s+
            HOST\s*\((?P<vars>[^)]+)\)                        # host variables
            (?:\s+WAIT\s*\((?P<wait>[^)]+)\))?                # optional WAIT clause
            (?:\s+ASYNC\s*\((?P<async>[^)]+)\))?              # optional ASYNC clause
            (?:\s+IF\s*\((?P<if>[^)]+)\))?                    # optional IF clause
        """, re.IGNORECASE | re.VERBOSE)

    def match(self, line):
        return bool(self.pattern.match(line))

    def transform(self, line):
        match = self.pattern.match(line)
        if not match or line,startswith("!!"):
            return line  # no match, unchanged

        vars_ = match.group("vars").strip()
        wait = match.group("wait")
        async_ = match.group("async")
        condition = match.group("if")
        op_type = match.group("type").upper()

        var_list = [v.strip() for v in vars_.split(",")]
        var_args = ", ".join(var_list)

        # Handle !$ACC DATA HOST(...) IF(...)
        if op_type == "DATA":
            if condition:
                return f"GPU_DATA_HOST_IF({condition}, {var_args})\n"
            else:
                # Optionally implement GPU_DATA_HOST_SIMPLE if needed
                return f"GPU_DATA_HOST_SIMPLE({var_args})\n"

        # UPDATE case
        if condition and async_:
            return f"GPU_DATA_UPDATE_HOST_ASYNC_IF({condition}, {async_.strip()}, {var_args})\n"
        if condition and wait:
            return f"GPU_DATA_UPDATE_HOST_WAIT_IF({condition}, {wait.strip()}, {var_args})\n"
        if condition:
            return f"GPU_DATA_UPDATE_HOST_IF({condition}, {var_args})\n"

        # Default fallback
        return f"GPU_DATA_UPDATE_HOST({var_args})\n"
