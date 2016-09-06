# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import djorm_pgfulltext.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0040_auto_20160302_1504'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='visitoccurrence',
            options={'ordering': ['start_datetime'], 'verbose_name': 'planlagt bes\xf8g/bes\xf8g under planl\xe6gning', 'verbose_name_plural': 'planlagte bes\xf8g/bes\xf8g under planl\xe6gning'},
        ),
        migrations.RemoveField(
            model_name='booker',
            name='notes',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='comments',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='extra_search_text',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='host_status',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='hosts',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='room_status',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='search_index',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='teacher_status',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='teachers',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='visit',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='workflow_status',
        ),
        migrations.RemoveField(
            model_name='classbooking',
            name='desired_time',
        ),
        migrations.RemoveField(
            model_name='classbooking',
            name='time',
        ),
        migrations.RemoveField(
            model_name='visitoccurrence',
            name='end_datetime1',
        ),
        migrations.RemoveField(
            model_name='visitoccurrence',
            name='end_datetime2',
        ),
        migrations.AddField(
            model_name='booking',
            name='notes',
            field=models.TextField(verbose_name='Bem\xe6rkninger', blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='visitoccurrence',
            field=models.ForeignKey(related_name='bookings', to='booking.VisitOccurrence', null=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='bookable',
            field=models.BooleanField(default=False, verbose_name='Kan bookes'),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='comments',
            field=models.TextField(default=b'', verbose_name='Interne kommentarer', blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='desired_time',
            field=models.CharField(max_length=2000, null=True, verbose_name='\xd8nsket tidspunkt', blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='extra_search_text',
            field=models.TextField(default=b'', verbose_name='Tekst-v\xe6rdier til friteksts\xf8gning', editable=False, blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='host_status',
            field=models.IntegerField(default=2, verbose_name='Status for tildeling af v\xe6rter', choices=[(0, 'Tildeling af v\xe6rter ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling'), (1, 'Tildelt')]),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='hosts',
            field=models.ManyToManyField(related_name='hosted_bookings', verbose_name='V\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='override_duration',
            field=models.CharField(max_length=8, null=True, verbose_name='Varighed', blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='override_locality',
            field=models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='room_status',
            field=models.IntegerField(default=2, verbose_name='Status for tildeling af lokaler', choices=[(0, 'Tildeling af lokaler ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling'), (1, 'Tildelt')]),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='search_index',
            field=djorm_pgfulltext.fields.VectorField(default=b'', serialize=False, null=True, editable=False, db_index=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='teacher_status',
            field=models.IntegerField(default=2, verbose_name='Status for tildeling af undervisere', choices=[(0, 'Tildeling af undervisere ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling'), (1, 'Tildelt')]),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='teachers',
            field=models.ManyToManyField(related_name='taught_bookings', verbose_name='Undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='workflow_status',
            field=models.IntegerField(default=0, choices=[(0, 'Under planl\xe6gning'), (1, 'Afvist af undervisere eller v\xe6rter'), (2, 'Planlagt (ressourcer tildelt)'), (3, 'Bekr\xe6ftet af booker'), (4, 'P\xe5mindelse afsendt'), (5, 'Afviklet'), (6, 'Evalueret'), (7, 'Aflyst'), (8, 'Udeblevet')]),
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='start_datetime',
            field=models.DateTimeField(null=True, verbose_name='Starttidspunkt', blank=True),
        ),
    ]
