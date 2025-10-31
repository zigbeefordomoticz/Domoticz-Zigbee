#!/usr/bin/env bash
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

# Tools/backup_z4d.sh
# Backup script for Domoticz and Domoticz-Zigbee plugin data.
# Simplified plugin handling:
#  - Provide --plugin-target-path <plugin-root> (e.g. /opt/domoticz/userdata/plugins/Domoticz-Zigbee)
#  - The script will deduce Data and Conf subfolders:
#      Data: <plugin-root>/Data
#      Conf: <plugin-root>/Conf
#  - It will back up key files from Data and PluginConf-*.json from Conf, or use --full-plugin-copy to copy the full plugin folder.
#
# Usage:
#   ./Tools/backup_z4d.sh --domoticz-db /path/to/domoticz.db --plugin-target-path /path/to/plugin-root \
#       [--dest DIR] [--stop-service] [--retention DAYS] [--dry-run] [--full-plugin-copy]
#
# Backward-compatibility:
#  - The older --plugin-data argument is accepted (interpreted as Data directory); if you provide --plugin-data,
#    the script will try to infer plugin-root as the parent of the Data directory.
#
# Copyright (c) 2023-2025 ZigbeeForDomoticz contributors
# SPDX-License-Identifier: MIT
# Repository: https://github.com/zigbeefordomoticz/Domoticz-Zigbee

set -euo pipefail

# Defaults
DEST="${HOME}/backups/domoticz"
RETENTION_DAYS=14
STOP_SERVICE=false
DRY_RUN=false
FULL_PLUGIN_COPY=false
DOMOTICZ_DB_ARGS=()
PLUGIN_TARGET_ARGS=()   # plugin root(s)
PLUGIN_DATA_ARGS=()     # legacy: Data dir(s) provided directly

COMMON_DOMOTICZ_PATHS=(
  "/home/pi/domoticz/domoticz.db"
  "/opt/domoticz/domoticz.db"
  "/var/lib/domoticz/domoticz.db"
  "/home/domoticz/domoticz.db"
  "${HOME}/domoticz/domoticz.db"
)

COMMON_PLUGIN_DIRS=(
  "/home/pi/domoticz/plugins/Domoticz-Zigbee"
  "/opt/domoticz/plugins/Domoticz-Zigbee"
  "${HOME}/domoticz/plugins/Domoticz-Zigbee"
  "${HOME}/.local/share/domoticz/plugins/Domoticz-Zigbee"
)

DOMOTICZ_SERVICE_NAMES=(
  "domoticz.service"
  "domoticz"
)

show_help() {
  cat <<EOF
Backup Domoticz + Domoticz-Zigbee plugin data script.

Options:
  --domoticz-db PATH         Path to domoticz.db (can be specified multiple times).
  --plugin-target-path PATH  Path to plugin root directory (can be specified multiple times).
                             The script will use <plugin-root>/Data and <plugin-root>/Conf automatically.
  --plugin-data PATH         (legacy) Path to the plugin Data directory; parent is used to deduce plugin root.
  --full-plugin-copy         Copy the entire plugin root instead of only key files.
  --dest DIR                 Destination directory for backups (default: ${DEST}).
  --stop-service             Stop domoticz service during backup for guaranteed consistency.
  --retention DAYS           Delete backups older than DAYS (default: ${RETENTION_DAYS}).
  --dry-run                  Print actions but don't perform filesystem changes.
  -h, --help                 Show this help.
EOF
}

# parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --domoticz-db)
      shift
      DOMOTICZ_DB_ARGS+=("$1")
      ;;
    --plugin-target-path)
      shift
      PLUGIN_TARGET_ARGS+=("$1")
      ;;
    --plugin-data)
      shift
      PLUGIN_DATA_ARGS+=("$1")
      ;;
    --plugin-db) # kept as alias historically
      shift
      PLUGIN_DATA_ARGS+=("$1")
      ;;
    --full-plugin-copy)
      FULL_PLUGIN_COPY=true
      ;;
    --dest)
      shift
      DEST="$1"
      ;;
    --stop-service)
      STOP_SERVICE=true
      ;;
    --retention)
      shift
      RETENTION_DAYS="$1"
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help
      exit 2
      ;;
  esac
  shift
done

run_or_echo() {
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] $*"
  else
    eval "$@"
  fi
}

# Timestamp format: YYYY-MM-DD_HH-MM (UTC)
timestamp() { date -u +"%Y-%m-%d_%H-%M"; }

