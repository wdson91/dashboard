# Generated by Django 5.2.3 on 2025-06-13 07:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturas', '0003_fatura_qrcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='fatura',
            name='texto_completo',
            field=models.TextField(blank=True, null=True),
        ),
    ]
