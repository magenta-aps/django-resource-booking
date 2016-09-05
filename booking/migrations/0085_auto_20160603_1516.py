# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0084_auto_20160601_1309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='autosend',
            name='template_key',
            field=models.IntegerField(verbose_name='Skabelon', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (20, 'Besked til g\xe6st ved tilmelding p\xe5 venteliste'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (16, 'Mail til g\xe6st fra venteliste, der f\xe5r tilbudt plads p\xe5 bes\xf8get'), (17, 'Besked til g\xe6st ved accept af plads (fra venteliste)'), (18, 'Besked til g\xe6st ved afvisning af plads (fra venteliste)'), (19, 'Besked til koordinatorer ved afvisning af plads (fra venteliste)'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (21, 'Notifikation til underviser om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (22, 'Besked til alle om evaluering'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Type', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (20, 'Besked til g\xe6st ved tilmelding p\xe5 venteliste'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (16, 'Mail til g\xe6st fra venteliste, der f\xe5r tilbudt plads p\xe5 bes\xf8get'), (17, 'Besked til g\xe6st ved accept af plads (fra venteliste)'), (18, 'Besked til g\xe6st ved afvisning af plads (fra venteliste)'), (19, 'Besked til koordinatorer ved afvisning af plads (fra venteliste)'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (21, 'Notifikation til underviser om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (22, 'Besked til alle om evaluering'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='kuemailmessage',
            name='template_key',
            field=models.IntegerField(default=None, null=True, verbose_name='Template key', blank=True, choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (20, 'Besked til g\xe6st ved tilmelding p\xe5 venteliste'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (16, 'Mail til g\xe6st fra venteliste, der f\xe5r tilbudt plads p\xe5 bes\xf8get'), (17, 'Besked til g\xe6st ved accept af plads (fra venteliste)'), (18, 'Besked til g\xe6st ved afvisning af plads (fra venteliste)'), (19, 'Besked til koordinatorer ved afvisning af plads (fra venteliste)'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (21, 'Notifikation til underviser om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (22, 'Besked til alle om evaluering'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Oprettet af', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='contact',
            field=models.ForeignKey(related_name='contactperson_for_units', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Kontaktperson', blank=True, to='booking.Person', null=True),
        ),
    ]
