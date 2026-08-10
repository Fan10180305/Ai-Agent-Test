#!/usr/bin/env python3
"""Stage tracked files for Composer dags bucket sync.

设计要点（B 方案：路径前缀白名单）
================================

提供 `--dry-run` 模式：仅打印将要 / 不会被同步的清单，不实际 staging，
便于在白名单变更前本地验证。
"""

import argparse
import os
import shutil
import subprocess
import sys

INCLUDED_PREFIXES = (
    "dags/",
    "data-agent/",
    "qpon-bigdata-knowledge/",

)

EXCLUDED_FILENAMES = {
    "cloudbuild.yaml",
    "sync_script.py",
    ".DS_Store",
}

_PREVIEW_LIMIT = 20


def run_command(command, cwd=None):
    """Runs a shell command, prints output, and raises error on failure."""
    print(f"Executing: {' '.join(command)}")
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
        print(f"Stdout: {result.stdout.strip()}")
        print(f"Stderr: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {' '.join(command)}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        print(f"Stderr: {e.stderr.strip()}", file=sys.stderr)
        print(f"Stdout: {e.stdout.strip()}", file=sys.stderr)
        raise


def get_all_tracked_files():
    """Gets a list of all files tracked by Git in the current HEAD commit."""
    print("Getting list of all tracked files in HEAD...")
    output = run_command(['git', 'ls-tree', '-r', '--name-only', 'HEAD'])
    return [line for line in output.splitlines() if line]


def classify_file(filepath):
    """Decide how a tracked file should be handled.

    Returns one of: 'include', 'exclude_filename', 'exclude_non_dag'.
    """
    if os.path.basename(filepath) in EXCLUDED_FILENAMES:
        return "exclude_filename"
    if not any(filepath.startswith(prefix) for prefix in INCLUDED_PREFIXES):
        return "exclude_non_dag"
    return "include"


def stage_file(filepath):
    """Copies a file from /workspace to /workspace/staging, maintaining structure."""
    source_path = os.path.join('/workspace', filepath)
    if not os.path.exists(source_path):
        print(f"Skipping staging: {source_path} (does not exist)")
        return

    staging_base_dir = '/workspace/staging'
    staging_target_path = os.path.join(staging_base_dir, filepath)

    staging_target_dir = os.path.dirname(staging_target_path)
    try:
        os.makedirs(staging_target_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating staging directory {staging_target_dir}: {e}", file=sys.stderr)
        return

    try:
        shutil.copyfile(source_path, staging_target_path)
    except Exception as e:
        print(f"Error staging file {source_path} to {staging_target_path}: {e}", file=sys.stderr)


def _print_preview(label, items):
    print(f"\n{label} ({len(items)} files):")
    for item in items[:_PREVIEW_LIMIT]:
        print(f"  - {item}")
    remaining = len(items) - _PREVIEW_LIMIT
    if remaining > 0:
        print(f"  ... and {remaining} more")


def main():
    parser = argparse.ArgumentParser(description='Stage Airflow DAG files for GCS sync.')
    parser.add_argument(
        '--gcs-destination',
        required=False,
        default='',
        help='Base GCS destination path (for context only; staging is local).'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only print include/exclude decisions; do not modify the staging directory.'
    )
    args = parser.parse_args()

    if args.gcs_destination:
        print(f"GCS Destination Base (for context): {args.gcs_destination}")

    workspace = '/workspace' if os.path.isdir('/workspace') else os.getcwd()
    os.chdir(workspace)
    print(f"Current working directory: {os.getcwd()}")

    all_tracked_files = get_all_tracked_files()

    included = []
    excluded_by_filename = []
    excluded_non_dag = []
    for filepath in all_tracked_files:
        verdict = classify_file(filepath)
        if verdict == "include":
            included.append(filepath)
        elif verdict == "exclude_filename":
            excluded_by_filename.append(filepath)
        else:
            excluded_non_dag.append(filepath)

    print(f"\nTotal tracked files: {len(all_tracked_files)}")
    print(f"  INCLUDED_PREFIXES = {INCLUDED_PREFIXES}")
    print(f"  EXCLUDED_FILENAMES = {sorted(EXCLUDED_FILENAMES)}")
    _print_preview("INCLUDED (will be synced to dags bucket)", included)
    _print_preview("EXCLUDED by filename", excluded_by_filename)
    _print_preview("EXCLUDED by non-DAG prefix", excluded_non_dag)

    if args.dry_run:
        print("\n[dry-run] Skipping staging directory mutations.")
        sys.exit(0)

    staging_base_dir = '/workspace/staging'
    if os.path.exists(staging_base_dir):
        print(f"\nClearing existing staging directory: {staging_base_dir}")
        shutil.rmtree(staging_base_dir)
    try:
        os.makedirs(staging_base_dir, exist_ok=True)
    except Exception as e:
        print(f"Fatal Error: Could not create staging directory {staging_base_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    if not included:
        print("No files matched INCLUDED_PREFIXES. Staging directory will be empty.")
        sys.exit(0)

    print(f"\nStaging {len(included)} files...")
    for filepath in included:
        stage_file(filepath)

    print(
        "File staging complete. Next Cloud Build step should run "
        "'gsutil rsync -r /workspace/staging gs://<dags-bucket>' to sync."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
