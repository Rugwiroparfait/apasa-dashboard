"""Explicit local diagnostics; never prints a key or a provider error body."""

from django.core.management.base import BaseCommand, CommandError
from planning.ai import local_status, check_access, generate, AIUnavailable


class Command(BaseCommand):
    help = "Show safe local AI status. --check-access reads model access; --generate explicitly sends one small generation request."

    def add_arguments(self, parser):
        parser.add_argument("--check-access", action="store_true")
        parser.add_argument("--generate", action="store_true")

    def handle(self, *args, **options):
        status = local_status()
        self.stdout.write(
            f"Provider: NVIDIA; credential: {'set' if status['configured'] else 'missing'}; binding: {status['binding_name'] or 'none'}; model: {status['model']}"
        )
        self.stdout.write(
            f"Local limits: {status['requests_per_minute']} requests/minute, {status['requests_per_day']} requests/24 hours, {status['max_output_tokens']} max output tokens."
        )
        try:
            if options["check_access"]:
                result = check_access()
                self.stdout.write(
                    f"Selected model visible: {result['model_available']}. {result['note']}"
                )
            if options["generate"]:
                text, metadata = generate(
                    "Reply with APASA connection OK only.",
                    "A user explicitly requested this small connection test; no project evidence is included.",
                )
                self.stdout.write(text)
                self.stdout.write(f"Reported usage: {metadata.get('usage',{})}")
        except AIUnavailable as exc:
            raise CommandError(str(exc))
