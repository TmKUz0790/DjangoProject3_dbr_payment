# Generated by Django 5.1.4 on 2025-01-15 09:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbr_payment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='months_covered',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
