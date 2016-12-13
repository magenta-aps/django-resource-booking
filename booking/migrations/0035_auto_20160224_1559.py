# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0034_auto_20160223_1022'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='additionalservice',
            options={'verbose_name': 'ekstra ydelse', 'verbose_name_plural': 'ekstra ydelser'},
        ),
        migrations.AlterModelOptions(
            name='bookedroom',
            options={'verbose_name': 'lokale for booking', 'verbose_name_plural': 'lokaler for bookinger'},
        ),
        migrations.AlterModelOptions(
            name='booker',
            options={'verbose_name': 'bes\xf8gende', 'verbose_name_plural': 'bes\xf8gende'},
        ),
        migrations.AlterModelOptions(
            name='booking',
            options={'verbose_name': 'booking', 'verbose_name_plural': 'bookinger'},
        ),
        migrations.AlterModelOptions(
            name='bookingsubjectlevel',
            options={'verbose_name': 'fagniveau for booking', 'verbose_name_plural': 'fagniveauer for bookinger'},
        ),
        migrations.AlterModelOptions(
            name='classbooking',
            options={'verbose_name': 'booking for klassebes\xf8g', 'verbose_name_plural': 'bookinger for klassebes\xf8g'},
        ),
        migrations.AlterModelOptions(
            name='gymnasielevel',
            options={'ordering': ['level'], 'verbose_name': 'Gymnasieniveau', 'verbose_name_plural': 'Gymnasieniveauer'},
        ),
        migrations.AlterModelOptions(
            name='locality',
            options={'verbose_name': 'lokalitet', 'verbose_name_plural': 'lokaliteter'},
        ),
        migrations.AlterModelOptions(
            name='otherresource',
            options={'verbose_name': 'tilbud uden booking', 'verbose_name_plural': 'tilbud uden booking'},
        ),
        migrations.AlterModelOptions(
            name='person',
            options={'verbose_name': 'kontaktperson', 'verbose_name_plural': 'kontaktpersoner'},
        ),
        migrations.AlterModelOptions(
            name='postcode',
            options={'verbose_name': 'postnummer', 'verbose_name_plural': 'postnumre'},
        ),
        migrations.AlterModelOptions(
            name='region',
            options={'verbose_name': 'region', 'verbose_name_plural': 'regioner'},
        ),
        migrations.AlterModelOptions(
            name='resourcegrundskolefag',
            options={'verbose_name': 'grundskolefagtilknytning', 'verbose_name_plural': 'grundskolefagtilknytninger'},
        ),
        migrations.AlterModelOptions(
            name='resourcegymnasiefag',
            options={'verbose_name': 'gymnasiefagtilknytning', 'verbose_name_plural': 'gymnasiefagtilknytninger'},
        ),
        migrations.AlterModelOptions(
            name='room',
            options={'verbose_name': 'lokale for tilbud', 'verbose_name_plural': 'lokaler for tilbud'},
        ),
        migrations.AlterModelOptions(
            name='school',
            options={'verbose_name': 'uddannelsesinstitution', 'verbose_name_plural': 'uddannelsesinstitutioner'},
        ),
        migrations.AlterModelOptions(
            name='specialrequirement',
            options={'verbose_name': 's\xe6rligt krav', 'verbose_name_plural': 's\xe6rlige ydelser'},
        ),
        migrations.AlterModelOptions(
            name='studymaterial',
            options={'verbose_name': 'undervisningsmateriale', 'verbose_name_plural': 'undervisningsmaterialer'},
        ),
        migrations.AlterModelOptions(
            name='subject',
            options={'verbose_name': 'fag', 'verbose_name_plural': 'fag'},
        ),
        migrations.AlterModelOptions(
            name='teacherbooking',
            options={'verbose_name': 'booking for l\xe6rerarrangement', 'verbose_name_plural': 'bookinger for l\xe6rerarrangementer'},
        ),
        migrations.AlterModelOptions(
            name='topic',
            options={'verbose_name': 'emne', 'verbose_name_plural': 'emner'},
        ),
        migrations.AlterModelOptions(
            name='unit',
            options={'verbose_name': 'enhed', 'verbose_name_plural': 'enheder'},
        ),
        migrations.AlterModelOptions(
            name='unittype',
            options={'verbose_name': 'enhedstype', 'verbose_name_plural': 'Enhedstyper'},
        ),
        migrations.AlterModelOptions(
            name='visit',
            options={'verbose_name': 'tilbud med booking', 'verbose_name_plural': 'tilbud med booking'},
        ),
        migrations.AlterModelOptions(
            name='visitoccurrence',
            options={'ordering': ['start_datetime'], 'verbose_name': 'tidspunkt for bes\xf8g', 'verbose_name_plural': 'tidspunkter for bes\xf8g'},
        ),
        migrations.AddField(
            model_name='person',
            name='unit',
            field=models.ForeignKey(blank=True, to='booking.Unit', null=True),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'V\xe6rt: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking'), (11, 'System: Indpakning af brugerbesked')]),
        ),
        migrations.AlterField(
            model_name='unit',
            name='contact',
            field=models.ForeignKey(related_name='contactperson_for_units', verbose_name='Kontaktperson', blank=True, to='booking.Person', null=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='duration',
            field=models.CharField(blank=True, max_length=8, null=True, verbose_name='Varighed', choices=[(b'00:00', b'00:00'), (b'00:15', b'00:15'), (b'00:30', b'00:30'), (b'00:45', b'00:45'), (b'01:00', b'01:00'), (b'01:15', b'01:15'), (b'01:30', b'01:30'), (b'01:45', b'01:45'), (b'02:00', b'02:00'), (b'02:15', b'02:15'), (b'02:30', b'02:30'), (b'02:45', b'02:45'), (b'03:00', b'03:00'), (b'03:15', b'03:15'), (b'03:30', b'03:30'), (b'03:45', b'03:45'), (b'04:00', b'04:00'), (b'04:15', b'04:15'), (b'04:30', b'04:30'), (b'04:45', b'04:45'), (b'05:00', b'05:00'), (b'05:15', b'05:15'), (b'05:30', b'05:30'), (b'05:45', b'05:45'), (b'06:00', b'06:00'), (b'06:15', b'06:15'), (b'06:30', b'06:30'), (b'06:45', b'06:45'), (b'07:00', b'07:00'), (b'07:15', b'07:15'), (b'07:30', b'07:30'), (b'07:45', b'07:45'), (b'08:00', b'08:00'), (b'08:15', b'08:15'), (b'08:30', b'08:30'), (b'08:45', b'08:45'), (b'09:00', b'09:00'), (b'09:15', b'09:15'), (b'09:30', b'09:30'), (b'09:45', b'09:45'), (b'10:00', b'10:00'), (b'10:15', b'10:15'), (b'10:30', b'10:30'), (b'10:45', b'10:45'), (b'11:00', b'11:00'), (b'11:15', b'11:15'), (b'11:30', b'11:30'), (b'11:45', b'11:45')]),
        ),
    ]
