# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import uuid

import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailLoginURL',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('success_url', models.CharField(max_length=2024)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_in', models.DurationField(default=datetime.timedelta(2))),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('additional_information', models.TextField(default=b'', verbose_name='Yderligere information', blank=True)),
                ('my_resources', models.ManyToManyField(to='booking.Product', verbose_name='Mine tilbud', blank=True)),
                ('organizationalunit', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='booking.OrganizationalUnit', null=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.IntegerField(default=0, choices=[(0, 'Underviser'), (1, 'Vært'), (2, 'Koordinator'), (3, 'Administrator'), (4, 'Fakultetsredaktør'), (5, 'Ingen')])),
                ('name', models.CharField(max_length=256, blank=True)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'brugerrolle',
                'verbose_name_plural': 'brugerroller',
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='user_role',
            field=models.ForeignKey(to='user_profile.UserRole', on_delete=django.db.models.deletion.CASCADE),
        ),
    ]
