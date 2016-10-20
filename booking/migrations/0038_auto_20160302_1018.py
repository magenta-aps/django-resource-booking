# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0037_unit_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitAutosend',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('template_key', models.IntegerField(choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'V\xe6rt: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking')])),
                ('visit', models.ForeignKey(verbose_name='Bes\xf8g', to='booking.Visit')),
            ],
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'V\xe6rt: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking')]),
        ),
    ]
