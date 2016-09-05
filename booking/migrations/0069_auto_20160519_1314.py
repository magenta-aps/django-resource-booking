# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0068_auto_20160517_0934'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPerson',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('person', models.ForeignKey(blank=True, to='booking.Person', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name': 'Lokaleanvarlig',
                'verbose_name_plural': 'Lokaleanvarlige',
            },
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Type', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='state',
            field=models.IntegerField(default=0, verbose_name='Status', choices=[(0, 'Under udarbejdelse'), (1, 'Offentlig'), (2, 'Skjult')]),
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='workflow_status',
            field=models.IntegerField(default=0, choices=[(0, 'Under planl\xe6gning'), (1, 'Afvist af undervisere eller v\xe6rter'), (2, 'Planlagt (ressourcer tildelt)'), (9, 'Planlagt og lukket for booking'), (3, 'Bekr\xe6ftet af g\xe6st'), (4, 'P\xe5mindelse afsendt'), (5, 'Afviklet'), (6, 'Evalueret'), (7, 'Aflyst'), (8, 'Udeblevet')]),
        ),
        migrations.AddField(
            model_name='resource',
            name='room_contact',
            field=models.ManyToManyField(related_name='roomadmin_visit_new', verbose_name='Lokaleansvarlige', to='booking.UserPerson', blank=True),
        ),
    ]