# Resolve domoticz DB paths (prefer explicit args, otherwise probe common paths)
DOMOTICZ_DB_PATHS=()
if [ "${#DOMOTICZ_DB_ARGS[@]}" -gt 0 ]; then
  for p in "${DOMOTICZ_DB_ARGS[@]}"; do
    if [ -f "$p" ]; then
      DOMOTICZ_DB_PATHS+=("$p")
    else
      echo "Warning: specified Domoticz DB not found: $p" >&2
    fi
  done
else
  for p in "${COMMON_DOMOTICZ_PATHS[@]}"; do
    if [ -f "$p" ]; then
      DOMOTICZ_DB_PATHS+=("$p")
    fi
  done
fi

# Resolve plugin target(s):
# - New: PLUGIN_TARGET_ARGS are plugin roots
# - Legacy: PLUGIN_DATA_ARGS are Data directories; parent directory is used as plugin root
PLUGIN_ROOTS=()
if [ "${#PLUGIN_TARGET_ARGS[@]}" -gt 0 ]; then
  for p in "${PLUGIN_TARGET_ARGS[@]}"; do
    if [ -d "$p" ]; then
      PLUGIN_ROOTS+=("$p")
    else
      echo "Warning: specified plugin target not found: $p" >&2
    fi
  done
fi

if [ "${#PLUGIN_DATA_ARGS[@]}" -gt 0 ]; then
  for d in "${PLUGIN_DATA_ARGS[@]}"; do
    if [ -d "$d" ]; then
      # assume plugin root is parent of Data dir
      parent="$(dirname "$d")"
      PLUGIN_ROOTS+=("$parent")
    else
      echo "Warning: specified plugin data path not found: $d" >&2
    fi
  done
fi

# If none provided, fall back to common plugin dirs' parents if they exist
if [ "${#PLUGIN_ROOTS[@]}" -eq 0 ]; then
  for p in "${COMMON_PLUGIN_DIRS[@]}"; do
    if [ -d "$p" ]; then
      PLUGIN_ROOTS+=("$p")
    fi
  done
fi

# Helper to try to detect a domoticz service name
find_domoticz_service() {
  for s in "${DOMOTICZ_SERVICE_NAMES[@]}"; do
    if systemctl list-units --full -a --type=service 2>/dev/null | grep -q "^${s}"; then
      echo "$s"
      return 0
    fi
  done
  echo "${DOMOTICZ_SERVICE_NAMES[0]}"
  return 1
}

# sqlite online backup helper
sqlite_backup() {
  local src="$1"
  local dest="$2"
  if command -v sqlite3 >/dev/null 2>&1; then
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] sqlite3 '$src' \".backup '$dest'\""
    else
      sqlite3 "$src" ".backup '$dest'"
    fi
  else
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] cp --preserve=mode,timestamps '$src' '$dest'"
    else
      cp --preserve=mode,timestamps "$src" "$dest"
    fi
  fi
}

# copy directory helper (prefer rsync)
copy_dir() {
  local src="$1"
  local dest="$2"
  if command -v rsync >/dev/null 2>&1; then
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] rsync -a --delete '$src' '$dest'"
    else
      mkdir -p "$dest"
      rsync -a --delete "$src"/ "$dest"/
    fi
  else
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] cp -a '$src' '$dest'"
    else
      rm -rf "$dest"
      cp -a "$src" "$dest"
    fi
  fi
}

# copy only key files from Data and PluginConf from Conf
backup_plugin_key_files() {
  local plugin_root="$1"
  local dest_dir="$2"

  local data_dir="${plugin_root%/}/Data"
  local conf_dir="${plugin_root%/}/Conf"

  # patterns to search in Data (and deeper) and in Conf
  local -a patterns=( \
    -iname 'Coordinator-*.backup' \
    -o -iname 'DeviceList-*.txt' \
    -o -iname 'GroupsList-*.txt' \
    -o -iname 'zigpy_persistent_*.db' \
  )

  mapfile -t found_files < <(find "$data_dir" -maxdepth 4 -type f \( "${patterns[@]}" \) -print 2>/dev/null || true)

  # PluginConf in Conf
  if [ -d "$conf_dir" ]; then
    while IFS= read -r -d $'\0' f; do
      found_files+=("$f")
    done < <(find "$conf_dir" -maxdepth 2 -type f -iname 'PluginConf-*.json' -print0 2>/dev/null || true)
  fi

  if [ "${#found_files[@]}" -eq 0 ]; then
    echo "No key plugin files found in plugin root: $plugin_root"
    return 0
  fi

  for f in "${found_files[@]}"; do
    rel="${f#${plugin_root%/}/}"     # relative path under plugin root
    target_dir="$(dirname "$dest_dir/$rel")"
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] mkdir -p '$target_dir' && cp --preserve=mode,timestamps '$f' '$target_dir/'"
    else
      mkdir -p "$target_dir"
      cp --preserve=mode,timestamps "$f" "$target_dir/"
    fi
    echo "Copied key file: $f -> $target_dir/"
  done
}

