#!/usr/bin/env bash

# Installs Python requirements line-by-line, continuing past failures.
# Writes failures to failed_requirements.txt (in the same folder as the requirements file).

set -u

REQ_FILE="${1:-requirements.txt}"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "requirements file not found: $REQ_FILE" >&2
  exit 2
fi

REQ_DIR="$(cd "$(dirname "$REQ_FILE")" && pwd)"
FAILED_FILE="$REQ_DIR/failed_requirements.txt"

# Truncate failures log
: > "$FAILED_FILE"

process_file() {
  local file="$1"
  local base_dir
  base_dir="$(cd "$(dirname "$file")" && pwd)"

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    # Strip leading/trailing whitespace
    local line
    line="${raw_line#${raw_line%%[![:space:]]*}}"
    line="${line%${line##*[![:space:]]}}"

    # Skip blanks and comments
    [[ -z "$line" ]] && continue
    [[ "$line" == \#* ]] && continue

    # Support nested requirements: -r other.txt / --requirement other.txt
    if [[ "$line" == -r* ]] || [[ "$line" == --requirement* ]]; then
      local nested
      nested="${line#-r}"
      nested="${nested#--requirement}"
      nested="${nested#${nested%%[![:space:]]*}}"

      # Resolve relative to the current file
      if [[ "$nested" != /* ]]; then
        nested="$base_dir/$nested"
      fi

      if [[ -f "$nested" ]]; then
        echo "==> Processing nested requirements: $nested"
        process_file "$nested"
      else
        echo "FAILED (missing nested file): $line" | tee -a "$FAILED_FILE" >&2
      fi
      continue
    fi

    echo "==> Installing: $line"
    python -m pip install "$line"
    if [[ $? -ne 0 ]]; then
      echo "FAILED: $line" | tee -a "$FAILED_FILE" >&2
    fi
  done < "$file"
}

process_file "$REQ_FILE"

echo
if [[ -s "$FAILED_FILE" ]]; then
  echo "Done with failures. See: $FAILED_FILE"
  exit 1
else
  echo "Done. All requirements installed successfully."
fi
