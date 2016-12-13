# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0049_auto_20160314_1426'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='room_responsible',
            field=models.ManyToManyField(related_name='roomadmin_visit', verbose_name='Lokaleansvarlige', to='booking.Person', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='contact_persons',
            field=models.ManyToManyField(related_name='contact_visit', verbose_name='Kontaktpersoner', to='booking.Person', blank=True),
        ),
    ]
