from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_deliveryassignment_multiple_offers'),
    ]

    operations = [
        migrations.AddField(
            model_name='deliveryassignment',
            name='restaurant_lat',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name='Latitud del restaurante',
            ),
        ),
        migrations.AddField(
            model_name='deliveryassignment',
            name='restaurant_lng',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name='Longitud del restaurante',
            ),
        ),
    ]
