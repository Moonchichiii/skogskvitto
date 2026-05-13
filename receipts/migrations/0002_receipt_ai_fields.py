import django.db.models.deletion
from django.db import migrations, models

import receipts.models


class Migration(migrations.Migration):
    dependencies = [
        ("receipts", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="receipt",
            name="currency",
        ),
        migrations.RemoveField(
            model_name="receipt",
            name="title",
        ),
        migrations.RemoveField(
            model_name="receipt",
            name="total",
        ),
        migrations.AddField(
            model_name="receipt",
            name="category",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="receipt",
            name="date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="receipt",
            name="image",
            field=models.ImageField(default="", upload_to=receipts.models.receipt_image_upload_path),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="receipt",
            name="total_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="receipt",
            name="vat_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="receipt",
            name="vendor",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="receipt",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="receipts",
                to="core.user",
            ),
        ),
    ]
