#!/usr/bin/env bash
# Tools/restore_z4d.sh
# Restore script for Domoticz + Domoticz-Zigbee plugin data created by Tools/backup_z4d.sh
# Simplified plugin handling:
#  - Provide --plugin-target-path which is the plugin root (plugin folder). The script will deduce Data and Conf subfolders.
#  - Backward compatibility: if you provide --plugin-data-target (Data dir) we'll deduce plugin root as parent.
#
# Usage:
#   ./Tools/restore_z4d.sh --archive /path/to/domoticz-backup-YYYY-MM-DD_HH-MM.tar.gz \
#       --plugin-target-path /opt/domoticz/userdata/plugins/Domoticz-Zigbee \
#       [--domoticz-db-target /opt/domoticz/userdata/domoticz.db] [--stop-service] [--dry-run]
#
# Backward-compatibility:
#  - --plugin-data-target (old) is accepted; parent dir is used as plugin root if given.
#
# Copyright (c) 2023-2025 ZigbeeForDomoticz contributors
# SPDX-License-Identifier: MIT
# Repository: https://github.com/zigbeefordomoticz/Domoticz-Zigbee

set -euo pipefail

DRY_RUN=false
STOP_SERVICE=false
YES=false
LIST_ONLY=false

ARCHIVE=""
BACKUP_DIR=""
DOMOTICZ_DB_TARGETS=()   # can be provided multiple times
PLUGIN_TARGET=""          # plugin root target (new)
PLUGIN_DATA_TARGET_LEGACY=""  # legacy Data dir target (old)
TMPDIR=""
PREVIFS="$IFS"

DOMOTICZ_SERVICE_NAMES=(
  "domoticz.service"
  "domoticz"
)

timestamp() { date -u +"%Y-%m-%d_%H-%M"; }
ts="$(timestamp)"

show_help() {
  cat <<EOF
Restore Domoticz + plugin data (reverse of Tools/backup_z4d.sh)

Options:
  --archive PATH             Path to backup tar.gz archive created by backup_z4d.sh
  --backup-dir PATH          Path to an already-extracted backup directory
  --domoticz-db-target PATH  Destination path(s) to restore domoticz DB into (can be specified multiple times).
  --plugin-target-path PATH  Destination plugin root directory (where plugin folder lives). The script will use
                             <plugin-root>/Data and <plugin-root>/Conf for restoring Data/Conf files.
  --plugin-data-target PATH  (legacy) Destination plugin Data directory; parent will be used as plugin root.
  --stop-service             Stop domoticz service before restore and start it afterwards.
  --dry-run                  Print actions but don't perform filesystem changes.
  --list                     List files contained in the archive or backup dir and exit.
  --yes                      Do not prompt for confirmation (use with care).
  -h, --help                 Show this help.

One of --archive or --backup-dir is required.
EOF
}

# Simple arg parsing
while [[ $# -gt 0 ]]; do
  case "$1" in
    --archive)
      shift
      ARCHIVE="$1"
      ;;
    --backup-dir)
      shift
      BACKUP_DIR="$1"
      ;;
    --domoticz-db-target)
      shift
      DOMOTICZ_DB_TARGETS+=("$1")
      ;;
    --plugin-target-path)
      shift
      PLUGIN_TARGET="$1"
      ;;
    --plugin-data-target)
      shift
      PLUGIN_DATA_TARGET_LEGACY="$1"
      ;;
    --stop-service)
      STOP_SERVICE=true
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    --yes)
      YES=true
      ;;
    --list)
      LIST_ONLY=true
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

run() {
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] $*"
  else
    eval "$@"
  fi
}

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

require_one_of_archive_or_dir() {
  if [ -z "$ARCHIVE" ] && [ -z "$BACKUP_DIR" ]; then
    echo "ERROR: you must provide either --archive or --backup-dir" >&2
    exit 2
  fi
}

ensure_tmpdir() {
  if [ -z "${TMPDIR:-}" ]; then
    TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/domoticz-restore.XXXXXX")"
    trap 'if [ -n "${TMPDIR:-}" ]; then rm -rf "$TMPDIR"; fi' EXIT
  fi
}

