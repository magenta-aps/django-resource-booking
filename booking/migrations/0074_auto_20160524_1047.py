# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0073_auto_20160523_1358'),
    ]

    operations = [
        migrations.CreateModel(
            name='Municipality',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=30, verbose_name='Navn')),
                ('region', models.ForeignKey(verbose_name='Region', to='booking.Region')),
            ],
            options={
                'verbose_name': 'kommune',
                'verbose_name_plural': 'kommuner',
            },
        ),
        migrations.AddField(
            model_name='school',
            name='municipality',
            field=models.ForeignKey(to='booking.Municipality', null=True),
        ),
    ]
