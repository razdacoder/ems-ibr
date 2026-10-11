from django.db import migrations

STARTER_FEATURES = sorted({"seat_allocation", "exports", "publication", "branding"})


def seed_starter(apps, schema_editor):
    """One plan the console can offer from day one (plans become editable in
    build slice 8). Unlimited, with every feature; edit it like any plan."""
    Plan = apps.get_model("tenancy", "Plan")
    Plan.objects.get_or_create(
        code="starter",
        defaults={
            "name": "Starter",
            "max_students": None,
            "max_staff_users": None,
            "features": STARTER_FEATURES,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0003_school_created_by"),
    ]

    operations = [
        migrations.RunPython(seed_starter, migrations.RunPython.noop),
    ]
