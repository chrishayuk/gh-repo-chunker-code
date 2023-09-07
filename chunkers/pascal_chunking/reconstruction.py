def reconstruct_program(chunked_data, language="pascal"):
    chunks = chunked_data["chunks"]
    reconstructed_lines = []

    # The base indentation level
    indentation_level = 0

    # Define a helper function to handle the indentation
    def apply_indentation(line, level):
        return "    " * level + line

    in_comment_block = False
    for chunk in chunks:
        for line in chunk["content"]:
            stripped_line = line.strip().upper()  # use uppercase for all checks

            # Handling comments
            if not in_comment_block and (stripped_line.startswith("(*") or stripped_line.startswith("{")):
                in_comment_block = True

            if in_comment_block:
                reconstructed_lines.append(apply_indentation(line, indentation_level))
                if stripped_line.endswith("*)") or stripped_line.endswith("}"):
                    in_comment_block = False
                continue

            # Handling constructs and indentation
            if stripped_line in ["CONST", "TYPE", "VAR"]:
                reconstructed_lines.append(apply_indentation(line, indentation_level))
            elif stripped_line.startswith("MODULE ") and language == "modula-2":
                reconstructed_lines.append(apply_indentation(line, indentation_level))
                indentation_level += 1
            elif stripped_line.startswith("PROCEDURE ") or (language == "pascal" and stripped_line.startswith("FUNCTION ")):
                reconstructed_lines.append(apply_indentation(line, indentation_level))
                indentation_level += 1
            elif stripped_line.startswith("BEGIN"):
                reconstructed_lines.append(apply_indentation(line, indentation_level))
                indentation_level += 1
            elif stripped_line.startswith("END"):
                indentation_level -= 1
                reconstructed_lines.append(apply_indentation(line, indentation_level))
            elif stripped_line.startswith("IF ") or stripped_line.startswith("FOR ") or stripped_line.startswith("WHILE ") or stripped_line.startswith("CASE ") or (language == "modula-2" and stripped_line.startswith("LOOP ")):
                reconstructed_lines.append(apply_indentation(line, indentation_level))
                if not line.strip().endswith('then') and not line.strip().endswith('do') and not line.strip().endswith('of'):
                    indentation_level += 1
            elif stripped_line.startswith("ELSE") or stripped_line.startswith("ELSIF"):
                reconstructed_lines.append(apply_indentation(line, indentation_level))
            elif language == "modula-2" and stripped_line.startswith("REPEAT"):
                reconstructed_lines.append(apply_indentation(line, indentation_level))
            elif language == "modula-2" and stripped_line.startswith("UNTIL"):
                reconstructed_lines.append(apply_indentation(line, indentation_level))
                indentation_level -= 1
            else:
                reconstructed_lines.append(apply_indentation(line, indentation_level))

    return "\n".join(reconstructed_lines)
