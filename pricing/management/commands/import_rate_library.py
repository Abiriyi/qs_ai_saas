import csv
import os

from django.core.management.base import BaseCommand

from pricing.models import RateLibrary
from users.models import Organization


class Command(BaseCommand):

    help = "Import CSV rate library"

    def handle(self, *args, **kwargs):

        org = Organization.objects.first()

        path = os.path.join(
            os.getcwd(),
            "qs_ai_project",
            "rate_library.csv",
        )

        with open(path, newline="") as csvfile:

            reader = csv.DictReader(
                row for row in csvfile
                if not row.startswith("#")
            )

            for row in reader:

                RateLibrary.objects.create(
                    organization=org,
                    element=row["Element"],
                    unit=row["Unit"],
                    location=row["Location"],
                    base_rate=row["BaseRate"],
                    source="csv",
                    is_verified=True,
                    year=int(row["Year"]),
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Rate library imported successfully"
            )
        )