# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
import djorm_pgfulltext.fields
from django.utils.timezone import utc
import timedelta.fields


class Migration(migrations.Migration):

    dependencies = [
        ('booking', 'units'),
    ]

    operations = [
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=True, verbose_name='Aktiv')),
                ('type', models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (1, 'Gruppebes\xf8g med faste tider'), (2, 'Gruppebes\xf8g uden faste tider'), (3, 'Studieretningsprojekt - SRP'), (4, 'Enkeltst\xe5ende event'), (5, 'Andre tilbud')])),
                ('title', models.CharField(max_length=256, verbose_name='Titel')),
                ('teaser', models.TextField(verbose_name='Teaser', blank=True)),
                ('description', models.TextField(verbose_name='Beskrivelse', blank=True)),
                ('mouseover_description', models.CharField(max_length=512, verbose_name='Mouseover-tekst', blank=True)),
                ('audience', models.IntegerField(default=0, verbose_name='M\xe5lgruppe', choices=[(0, 'L\xe6rer'), (1, 'Elev')])),
                ('institution_level', models.IntegerField(default=1, verbose_name='Institution', choices=[(0, 'Grundskole'), (1, 'Gymnasium')])),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Niveau', choices=[(0, 'A'), (0, 'B'), (0, 'C')])),
                ('class_level_min', models.IntegerField(default=0, verbose_name='Klassetrin fra', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('class_level_max', models.IntegerField(default=10, verbose_name='Klassetrin til', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('comment', models.TextField(verbose_name='Kommentar', blank=True)),
                ('search_index', djorm_pgfulltext.fields.VectorField(default=b'', serialize=False, null=True, editable=False, db_index=True)),
                ('extra_search_text', models.TextField(default=b'', verbose_name='Tekst-v\xe6rdier til friteksts\xf8gning', blank=True)),
                ('links', models.ManyToManyField(to='booking.Link', verbose_name='Links', blank=True)),
                ('subjects', models.ManyToManyField(to='booking.Subject', verbose_name='Fag', blank=True)),
                ('tags', models.ManyToManyField(to='booking.Tag', verbose_name='Tags', blank=True)),
                ('topics', models.ManyToManyField(to='booking.Topic', verbose_name='Emner', blank=True)),
                ('unit', models.ForeignKey(verbose_name='Enhed', blank=True, to='booking.Unit', null=True)),
            ],
        ),
        migrations.RenameField(
            model_name='visit',
            old_name='mininimum_number_of_visitors',
            new_name='minimum_number_of_visitors',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='audience',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='class_level_max',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='class_level_min',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='comment',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='description',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='id',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='institution_level',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='level',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='links',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='mouseover_description',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='subjects',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='title',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='topics',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='type',
        ),
        migrations.RemoveField(
            model_name='otherresource',
            name='unit',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='audience',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='class_level_max',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='class_level_min',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='comment',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='description',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='id',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='institution_level',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='level',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='links',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='mouseover_description',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='preparatory_material',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='subjects',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='title',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='topics',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='type',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='unit',
        ),
        migrations.AddField(
            model_name='visit',
            name='duration',
            field=timedelta.fields.TimedeltaField(null=True, verbose_name='Varighed', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2015, 12, 2, 15, 39, 31, 106122, tzinfo=utc), verbose_name='Tid'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otherresource',
            name='resource_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=1, serialize=False, to='booking.Resource'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='visit',
            name='resource_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=1, serialize=False, to='booking.Resource'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studymaterial',
            name='visit',
            field=models.ForeignKey(default=1, to='booking.Visit'),
            preserve_default=False,
        ),
    ]
