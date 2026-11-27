import os
import shutil
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings

from documents.models import UploadedDocument
from projects.models import Project


class Command(BaseCommand):
    help = (
        "Delete orphaned PDF files and empty directories in the media directory "
        "that no longer have a corresponding UploadedDocument record (e.g. from "
        "previously deleted projects). Scans media/uploads/projects/ for files "
        "without a database record and removes them, then removes any now-empty "
        "project directories."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List orphaned files and empty directories without deleting them.",
        )
        parser.add_argument(
            "--project-id",
            type=str,
            help="Only clean up orphaned files for a specific project ID.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        project_id = options["project_id"]
        media_root = settings.MEDIA_ROOT

        # Gather all file paths that have a corresponding DB record.
        if project_id:
            docs = UploadedDocument._base_manager.filter(project_id=project_id)
            valid_files = {doc.file.name for doc in docs if doc.file}
            media_prefix = f"uploads/projects/{project_id}/"
        else:
            docs = UploadedDocument._base_manager.all()
            valid_files = {doc.file.name for doc in docs if doc.file}
            media_prefix = "uploads/projects/"

        # Full filesystem path to the media prefix directory.
        prefix_path = os.path.join(media_root, media_prefix.rstrip("/"))

        # List all files actually present in the media directory.
        orphaned = []
        try:
            dirs, files = default_storage.listdir(media_prefix)
        except FileNotFoundError:
            self.stdout.write(
                f"No media directory found at {media_prefix}. Nothing to clean."
            )
            return

        # Recursively collect files under media_prefix.
        all_files = set(files)
        all_dirs = set()
        for subdir in dirs:
            subdir_path = f"{media_prefix}{subdir}/"
            all_dirs.add(subdir_path.rstrip("/"))
            try:
                _, subfiles = default_storage.listdir(subdir_path)
                all_files.update(
                    f"{subdir_path}{f}" for f in subfiles
                )
            except (FileNotFoundError, NotADirectoryError):
                continue

        # Find files not referenced by any document record.
        for file_name in sorted(all_files):
            if file_name not in valid_files:
                orphaned.append(file_name)

        # Find directories that are now (or already) empty.
        empty_dirs = []
        for d in sorted(all_dirs, reverse=True):
            dir_path = os.path.join(media_root, d)
            if os.path.isdir(dir_path):
                try:
                    contents = os.listdir(dir_path)
                except OSError:
                    continue
                if not contents:
                    empty_dirs.append(d)

        if not orphaned and not empty_dirs:
            self.stdout.write("No orphaned files or empty directories found.")
            return

        if dry_run:
            if orphaned:
                self.stdout.write(
                    f"[dry-run] {len(orphaned)} orphaned file(s) would be deleted:"
                )
                for f in orphaned:
                    self.stdout.write(f"  {f}")
            if empty_dirs:
                self.stdout.write(
                    f"[dry-run] {len(empty_dirs)} empty directory(ies) would be removed:"
                )
                for d in empty_dirs:
                    self.stdout.write(f"  {d}/")
            return

        # Delete orphaned files.
        deleted = 0
        for f in orphaned:
            try:
                default_storage.delete(f)
                deleted += 1
                self.stdout.write(f"Deleted {f}")
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"Failed to delete {f}: {exc}")

        # Remove empty directories (deepest first so parent dirs become removable).
        removed_dirs = 0
        for d in sorted(empty_dirs, key=lambda x: x.count("/"), reverse=True):
            dir_path = os.path.join(media_root, d)
            try:
                if os.path.isdir(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    removed_dirs += 1
                    self.stdout.write(f"Removed directory {d}/")
            except OSError as exc:
                self.stderr.write(f"Failed to remove directory {d}: {exc}")

        # Also try removing the top-level prefix directory if it is now empty.
        if os.path.isdir(prefix_path) and not os.listdir(prefix_path):
            try:
                os.rmdir(prefix_path)
                removed_dirs += 1
                self.stdout.write(f"Removed directory {media_prefix.rstrip('/')}/")
            except OSError as exc:
                self.stderr.write(f"Failed to remove directory {media_prefix}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} orphaned file(s) and removed "
                f"{removed_dirs} empty directory(ies)."
            )
        )