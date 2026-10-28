"""Provision the two supported roles without overwriting existing passwords."""

import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create role accounts. --demo is development-only; production uses environment-supplied passwords."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        demo = options["demo"]
        if demo and not settings.DEBUG:
            raise CommandError("Demo accounts are disabled outside development.")
        specs = [
            (
                "policymaker",
                "National policymaker",
                "APASA_POLICYMAKER_PASSWORD",
                "ApasaPolicyDemo!2026",
            ),
            (
                "district_officer",
                "District agriculture officer",
                "APASA_DISTRICT_PASSWORD",
                "ApasaDistrictDemo!2026",
            ),
        ]
        # Validate both requirements before changing anything.
        for username, role, variable, default in specs:
            if not get_user_model().objects.filter(username=username).exists() and not (
                demo or os.environ.get(variable)
            ):
                raise CommandError(
                    f"Set {variable} securely before provisioning {username}."
                )
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        for username, role, variable, default in specs:
            group, _ = Group.objects.get_or_create(name=role)
            user, created = get_user_model().objects.get_or_create(username=username)
            if created:
                try:
                    password = default if demo else os.environ[variable]
                    validate_password(password, user)
                except ValidationError as exc:
                    user.delete()
                    raise CommandError("; ".join(exc.messages))
                user.set_password(password)
                user.save()
            if not demo and user.check_password(default):
                raise CommandError(
                    f"{username} still uses a demo password. Run changepassword before production."
                )
            user.groups.add(group)
            self.stdout.write(
                f'{username}: {"created" if created else "preserved"}; {role}'
            )
