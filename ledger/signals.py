from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DEFAULT_CATEGORIES, Category


@receiver(post_save, sender=get_user_model())
def seed_default_categories(sender, instance, created, **kwargs):
    """Every new user starts with the 5 default categories (US-04)."""
    if not created:
        return
    for name, icon, color in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            owner=instance, name=name, defaults={"icon": icon, "color": color}
        )
