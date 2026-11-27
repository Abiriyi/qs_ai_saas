from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.tenant import set_current_org, reset_current_org
from documents.enums import DocumentStatus
from documents.models import UploadedDocument


class Command(BaseCommand):
    help = (
        "Reset documents stuck in PROCESSING state back to PENDING so they can "
        "be re-queued for processing. A document is considered stuck when it has "
        "remained in PROCESSING for longer than the given threshold."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=10,
            help=(
                "Minutes a document must remain in PROCESSING before it is "
                "considered stuck and reset to PENDING. Default: 10."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List stuck documents without resetting them.",
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(minutes=minutes)

        stuck = (
            UploadedDocument._base_manager.filter(
                status=DocumentStatus.PROCESSING,
                updated_at__lt=cutoff,
            )
            .select_related("organization")
            .order_by("updated_at")
        )

        count = stuck.count()
        if count == 0:
            self.stdout.write(
                f"No documents stuck in PROCESSING for more than {minutes} minute(s)."
            )
            return

        if dry_run:
            self.stdout.write(
                f"[dry-run] {count} document(s) stuck in PROCESSING for > {minutes} min:"
            )
            for doc in stuck:
                self.stdout.write(
                    f"  {doc.id} | {doc.original_filename} | "
                    f"org={doc.organization_id} | stuck since {doc.updated_at}"
                )
            return

        reset_count = 0
        for doc in stuck:
            token = set_current_org(doc.organization)
            try:
                doc.status = DocumentStatus.PENDING
                doc.processing_error = ""
                doc.save(
                    update_fields=["status", "processing_error", "updated_at"]
                )
                reset_count += 1
                self.stdout.write(
                    f"Reset {doc.id} ({doc.original_filename}) -> PENDING"
                )
            finally:
                reset_current_org(token)

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset {reset_count} of {count} stuck document(s) to PENDING."
            )
        )