# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import datetime
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0082_auto_20160530_1320'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailBookerEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_in', models.DurationField(default=datetime.timedelta(2))),
                ('booker', models.ForeignKey(to='booking.Booker')),
            ],
        ),
    ]
