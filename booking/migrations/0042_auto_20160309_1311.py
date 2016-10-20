# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0041_auto_20160303_1644'),
    ]

    operations = [
        migrations.CreateModel(
            name='Autosend',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('template_key', models.IntegerField(verbose_name='Skabelon', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'Alle: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking')])),
                ('days', models.PositiveSmallIntegerField(null=True, verbose_name='Afsendes dage inden bes\xf8get', blank=True)),
                ('enabled', models.BooleanField(default=True, verbose_name='Aktiv')),
            ],
        ),
        migrations.AlterModelOptions(
            name='bookedroom',
            options={'verbose_name': 'lokale for arrangement', 'verbose_name_plural': 'lokaler for arrangement'},
        ),
        migrations.AlterModelOptions(
            name='unit',
            options={'ordering': ['name'], 'verbose_name': 'enhed', 'verbose_name_plural': 'enheder'},
        ),
        migrations.AlterModelOptions(
            name='visitoccurrence',
            options={'ordering': ['start_datetime'], 'verbose_name': 'arrangement', 'verbose_name_plural': 'arrangementer'},
        ),
        migrations.RemoveField(
            model_name='visit',
            name='needed_hosts_text',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='needed_teachers_text',
        ),
        migrations.RemoveField(
            model_name='visitautosend',
            name='id',
        ),
        migrations.RemoveField(
            model_name='visitautosend',
            name='template_key',
        ),
        migrations.AlterField(
            model_name='booking',
            name='visitoccurrence',
            field=models.ForeignKey(related_name='bookings', blank=True, to='booking.VisitOccurrence', null=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='needed_hosts',
            field=models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal v\xe6rter', choices=[(0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')]),
        ),
        migrations.AlterField(
            model_name='visit',
            name='needed_teachers',
            field=models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal undervisere', choices=[(0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')]),
        ),
        migrations.CreateModel(
            name='VisitOccurrenceAutosend',
            fields=[
                ('autosend_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Autosend')),
                ('inherit', models.BooleanField(verbose_name='Nedarv fra tilbud')),
                ('visitoccurrence', models.ForeignKey(verbose_name='Bes\xf8gForekomst', to='booking.VisitOccurrence')),
            ],
            bases=('booking.autosend',),
        ),
        migrations.AddField(
            model_name='visitautosend',
            name='autosend_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=None, serialize=False, to='booking.Autosend'),
            preserve_default=False,
        ),
    ]
