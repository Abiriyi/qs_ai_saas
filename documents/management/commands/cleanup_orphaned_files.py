from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings

from documents.models import UploadedDocument
from projects.models import Project


class Command(BaseCommand):
    help = (
        "Delete orphaned PDF files in the media directory that no longer have "
        "a corresponding UploadedDocument record (e.g. from previously deleted "
        "projects). Scans media/uploads/projects/ for files without a database "
        "record and removes them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List orphaned files without deleting them.",
        )
        parser.add_argument(
            "--project-id",
            type=str,
            help="Only clean up orphaned files for a specific project ID.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        project_id = options["project_id"]

        # Gather all file paths that have a corresponding DB record.
        if project_id:
            docs = UploadedDocument._base_manager.filter(project_id=project_id)
            valid_files = {doc.file.name for doc in docs if doc.file}
            media_prefix = f"uploads/projects/{project_id}/"
        else:
            docs = UploadedDocument._base_manager.all()
            valid_files = {doc.file.name for doc in docs if doc.file}
            media_prefix = "uploads/projects/"

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
        for subdir in dirs:
            try:
                _, subfiles = default_storage.listdir(media_prefix + subdir)
                all_files.update(
                    f"{media_prefix}{subdir}/{f}" for f in subfiles
                )
            except (FileNotFoundError, NotADirectoryError):
                continue

        # Find files not referenced by any document record.
        for file_name in sorted(all_files):
            if file_name not in valid_files:
                orphaned.append(file_name)

        if not orphaned:
            self.stdout.write("No orphaned files found.")
            return

        if dry_run:
            self.stdout.write(
                f"[dry-run] {len(orphaned)} orphaned file(s) would be deleted:"
            )
            for f in orphaned:
                self.stdout.write(f"  {f}")
            return

        deleted = 0
        for f in orphaned:
            try:
                default_storage.delete(f)
                deleted += 1
                self.stdout.write(f"Deleted {f}")
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"Failed to delete {f}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} of {len(orphaned)} orphaned file(s)."
            )
        )