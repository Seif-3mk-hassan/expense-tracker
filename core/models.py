from django.conf import settings
from django.db import models


class OwnedQuerySet(models.QuerySet):
    """Adds per-user scoping. Every data view must go through ``for_user``."""

    def for_user(self, user):
        return self.filter(owner=user)


class OwnedManager(models.Manager.from_queryset(OwnedQuerySet)):
    pass


class OwnedModel(models.Model):
    """Abstract base for anything owned by one user (US-03)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    objects = OwnedManager()

    class Meta:
        abstract = True
