import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("receipts", "0002_receipt_ai_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stripe_customer_id", models.CharField(blank=True, max_length=255)),
                ("stripe_subscription_id", models.CharField(max_length=255, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("trialing", "Trialing"),
                            ("canceled", "Canceled"),
                            ("incomplete", "Incomplete"),
                            ("incomplete_expired", "Incomplete expired"),
                            ("unpaid", "Unpaid"),
                            ("past_due", "Past due"),
                        ],
                        max_length=32,
                    ),
                ),
                ("plan_interval", models.CharField(choices=[("month", "Month"), ("year", "Year")], default="month", max_length=16)),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
