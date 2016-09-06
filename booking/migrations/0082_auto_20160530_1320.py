# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0081_auto_20160530_1057'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='waitinglist',
            name='guests',
        ),
        migrations.AlterModelOptions(
            name='school',
            options={'ordering': ['name', 'postcode'], 'verbose_name': 'uddannelsesinstitution', 'verbose_name_plural': 'uddannelsesinstitutioner'},
        ),
        migrations.AlterField(
            model_name='autosend',
            name='template_key',
            field=models.IntegerField(verbose_name='Skabelon', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (16, 'Besked til g\xe6st p\xe5 venteliste om ledig plads'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Type', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (16, 'Besked til g\xe6st p\xe5 venteliste om ledig plads'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='kuemailmessage',
            name='template_key',
            field=models.IntegerField(default=None, null=True, verbose_name='Template key', blank=True, choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (16, 'Besked til g\xe6st p\xe5 venteliste om ledig plads'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='audience',
            field=models.IntegerField(default=None, verbose_name='M\xe5lgruppe', choices=[(None, b'---------'), (1, 'L\xe6rer'), (2, 'Elev'), (3, 'Alle')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='state',
            field=models.IntegerField(verbose_name='Status', choices=[(None, b'---------'), (0, 'Under udarbejdelse'), (1, 'Offentlig'), (2, 'Skjult')]),
        ),
        migrations.AlterField(
            model_name='visit',
            name='needed_hosts',
            field=models.IntegerField(default=None, verbose_name='N\xf8dvendigt antal v\xe6rter', choices=[(None, b'---------'), (0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')]),
        ),
        migrations.AlterField(
            model_name='visit',
            name='needed_teachers',
            field=models.IntegerField(default=None, verbose_name='N\xf8dvendigt antal undervisere', choices=[(None, b'---------'), (0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')]),
        ),
        migrations.DeleteModel(
            name='WaitingList',
        ),
    ]
