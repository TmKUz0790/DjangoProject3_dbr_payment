# Generated by Django 5.1.4 on 2025-01-15 09:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbr_payment', '0002_payment_months_covered'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='payment',
            name='months_covered',
        ),
    ]
