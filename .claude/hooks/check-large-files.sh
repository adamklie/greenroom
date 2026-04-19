#!/bin/bash
# PreToolUse hook: warn about large files before git add/commit.
# Greenroom's audio/video files belong in the iCloud vault, not git.
# Exit 2 = block, exit 0 = allow. We warn but don't block (dual-use — e.g.
# a new dependency tarball might legitimately be >50MB once in a blue moon).

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check git add and git commit commands
if [[ "$COMMAND" =~ ^git\ (add|commit) ]]; then
  # Find files larger than 50MB in the working directory (ignore .git)
  LARGE_FILES=$(find . -not -path './.git/*' -type f -size +50M 2>/dev/null | head -10)

  if [ -n "$LARGE_FILES" ]; then
    echo "WARNING: Large files detected (>50MB) that may block git push:" >&2
    echo "$LARGE_FILES" | while read f; do
      SIZE=$(ls -lh "$f" 2>/dev/null | awk '{print $5}')
      echo "  $f ($SIZE)" >&2
    done
    echo "" >&2
    echo "Audio/video belongs in the iCloud vault (see docs/STORAGE.md)," >&2
    echo "not in git. Add large files to .gitignore if they should not be tracked." >&2
    exit 0
  fi
fi

exit 0