list_archive_contents() {
  if [ -n "$ARCHIVE" ]; then
    echo "Contents of archive: $ARCHIVE"
    tar -tzf "$ARCHIVE"
  else
    echo "Contents of backup directory: $BACKUP_DIR"
    find "$BACKUP_DIR" -type f -print
  fi
}

extract_archive() {
  ensure_tmpdir
  echo "Extracting archive to: $TMPDIR/extracted"
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] mkdir -p '$TMPDIR/extracted' && tar -xzf '$ARCHIVE' -C '$TMPDIR/extracted'"
    return 0
  fi
  mkdir -p "$TMPDIR/extracted"
  tar -xzf "$ARCHIVE" -C "$TMPDIR/extracted"
  BACKUP_DIR="$TMPDIR/extracted"
}

read_backup_info_targets() {
  local info_file="${BACKUP_DIR}/backup-info.txt"
  if [ -f "$info_file" ]; then
    # attempt to extract Domoticz DB paths
    local domlines
    domlines="$(awk '/^Domoticz DBs:/{flag=1;next}/^Plugin/{flag=0}flag{print}' "$info_file" 2>/dev/null || true)"
    if [ -n "$domlines" ] && [ "${#DOMOTICZ_DB_TARGETS[@]}" -eq 0 ]; then
      while IFS= read -r l; do
        l_trimmed="${l# - }"
        if [ -n "$l_trimmed" ]; then
          DOMOTICZ_DB_TARGETS+=("$l_trimmed")
        fi
      done <<< "$domlines"
    fi

    # try to find a plugin root entry
    if [ -z "$PLUGIN_TARGET" ]; then
      local pd="$(awk '/^Plugin roots:/{flag=1;next}/^Full plugin copy:/{flag=0}flag{print}' "$info_file" 2>/dev/null || true)"
      if [ -n "$pd" ]; then
        while IFS= read -r l; do
          l_trimmed="${l# - }"
          if [ -n "$l_trimmed" ]; then
            # pick the first one that exists on this host
            if [ -d "$l_trimmed" ]; then
              PLUGIN_TARGET="$l_trimmed"
              break
            fi
          fi
        done <<< "$pd"
      fi
    fi
  fi
}

backup_existing_file() {
  local target="$1"
  if [ -e "$target" ]; then
    local bak="${target}.pre-restore-${ts}"
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] mv '$target' '$bak'"
    else
      mkdir -p "$(dirname "$bak")"
      mv "$target" "$bak"
      echo "Backed up existing: $target -> $bak"
    fi
  fi
}

restore_domoticz_dbs() {
  local found=()
  while IFS= read -r -d $'\0' f; do
    found+=("$f")
  done < <(find "$BACKUP_DIR" -maxdepth 2 -type f -iname 'domoticz.db' -print0 2>/dev/null || true)

  if [ "${#found[@]}" -eq 0 ]; then
    while IFS= read -r -d $'\0' f; do
      found+=("$f")
    done < <(find "$BACKUP_DIR" -maxdepth 3 -type f -iname 'domoticz*' -print0 2>/dev/null || true)
  fi

  if [ "${#found[@]}" -eq 0 ]; then
    echo "No Domoticz DB files found in backup at $BACKUP_DIR" >&2
    return 0
  fi

  if [ "${#DOMOTICZ_DB_TARGETS[@]}" -eq 0 ]; then
    echo "No --domoticz-db-target provided. Attempting to use paths from backup-info.txt..."
    read_backup_info_targets
  fi

  if [ "${#DOMOTICZ_DB_TARGETS[@]}" -eq 0 ]; then
    echo "No domoticz target path configured. Provide --domoticz-db-target or update backup-info.txt." >&2
    return 2
  fi

  for src in "${found[@]}"; do
    src_basename="$(basename "$src")"
    chosen_target=""
    for t in "${DOMOTICZ_DB_TARGETS[@]}"; do
      if [ "$(basename "$t")" = "$src_basename" ]; then
        chosen_target="$t"
        break
      fi
    done
    if [ -z "$chosen_target" ]; then
      chosen_target="${DOMOTICZ_DB_TARGETS[0]}"
    fi

    echo "Restoring Domoticz DB: $src -> $chosen_target"
    backup_existing_file "$chosen_target"
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] cp --preserve=mode,timestamps '$src' '$chosen_target'"
    else
      mkdir -p "$(dirname "$chosen_target")"
      cp --preserve=mode,timestamps "$src" "$chosen_target"
      echo "Restored: $chosen_target"
      if command -v sqlite3 >/dev/null 2>&1; then
        if sqlite3 "$chosen_target" "PRAGMA integrity_check;" | grep -q '^ok$'; then
          echo "Integrity check: OK"
        else
          echo "WARNING: integrity_check failed for $chosen_target" >&2
        fi
      fi
    fi
  done
}

