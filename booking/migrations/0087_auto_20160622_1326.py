# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0086_auto_20160606_1258'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='visit',
            name='default_hosts',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='default_teachers',
        ),
        migrations.AlterField(
            model_name='booker',
            name='attendee_count',
            field=models.IntegerField(blank=True, null=True, verbose_name='Antal deltagere', validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='visit',
            name='custom_available',
            field=models.BooleanField(default=False, verbose_name='Andet'),
        ),
    ]
