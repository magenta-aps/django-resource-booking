# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import datetime
import uuid
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('profile', '0003_auto_20160120_1214'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailLoginEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('success_url', models.CharField(max_length=2024)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_in', models.DurationField(default=datetime.timedelta(2))),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
