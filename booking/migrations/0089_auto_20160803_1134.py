# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0088_auto_20160627_1349'),
    ]

    operations = [
        migrations.CreateModel(
            name='LokaleAnsvarlig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('email', models.EmailField(max_length=64, null=True, blank=True)),
                ('phone', models.CharField(max_length=14, null=True, blank=True)),
                ('unit', models.ForeignKey(blank=True, to='booking.Unit', null=True)),
            ],
            options={
                'verbose_name': 'Lokaleanvarlig',
                'verbose_name_plural': 'Lokaleanvarlige',
            },
        ),
        migrations.AlterModelOptions(
            name='userperson',
            options={'ordering': ['person__name', 'user__first_name', 'user__username'], 'verbose_name': 'Lokaleanvarlig-eller-kontaktperson', 'verbose_name_plural': 'Lokaleanvarlige-eller-kontaktpersoner'},
        ),
        migrations.RemoveField(
            model_name='resource',
            name='contact_persons',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='contacts',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='room_contact',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='room_responsible',
        ),
        migrations.AddField(
            model_name='resource',
            name='tilbudsansvarlig',
            field=models.ForeignKey(related_name='tilbudsansvarlig_for_set', verbose_name='Tilbudsansvarlig', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='created_by',
            field=models.ForeignKey(related_name='created_visits_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Oprettet af', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='lokaleansvarlige',
            field=models.ManyToManyField(related_name='ansvarlig_for_besoeg_set', verbose_name='Lokaleansvarlige', to='booking.LokaleAnsvarlig', blank=True),
        ),
    ]
