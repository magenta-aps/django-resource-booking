# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_auto_20151118_0845'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('line', models.IntegerField(blank=True, null=True, verbose_name='Linje', choices=[(0, 'stx'), (1, 'hf'), (2, 'htx'), (3, 'eux'), (4, 'valgfag')])),
                ('description', models.TextField()),
            ],
        ),
        migrations.AddField(
            model_name='resource',
            name='unit',
            field=models.ForeignKey(blank=True, to='booking.Unit', null=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='institution_level',
            field=models.IntegerField(default=1, verbose_name='Institution', choices=[(0, 'Folkeskole'), (1, 'Gymnasium')]),
        ),
        migrations.AddField(
            model_name='resource',
            name='subjects',
            field=models.ManyToManyField(to='booking.Subject'),
        ),
    ]
