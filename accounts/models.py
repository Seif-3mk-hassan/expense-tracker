from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Profile(models.Model):
    """Per-user preferences (US-19). Role stays group-based, never self-edited."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    currency = models.CharField(max_length=3, default="EGP")
    month_start_day = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(28)]
    )

    def __str__(self):
        return f"Profile of {self.user}"


def get_profile(user):
    """Fetch or create the profile, so pre-existing users are covered too."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile
