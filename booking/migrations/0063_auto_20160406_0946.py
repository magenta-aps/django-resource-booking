# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0062_auto_20160404_1548'),
    ]

    operations = [
        migrations.AlterField(
            model_name='autosend',
            name='template_key',
            field=models.IntegerField(verbose_name='Skabelon', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notfikation til v\xe6rter om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular')]),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='N\xf8gle', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notfikation til v\xe6rter om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular')]),
        ),
        migrations.AlterField(
            model_name='visitoccurrenceautosend',
            name='inherit',
            field=models.BooleanField(verbose_name='Genbrug indstilling fra tilbud'),
        ),
    ]
