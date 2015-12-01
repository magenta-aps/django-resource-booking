# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AdditionalService',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('name', models.CharField(max_length=256)),
                ('description', models.CharField(max_length=256, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Locality',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256, verbose_name='Navn')),
                ('description', models.TextField(verbose_name='Beskrivelse', blank=True)),
                ('address_line', models.CharField(max_length=256, verbose_name='Adresse')),
                ('zip_city', models.CharField(max_length=256, verbose_name='Postnummer og by')),
            ],
        ),
        migrations.CreateModel(
            name='OtherResource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (1, 'Gruppebes\xf8g med faste tider'), (2, 'Gruppebes\xf8g uden faste tider'), (3, 'Studieretningsprojekt - SRP'), (4, 'Enkeltst\xe5ende event'), (5, 'Andre tilbud')])),
                ('title', models.CharField(max_length=256, verbose_name='Titel')),
                ('description', models.TextField(verbose_name='Beskrivelse', blank=True)),
                ('mouseover_description', models.CharField(max_length=512, verbose_name='Mouseover-tekst', blank=True)),
                ('audience', models.IntegerField(default=0, verbose_name='M\xe5lgruppe', choices=[(0, 'L\xe6rer'), (1, 'Elev')])),
                ('institution_level', models.IntegerField(default=1, verbose_name='Institution', choices=[(0, 'Grundskole'), (1, 'Gymnasium')])),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Niveau', choices=[(0, 'A'), (0, 'B'), (0, 'C')])),
                ('class_level_min', models.IntegerField(default=0, verbose_name='Klassetrin fra', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('class_level_max', models.IntegerField(default=10, verbose_name='Klassetrin til', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('comment', models.TextField(verbose_name='Kommentar', blank=True)),
                ('links', models.ManyToManyField(to='booking.Link', verbose_name='Links', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('email', models.EmailField(max_length=64, null=True, blank=True)),
                ('phone', models.CharField(max_length=14, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='SpecialRequirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='StudyMaterial',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.IntegerField(default=0, choices=[(0, 'URL'), (1, 'Vedh\xe6ftet fil')])),
                ('url', models.URLField(null=True, blank=True)),
                ('file', models.FileField(null=True, upload_to=b'material', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('line', models.IntegerField(blank=True, verbose_name='Linje', choices=[(0, 'stx'), (1, 'hf'), (2, 'htx'), (3, 'eux'), (4, 'valgfag')])),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('contact', models.ForeignKey(blank=True, to='booking.Person', null=True)),
                ('parent', models.ForeignKey(blank=True, to='booking.Unit', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='UnitType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
            ],
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (1, 'Gruppebes\xf8g med faste tider'), (2, 'Gruppebes\xf8g uden faste tider'), (3, 'Studieretningsprojekt - SRP'), (4, 'Enkeltst\xe5ende event'), (5, 'Andre tilbud')])),
                ('title', models.CharField(max_length=256, verbose_name='Titel')),
                ('description', models.TextField(verbose_name='Beskrivelse', blank=True)),
                ('mouseover_description', models.CharField(max_length=512, verbose_name='Mouseover-tekst', blank=True)),
                ('audience', models.IntegerField(default=0, verbose_name='M\xe5lgruppe', choices=[(0, 'L\xe6rer'), (1, 'Elev')])),
                ('institution_level', models.IntegerField(default=1, verbose_name='Institution', choices=[(0, 'Grundskole'), (1, 'Gymnasium')])),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Niveau', choices=[(0, 'A'), (0, 'B'), (0, 'C')])),
                ('class_level_min', models.IntegerField(default=0, verbose_name='Klassetrin fra', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('class_level_max', models.IntegerField(default=10, verbose_name='Klassetrin til', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('comment', models.TextField(verbose_name='Kommentar', blank=True)),
                ('room', models.CharField(max_length=64, verbose_name='Lokale', blank=True)),
                ('do_send_evaluation', models.BooleanField(default=False, verbose_name='Udsend evaluering')),
                ('price', models.DecimalField(default=0, verbose_name='Pris', max_digits=10, decimal_places=2)),
                ('is_group_visit', models.BooleanField(default=True, verbose_name='Gruppebes\xf8g')),
                ('mininimum_number_of_visitors', models.IntegerField(null=True, verbose_name='Mindste antal deltagere', blank=True)),
                ('maximum_number_of_visitors', models.IntegerField(null=True, verbose_name='H\xf8jeste antal deltagere', blank=True)),
                ('do_create_waiting_list', models.BooleanField(default=False, verbose_name='Opret venteliste')),
                ('do_show_countdown', models.BooleanField(default=False, verbose_name='Vis nedt\xe6lling')),
                ('preparation_time', models.IntegerField(default=0, verbose_name='Forberedelsestid (i timer)')),
                ('additional_services', models.ManyToManyField(to='booking.AdditionalService', verbose_name='Ekstra ydelser', blank=True)),
                ('contact_persons', models.ManyToManyField(to='booking.Person', verbose_name='Kontaktpersoner', blank=True)),
                ('links', models.ManyToManyField(to='booking.Link', verbose_name='Links', blank=True)),
                ('locality', models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality')),
                ('preparatory_material', models.ManyToManyField(to='booking.StudyMaterial', verbose_name='Forberedelsesmateriale', blank=True)),
                ('special_requirements', models.ManyToManyField(to='booking.SpecialRequirement', verbose_name='S\xe6rlige krav', blank=True)),
                ('subjects', models.ManyToManyField(to='booking.Subject', verbose_name='Fag', blank=True)),
                ('tags', models.ManyToManyField(to='booking.Tag', verbose_name='Tags', blank=True)),
                ('topics', models.ManyToManyField(to='booking.Topic', verbose_name='Emner', blank=True)),
                ('unit', models.ForeignKey(verbose_name='Enhed', blank=True, to='booking.Unit', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='unit',
            name='type',
            field=models.ForeignKey(to='booking.UnitType'),
        ),
        migrations.AddField(
            model_name='otherresource',
            name='subjects',
            field=models.ManyToManyField(to='booking.Subject', verbose_name='Fag', blank=True),
        ),
        migrations.AddField(
            model_name='otherresource',
            name='tags',
            field=models.ManyToManyField(to='booking.Tag', verbose_name='Tags', blank=True),
        ),
        migrations.AddField(
            model_name='otherresource',
            name='topics',
            field=models.ManyToManyField(to='booking.Topic', verbose_name='Emner', blank=True),
        ),
        migrations.AddField(
            model_name='otherresource',
            name='unit',
            field=models.ForeignKey(verbose_name='Enhed', blank=True, to='booking.Unit', null=True),
        ),
        migrations.AddField(
            model_name='locality',
            name='unit',
            field=models.ForeignKey(verbose_name='Enhed', to='booking.Unit'),
        ),
    ]
