import hashlib
from .extraction import extract_definitions


from .utility import (is_procedure_or_function_start, 
                      safe_get_line, 
                      safe_get_next_line, 
                      is_large_comment_block, 
                      is_begin, 
                      is_end)
from .metadata import calculate_chunk_metadata, compute_file_metadata

def add_chunk(chunks, current_chunk, current_start, current_end, global_vars, procedures, constants, types):
    """Adds a chunk to the chunks list if current_chunk is not empty with its metadata."""
    
    if current_chunk:
        chunk_content = '\n'.join(current_chunk)
        chunk_metadata = {"variables": [], "procedures": [], "constants": [], "types": []}

        for var in global_vars:
            if var in chunk_content:
                chunk_metadata["variables"].append(var)
        for proc in procedures:
            if proc[0] in chunk_content:
                chunk_metadata["procedures"].append(proc[0])
        for const in constants:
            if const[0] in chunk_content:
                chunk_metadata["constants"].append(const[0])
        for typ in types:
            if typ[0] in chunk_content:
                chunk_metadata["types"].append(typ[0])

        chunks.append({
            "content": current_chunk.copy(),
            "start_line": current_start,
            "end_line": current_end,
            "metadata": chunk_metadata
        })

def compute_hashes(chunks):
    for chunk in chunks:
        chunk_content = '\n'.join(chunk["content"])
        hash_obj = hashlib.sha256(chunk_content.encode('utf-8'))
        hash_full = hash_obj.hexdigest()
        chunk["hash"] = hash_full
        chunk["hashTruncated"] = hash_full[:16]

import re

def chunk(lines, file_path=None, file_content=None, versions=[], language="pascal"):
    chunks = []
    current_chunk = []
    block_depth = 0
    start_line = 1
    procedure_stack = []
    comment_cache = []
    module_name = None
    in_main_program = False
    in_multiline_comment = False

    def is_procedure_or_function_start(line, language="pascal"):
        if language == "pascal":
            return re.match(r"^\s*(procedure|function)\s+(\w+)", line, re.I)
        elif language == "modula-2":
            return re.match(r"^\s*PROCEDURE\s+\w+", line, re.I)

    def is_module_start(line, language="pascal"):
        if language == "pascal":
            return None
        elif language == "modula-2":
            return re.match(r"^\s*MODULE\s+(\w+)", line, re.I)

    def is_module_end(line, module_name, language="pascal"):
        if language == "pascal":
            return False
        elif language == "modula-2":
            return re.match(fr"^\s*END\s+{module_name}\.", line, re.I) is not None

    def get_parent_hash(parent_name):
        return hashlib.sha256(parent_name.encode()).hexdigest()[:16] if parent_name else None


    for line_num, line in enumerate(lines, 1):  # Enumerate from 1 for correct line numbers.
        stripped_line = line.strip().lower()

        # Handling module start
        module_match = is_module_start(line, language)
        if module_match:
            module_name = module_match.group(1)
            current_chunk.append(line)
            continue

        # Handling module end
        if module_name and is_module_end(stripped_line, module_name, language):
            current_chunk.append(line)
            chunk_data = {
                "content": current_chunk.copy(),
                "start_line": start_line,
                "end_line": line_num,
                "parent_name": None  # For modules, we don't have a parent in this context.
            }
            chunks.append(calculate_chunk_metadata(chunk_data))
            current_chunk = []
            start_line = line_num + 1
            module_name = None
            continue

        # Handling comments
        if stripped_line.startswith("(*"):
            in_multiline_comment = True
        if in_multiline_comment:
            comment_cache.append(line)
            if stripped_line.endswith("*)"):
                in_multiline_comment = False
            continue

        # Skip blank lines
        if not stripped_line:
            continue

        # For a program's main declaration, module, or procedure, add preceding comments to the chunk.
        if is_procedure_or_function_start(stripped_line) or (language == "pascal" and re.match(r"^\s*program\s+\w+", stripped_line, re.I)) or is_module_start(line, language):
            if current_chunk:
                chunk_data = {
                    "content": current_chunk.copy(),
                    "start_line": start_line,
                    "end_line": line_num - len(comment_cache) - 1,
                    "parent_name": procedure_stack[-1] if procedure_stack else None,
                    "parent_hash": get_parent_hash(procedure_stack[-1] if procedure_stack else None)
                }
                chunks.append(calculate_chunk_metadata(chunk_data))
                current_chunk = []
                start_line = line_num - len(comment_cache)
            current_chunk.extend(comment_cache)
            comment_cache.clear()

        # Handle procedure or function start
        proc_match = is_procedure_or_function_start(stripped_line, language)
        if proc_match:
            procedure_name = proc_match.group(2)
            procedure_stack.append(procedure_name)

        current_chunk.append(line)

        # Adjusting for the main program BEGIN...END block
        if language == "pascal" and re.match(r"^\s*begin", stripped_line, re.I) and not in_main_program:
            in_main_program = True
            block_depth = 0  # Resetting the block depth because it's a new block

        # Adjust block depth
        block_depth += stripped_line.count("begin")
        block_depth -= stripped_line.count("end")

        # If we encounter an 'end' with block depth of zero
        if block_depth == 0 and "end" in stripped_line:
            if in_main_program:  # If you're inside the main program
                in_main_program = False
                chunk_data = {
                    "content": current_chunk.copy(),
                    "start_line": start_line,
                    "end_line": line_num,
                    "parent_name": None  # No parent for the main program
                }
                chunks.append(calculate_chunk_metadata(chunk_data))
                current_chunk = []
                start_line = line_num + 1
                continue
            else:
                chunk_data = {
                    "content": current_chunk.copy(),
                    "start_line": start_line,
                    "end_line": line_num,
                    "parent_name": procedure_stack[-1] if procedure_stack else None,
                    "parent_hash": get_parent_hash(procedure_stack[-1] if procedure_stack else None)
                }
                chunks.append(calculate_chunk_metadata(chunk_data))
                current_chunk = []
                start_line = line_num + 1
                if procedure_stack:
                    procedure_stack.pop()

    # Handle any leftover content
    if current_chunk:
        chunk_data = {
            "content": current_chunk,
            "start_line": start_line,
            "end_line": line_num,
            "parent_name": procedure_stack[-1] if procedure_stack else None,
            "parent_hash": get_parent_hash(procedure_stack[-1] if procedure_stack else None)
        }
        chunks.append(calculate_chunk_metadata(chunk_data))

    file_metadata = compute_file_metadata(file_path, "".join(lines), lines, chunks, versions)

    return {
        "metadata": file_metadata,
        "chunks": chunks
    }

# Remember to define or adapt the function `calculate_chunk_metadata` and `compute_file_metadata` outside of the chunk function.
