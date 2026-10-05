import csv
import os

from django.core.management.base import BaseCommand

from core.tenant import reset_current_org, set_current_org
from pricing.models import RateLibrary
from users.models import Organization


class Command(BaseCommand):

    help = "Import CSV rate library"

    def handle(self, *args, **kwargs):
        org = Organization.objects.first()
        if org is None:
            self.stderr.write("Create an organization before importing rates.")
            return

        tenant_token = set_current_org(org)

        candidate_paths = [
            os.path.join(os.getcwd(), "qs_ai_project", "rate_library.csv"),
            os.path.join(os.getcwd(), "engine", "rate_library.csv"),
        ]

        csv_path = next((path for path in candidate_paths if os.path.exists(path)), candidate_paths[0])

        try:
            with open(csv_path, newline="") as csvfile:
                reader = csv.DictReader(
                    row for row in csvfile
                    if row and not row.strip().startswith("#")
                )

                for row in reader:
                    if not row or not row.get("Element"):
                        continue

                    base_rate = row.get("BaseRate") or row.get("base_rate") or row.get("Rate")
                    if base_rate in (None, ""):
                        continue

                    RateLibrary.objects.create(
                        organization=org,
                        element=row.get("Element").strip(),
                        description=row.get("Description", ""),
                        unit=row.get("Unit").strip(),
                        location=(row.get("Location") or row.get("location") or "Kaduna").strip(),
                        base_rate=base_rate,
                        source="imported",
                        review_status="approved",
                        confidence_score=1.0,
                        is_active=True,
                    )
        finally:
            reset_current_org(tenant_token)

        self.stdout.write(
            self.style.SUCCESS(
                "Rate library imported successfully"
            )
        )