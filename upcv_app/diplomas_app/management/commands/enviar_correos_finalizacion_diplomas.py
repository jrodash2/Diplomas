from django.core.management.base import BaseCommand

from diplomas_app.notifications import send_completion_notifications_for_finished_courses


class Command(BaseCommand):
    help = "Envía correos de finalización pendientes del módulo de Diplomas."

    def handle(self, *args, **options):
        summary = send_completion_notifications_for_finished_courses()
        self.stdout.write(
            self.style.SUCCESS(
                "Correos de finalización procesados. "
                f"Enviados: {summary.get('sent', 0)} | "
                f"Omitidos: {summary.get('skipped', 0)} | "
                f"Errores: {summary.get('errors', 0)}"
            )
        )
        if summary.get("fatal_error"):
            self.stderr.write(
                self.style.WARNING(
                    "Se detectó un error fatal de SMTP (autenticación). "
                    "Revise la configuración de correo antes de reintentar."
                )
            )
