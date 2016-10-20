# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0061_auto_20160404_1021'),
    ]

    operations = [
        migrations.AlterField(
            model_name='objectstatistics',
            name='updated_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='hosts',
            field=models.ManyToManyField(related_name='hosted_visitoccurrences', verbose_name='V\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='teachers',
            field=models.ManyToManyField(related_name='taught_visitoccurrences', verbose_name='Undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
    ]
