# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0075_auto_20160524_1333'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitOccurrenceComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deleted_user_name', models.CharField(max_length=30)),
                ('text', models.CharField(max_length=500, verbose_name='Kommentartekst')),
                ('time', models.DateTimeField(auto_now=True, verbose_name='Tidsstempel')),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
                ('visitoccurrence', models.ForeignKey(verbose_name='Bes\xf8g', to='booking.VisitOccurrence')),
            ],
            options={
                'ordering': ['-time'],
            },
        ),
    ]
