# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0023_auto_20160204_1515'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookedRoom',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=60, verbose_name='Navn')),
            ],
        ),
        migrations.AddField(
            model_name='booking',
            name='host_status',
            field=models.IntegerField(default=2, verbose_name='Status for tildeling af v\xe6rter', choices=[(0, 'Tildeling af v\xe6rter ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling'), (1, 'Tildelt')]),
        ),
        migrations.AddField(
            model_name='booking',
            name='hosts',
            field=models.ManyToManyField(related_name='hosted_bookings', verbose_name='V\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='room_status',
            field=models.IntegerField(default=2, verbose_name='Status for tildeling af lokaler', choices=[(0, 'Tildeling af lokaler ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling'), (1, 'Tildelt')]),
        ),
        migrations.AddField(
            model_name='booking',
            name='teacher_status',
            field=models.IntegerField(default=2, verbose_name='Status for tildeling af undervisere', choices=[(0, 'Tildeling af undervisere ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling'), (1, 'Tildelt')]),
        ),
        migrations.AddField(
            model_name='booking',
            name='teachers',
            field=models.ManyToManyField(related_name='taught_bookings', verbose_name='Undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='workflow_status',
            field=models.IntegerField(default=0, choices=[(0, 'Under planl\xe6gning'), (1, 'Afvist af undervisere eller v\xe6rter'), (2, 'Planlagt (ressourcer tildelt)'), (3, 'Bekr\xe6ftet af booker'), (4, 'P\xe5mindelse afsendt'), (5, 'Afviklet'), (6, 'Evalueret'), (7, 'Aflyst'), (8, 'Udeblevet')]),
        ),
        migrations.AddField(
            model_name='bookedroom',
            name='booking',
            field=models.ForeignKey(related_name='assigned_rooms', to='booking.Booking'),
        ),
    ]
