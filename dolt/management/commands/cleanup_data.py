from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Status

class Command(BaseCommand):
    """Cleanup Database after migrations."""

    help = "Cleanup Database after migrations."

    def handle(self, *args, **kwargs):
        Status.objects.all().delete()
        ContentType.objects.all().delete()
        Permission.objects.all().delete()
