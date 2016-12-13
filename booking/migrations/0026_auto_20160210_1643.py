# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0025_emailtemplate'),
    ]

    operations = [
        migrations.CreateModel(
            name='KUEmailMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=datetime.datetime(2016, 2, 10, 15, 43, 30, 860202, tzinfo=utc))),
                ('subject', models.TextField()),
                ('body', models.TextField()),
                ('from_email', models.TextField()),
                ('recipients', models.TextField()),
            ],
        ),
        migrations.RemoveField(
            model_name='classbooking',
            name='time',
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'Booking created'), (2, 'Message to bookers of a visit')]),
        ),
    ]