restore_plugin_files() {
  # Determine plugin root target:
  # Preference order: --plugin-target-path, legacy --plugin-data-target (parent), backup-info
  if [ -z "$PLUGIN_TARGET" ]; then
    if [ -n "$PLUGIN_DATA_TARGET_LEGACY" ]; then
      # deduce plugin root as parent of Data dir
      if [ -d "$PLUGIN_DATA_TARGET_LEGACY" ]; then
        PLUGIN_TARGET="$(dirname "$PLUGIN_DATA_TARGET_LEGACY")"
      else
        echo "Legacy --plugin-data-target not found: $PLUGIN_DATA_TARGET_LEGACY" >&2
      fi
    else
      read_backup_info_targets
    fi
  fi

  if [ -z "$PLUGIN_TARGET" ]; then
    echo "No plugin target configured. Provide --plugin-target-path or --plugin-data-target (legacy)." >&2
    return 2
  fi

  local data_target="${PLUGIN_TARGET%/}/Data"
  local conf_target="${PLUGIN_TARGET%/}/Conf"

  echo "Plugin restore target deduced as plugin root: $PLUGIN_TARGET"
  echo "Plugin Data target: $data_target"
  echo "Plugin Conf target: $conf_target"

  # Discover backed-up plugin layouts
  local plugin_dirs=( )
  while IFS= read -r -d $'\0' d; do
    plugin_dirs+=("$d")
  done < <(find "$BACKUP_DIR" -maxdepth 3 -type d \( -iname 'plugin-dir-*' -o -iname 'plugin-key-files-*' \) -print0 2>/dev/null || true)

  local plugin_files=( )
  while IFS= read -r -d $'\0' f; do
    plugin_files+=("$f")
  done < <(find "$BACKUP_DIR" -maxdepth 2 -type f -iname 'plugin-file-*' -print0 2>/dev/null || true)

  # fallback detection: any directory containing known key files
  if [ "${#plugin_dirs[@]}" -eq 0 ]; then
    while IFS= read -r -d $'\0' candidate; do
      plugin_dirs+=("$(dirname "$candidate")")
    done < <(find "$BACKUP_DIR" -type f \( -iname 'Coordinator-*.backup' -o -iname 'zigpy_persistent_*.db' -o -iname 'DeviceList-*.txt' -o -iname 'GroupsList-*.txt' -o -iname 'PluginConf-*.json' \) -print0 2>/dev/null || true)

    if [ "${#plugin_dirs[@]}" -gt 0 ]; then
      IFS=$'\n' plugin_dirs=($(printf "%s\n" "${plugin_dirs[@]}" | awk '!seen[$0]++'))
      IFS="$PREVIFS"
    fi
  fi

  # Process found plugin directories
  for pd in "${plugin_dirs[@]:-}"; do
    bn="$(basename "$pd")"
    if [[ "$bn" == plugin-dir-* ]]; then
      echo "Restoring full plugin root from backup: $pd -> $PLUGIN_TARGET"
      if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] rsync -a --delete '$pd' '$PLUGIN_TARGET'"
      else
        if [ -d "$PLUGIN_TARGET" ]; then
          backup_existing_file "$PLUGIN_TARGET"
          rm -rf "$PLUGIN_TARGET"
        fi
        mkdir -p "$(dirname "$PLUGIN_TARGET")"
        if command -v rsync >/dev/null 2>&1; then
          rsync -a --delete "$pd"/ "$PLUGIN_TARGET"/
        else
          cp -a "$pd" "$PLUGIN_TARGET"
        fi
        echo "Restored plugin root to $PLUGIN_TARGET"
      fi
    elif [[ "$bn" == plugin-key-files-* ]]; then
      echo "Restoring key plugin files from: $pd -> $PLUGIN_TARGET"
      if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] find '$pd' -type f -print"
      else
        while IFS= read -r -d $'\0' f; do
          rel="${f#$pd/}"
          dest="$PLUGIN_TARGET/$rel"
          mkdir -p "$(dirname "$dest")"
          backup_existing_file "$dest"
          cp --preserve=mode,timestamps "$f" "$dest"
          echo "Copied: $f -> $dest"
        done < <(find "$pd" -type f -print0 2>/dev/null || true)
      fi
    else
      echo "Restoring directory $pd -> $PLUGIN_TARGET (fallback)"
      if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] rsync -a '$pd' '$PLUGIN_TARGET'"
      else
        mkdir -p "$PLUGIN_TARGET"
        if command -v rsync >/dev/null 2>&1; then
          rsync -a "$pd"/ "$PLUGIN_TARGET"/
        else
          cp -a "$pd"/* "$PLUGIN_TARGET"/ 2>/dev/null || true
        fi
      fi
    fi
  done

  # Restore plugin-file-* entries (single files)
  for pf in "${plugin_files[@]:-}"; do
    name="$(basename "$pf")"
    orig="${name#plugin-file-}"
    # decide dest: if file looks like DeviceList-*.txt or PluginConf-*.json etc, place under Data or Conf
    dest=""
    case "$orig" in
      DeviceList-*.txt|GroupsList-*.txt|Coordinator-*.backup|zigpy_persistent_*.db)
        dest="$data_target/$orig"
        ;;
      PluginConf-*.json)
        dest="$conf_target/$orig"
        ;;
      *)
        dest="$PLUGIN_TARGET/$orig"
        ;;
    esac
    echo "Restoring single plugin file: $pf -> $dest"
    backup_existing_file "$dest"
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] cp --preserve=mode,timestamps '$pf' '$dest'"
    else
      mkdir -p "$(dirname "$dest")"
      cp --preserve=mode,timestamps "$pf" "$dest"
    fi
  done

  echo "Plugin restore complete."
}

confirm_proceed() {
  if [ "$YES" = true ] || [ "$DRY_RUN" = true ]; then
    return 0
  fi
  echo "About to restore using:"
  echo "  Backup dir: $BACKUP_DIR"
  [ -n "$ARCHIVE" ] && echo "  Archive: $ARCHIVE"
  [ "${#DOMOTICZ_DB_TARGETS[@]}" -gt 0 ] && printf "  Domoticz DB targets: %s\n" "${DOMOTICZ_DB_TARGETS[*]}"
  [ -n "$PLUGIN_TARGET" ] && printf "  Plugin root target: %s\n" "$PLUGIN_TARGET"
  read -rp "Proceed? (y/N): " ans
  case "$ans" in
    y|Y|yes|YES) return 0 ;;
    *) echo "Aborted."; exit 1 ;;
  esac
}

main() {
  require_one_of_archive_or_dir

  if [ -n "$ARCHIVE" ] && [ -n "$BACKUP_DIR" ]; then
    echo "Both --archive and --backup-dir provided; using provided --backup-dir and ignoring --archive"
  fi

  if [ -n "$ARCHIVE" ] && [ -z "$BACKUP_DIR" ]; then
    if [ ! -f "$ARCHIVE" ]; then
      echo "Archive not found: $ARCHIVE" >&2
      exit 2
    fi
    if [ "$LIST_ONLY" = true ]; then
      list_archive_contents
      exit 0
    fi
    extract_archive
  fi

  if [ -n "$BACKUP_DIR" ] && [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory not found: $BACKUP_DIR" >&2
    exit 2
  fi

  if [ "$LIST_ONLY" = true ]; then
    list_archive_contents
    exit 0
  fi

  read_backup_info_targets

  confirm_proceed

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

  restore_domoticz_dbs
  restore_plugin_files

  if [ "$STOP_SERVICE" = true ]; then
    SERVICE_NAME="${SERVICE_NAME:-$(find_domoticz_service || true)}"
    echo "Starting service $SERVICE_NAME ..."
    if [ "$DRY_RUN" = true ]; then
      echo "[DRY-RUN] systemctl start $SERVICE_NAME"
    else
      sudo systemctl start "$SERVICE_NAME" || echo "Warning: failed to start service $SERVICE_NAME" >&2
    fi
  fi

  echo "Restore finished."
}

main "$@"
