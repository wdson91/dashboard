# Generated by Django 5.2.3 on 2025-06-17 16:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturas', '0005_profile_photo_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='fatura',
            name='ultima_atualizacao',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
