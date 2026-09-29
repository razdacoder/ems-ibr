from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ems', '0019_slot_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='hall',
            name='layout',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
