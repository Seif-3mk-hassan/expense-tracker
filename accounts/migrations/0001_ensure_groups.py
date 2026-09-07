"""Ensures the ``admin`` and ``user`` groups exist (US-02 roles)."""

from django.db import migrations


def ensure_groups(apps, _schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ("admin", "user"):
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(ensure_groups, migrations.RunPython.noop),
    ]
