# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0044_remove_studymaterial_resource'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudyMaterial_Migrate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.IntegerField(default=0, choices=[(0, 'URL'), (1, 'Vedh\xe6ftet fil')])),
                ('url', models.URLField(null=True, blank=True)),
                ('file', models.FileField(null=True, upload_to=b'material', blank=True)),
                ('resource', models.ForeignKey(to='booking.Resource', null=True)),
            ],
            options={
                'verbose_name': 'undervisningsmateriale',
                'verbose_name_plural': 'undervisningsmaterialer',
            },
        ),
    ]
