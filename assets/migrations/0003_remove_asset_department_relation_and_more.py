from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0002_asset_department_relation"),
        ("departments", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="asset",
            name="department_relation",
        ),

        migrations.AlterField(
            model_name="asset",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assets",
                to="departments.department",
            ),
        ),
    ]