# Basic validations & setup
mkdir -p "$DEST"
TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/domoticz-backup.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT

if [ "${#DOMOTICZ_DB_PATHS[@]}" -eq 0 ] && [ "${#PLUGIN_ROOTS[@]}" -eq 0 ]; then
  echo "No Domoticz DB or plugin root found to backup. Provide --domoticz-db or --plugin-target-path." >&2
  exit 2
fi

echo "Backup destination: $DEST"
echo "Retention (days): $RETENTION_DAYS"
echo "Stop service: $STOP_SERVICE"
echo "Full plugin copy: $FULL_PLUGIN_COPY"
echo "Domoticz DB(s) found: ${DOMOTICZ_DB_PATHS[*]:-None}"
echo "Plugin root(s) found: ${PLUGIN_ROOTS[*]:-None}"

# Optionally stop domoticz for a clean snapshot
if [ "$STOP_SERVICE" = true ]; then
  SERVICE_NAME="$(find_domoticz_service || true)"
  echo "Stopping service $SERVICE_NAME ..."
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] systemctl stop $SERVICE_NAME"
  else
    sudo systemctl stop "$SERVICE_NAME" || echo "Warning: failed to stop service $SERVICE_NAME" >&2
    sleep 1
  fi
fi

BACKUP_TS="$(timestamp)"
BACKUP_DIR="${TMPDIR}/backup-${BACKUP_TS}"
mkdir -p "$BACKUP_DIR"

# Backup domoticz DBs (use sqlite .backup)
for db in "${DOMOTICZ_DB_PATHS[@]}"; do
  base="$(basename "$db")"
  dest="${BACKUP_DIR}/${base}"
  echo "Backing up Domoticz DB: $db -> $dest"
  sqlite_backup "$db" "$dest"
done

# Backup plugin roots
for root in "${PLUGIN_ROOTS[@]}"; do
  bn="$(basename "$root")"
  if [ "$FULL_PLUGIN_COPY" = true ]; then
    dest="${BACKUP_DIR}/plugin-dir-${bn}"
    echo "Full plugin root copy: $root -> $dest"
    copy_dir "$root" "$dest"
  else
    dest="${BACKUP_DIR}/plugin-key-files-${bn}"
    echo "Backing up key plugin files from: $root -> $dest"
    backup_plugin_key_files "$root" "$dest"
  fi
done

# Create metadata file
cat > "${BACKUP_DIR}/backup-info.txt" <<EOF
Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Host: $(hostname)
User: $(whoami)
Domoticz DBs:
$(for p in "${DOMOTICZ_DB_PATHS[@]:-}"; do echo " - $p"; done)
Plugin roots:
$(for p in "${PLUGIN_ROOTS[@]:-}"; do echo " - $p"; done)
Full plugin copy: ${FULL_PLUGIN_COPY}
Key plugin file patterns copied:
 - Coordinator-*.backup
 - DeviceList-*.txt
 - GroupsList-*.txt
 - zigpy_persistent_*.db
 - Conf/PluginConf-*.json
EOF

# Archive & compress
ARCHIVE_NAME="domoticz-backup-${BACKUP_TS}.tar.gz"
ARCHIVE_PATH="${DEST}/${ARCHIVE_NAME}"
echo "Creating archive: $ARCHIVE_PATH"
if [ "$DRY_RUN" = true ]; then
  echo "[DRY-RUN] tar -czf '$ARCHIVE_PATH' -C '$BACKUP_DIR' .'"
else
  tar -czf "$ARCHIVE_PATH" -C "$BACKUP_DIR" .
  echo "Backup created: $ARCHIVE_PATH"
fi

# Start service again
if [ "$STOP_SERVICE" = true ]; then
  SERVICE_NAME="${SERVICE_NAME:-$(find_domoticz_service || true)}"
  echo "Starting service $SERVICE_NAME ..."
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] systemctl start $SERVICE_NAME"
  else
    sudo systemctl start "$SERVICE_NAME" || echo "Warning: failed to start service $SERVICE_NAME" >&2
  fi
fi

# Prune old backups
echo "Pruning backups older than ${RETENTION_DAYS} days in ${DEST} ..."
if [ "$DRY_RUN" = true ]; then
  echo "[DRY-RUN] find '$DEST' -type f -name 'domoticz-backup-*.tar.gz' -mtime +${RETENTION_DAYS} -print -delete"
else
  find "$DEST" -type f -name 'domoticz-backup-*.tar.gz' -mtime +"${RETENTION_DAYS}" -print -delete || true
fi

echo "Done."
exit 0
