# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0007_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdditionalService',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('name', models.CharField(max_length=256)),
                ('description', models.CharField(max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='SpecialRequirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField()),
            ],
        ),
        migrations.AddField(
            model_name='resource',
            name='level',
            field=models.IntegerField(blank=True, null=True, verbose_name='Niveau', choices=[(0, 'a'), (0, 'B'), (0, 'C')]),
        ),
        migrations.AddField(
            model_name='resource',
            name='type',
            field=models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (1, 'Gruppebes\xf8g med faste tider'), (2, 'Gruppebes\xf8g uden faste tider'), (3, 'Studieretningsprojekt - SRP'), (4, 'Enkeltst\xe5ende event'), (5, 'Andre tilbud')]),
        ),
        migrations.AddField(
            model_name='visit',
            name='contact_persons',
            field=models.ManyToManyField(to='booking.Person'),
        ),
        migrations.AddField(
            model_name='visit',
            name='do_create_waiting_list',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='visit',
            name='do_send_evaluation',
            field=models.BooleanField(default=False, verbose_name='Udsend evaluering'),
        ),
        migrations.AddField(
            model_name='visit',
            name='do_show_countdown',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='visit',
            name='is_group_visit',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='maximum_number_of_visitors',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='mininimum_number_of_visitors',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='price',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='resource',
            name='institution_level',
            field=models.IntegerField(default=1, verbose_name='Institution', choices=[(0, 'Grundskole'), (1, 'Gymnasium')]),
        ),
        migrations.AddField(
            model_name='resource',
            name='links',
            field=models.ManyToManyField(to='booking.Link'),
        ),
        migrations.AddField(
            model_name='resource',
            name='topics',
            field=models.ManyToManyField(to='booking.Topic'),
        ),
        migrations.AddField(
            model_name='visit',
            name='additional_services',
            field=models.ManyToManyField(to='booking.AdditionalService'),
        ),
        migrations.AddField(
            model_name='visit',
            name='special_requirements',
            field=models.ManyToManyField(to='booking.SpecialRequirement'),
        ),
    ]
