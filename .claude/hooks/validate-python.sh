#!/bin/bash
# PostToolUse hook: syntax-check Python files right after an edit lands.
# Exit 2 = report error back to Claude, exit 0 = silent success.

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE" == *.py ]]; then
  OUTPUT=$(python3 -m py_compile "$FILE" 2>&1)
  if [ $? -ne 0 ]; then
    echo "Python syntax error in $FILE:" >&2
    echo "$OUTPUT" >&2
    exit 2
  fi
fi

exit 0
