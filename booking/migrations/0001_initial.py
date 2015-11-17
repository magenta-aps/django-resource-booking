# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=256)),
                ('description', models.TextField()),
                ('mouseover_description', models.CharField(max_length=512)),
                ('audience', models.IntegerField(verbose_name='M\xe5lgruppe', choices=[(0, 'L\xe6rer'), (1, 'Elev')])),
                ('institution_level', models.IntegerField(verbose_name='Institution', choices=[(0, 'Folkeskole'), (1, 'Gymnasium')])),
                ('comment', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('resource_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Resource')),
            ],
            bases=('booking.resource',),
        ),
    ]
