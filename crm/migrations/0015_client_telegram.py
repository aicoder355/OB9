from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0014_loyaltyprogram_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='telegram_chat_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True, help_text='Telegram chat id, привязанный к клиенту'),
        ),
    ]
