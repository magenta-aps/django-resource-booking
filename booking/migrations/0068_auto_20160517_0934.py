# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0067_auto_20160425_1145'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='resourcegrundskolefag',
            options={'ordering': ['subject__name'], 'verbose_name': 'grundskolefagtilknytning', 'verbose_name_plural': 'grundskolefagtilknytninger'},
        ),
        migrations.AlterModelOptions(
            name='resourcegymnasiefag',
            options={'ordering': ['subject__name'], 'verbose_name': 'gymnasiefagtilknytning', 'verbose_name_plural': 'gymnasiefagtilknytninger'},
        ),
        migrations.AlterModelOptions(
            name='subject',
            options={'ordering': ['name'], 'verbose_name': 'fag', 'verbose_name_plural': 'fag'},
        ),
        migrations.AddField(
            model_name='classbooking',
            name='catering_desired',
            field=models.BooleanField(default=False, verbose_name='Forplejning \xf8nsket'),
        ),
        migrations.AddField(
            model_name='classbooking',
            name='custom_desired',
            field=models.BooleanField(default=False, verbose_name='Specialtilbud \xf8nsket'),
        ),
        migrations.AddField(
            model_name='classbooking',
            name='presentation_desired',
            field=models.BooleanField(default=False, verbose_name='Opl\xe6g om uddannelse \xf8nsket'),
        ),
        migrations.AddField(
            model_name='visit',
            name='catering_available',
            field=models.BooleanField(default=False, verbose_name='Mulighed for forplejning'),
        ),
        migrations.AddField(
            model_name='visit',
            name='custom_available',
            field=models.BooleanField(default=False, verbose_name='Tilpasset mulighed'),
        ),
        migrations.AddField(
            model_name='visit',
            name='custom_name',
            field=models.CharField(max_length=50, null=True, verbose_name='Navn for tilpasset mulighed', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='presentation_available',
            field=models.BooleanField(default=False, verbose_name='Mulighed for opl\xe6g om uddannelse'),
        ),
        migrations.AlterField(
            model_name='autosend',
            name='template_key',
            field=models.IntegerField(verbose_name='Skabelon', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='booker',
            name='level',
            field=models.IntegerField(verbose_name='Niveau', choices=[(17, '0. klasse'), (7, '1. klasse'), (8, '2. klasse'), (9, '3. klasse'), (10, '4. klasse'), (11, '5. klasse'), (12, '6. klasse'), (13, '7. klasse'), (14, '8. klasse'), (15, '9. klasse'), (16, '10. klasse'), (1, '1.g'), (2, '2.g'), (3, '3.g'), (4, 'Student'), (5, 'Andet')]),
        ),
        migrations.AlterField(
            model_name='classbooking',
            name='tour_desired',
            field=models.BooleanField(default=False, verbose_name='Rundvisning \xf8nsket'),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='N\xf8gle', choices=[(1, 'Besked til g\xe6st ved booking af bes\xf8g'), (7, 'Generel besked til g\xe6st(er)'), (15, 'Reminder til g\xe6st'), (2, 'Besked til koordinatorer ved booking af bes\xf8g'), (3, 'Anmodning om deltagelse i bes\xf8g til undervisere'), (4, 'Anmodning om deltagelse i bes\xf8g til v\xe6rter'), (5, 'Notifikation til v\xe6rt om tilknytning til bes\xf8g'), (6, 'Anmodning til lokaleansvarlig om lokale'), (8, 'Besked om f\xe6rdigplanlagt bes\xf8g til alle involverede'), (9, 'Besked om aflyst bes\xf8g til alle involverede'), (10, 'Reminder om bes\xf8g til alle involverede'), (11, 'Notifikation til koordinatorer om ledig v\xe6rtsrolle p\xe5 bes\xf8g'), (12, 'Foresp\xf8rgsel fra bruger via kontaktformular'), (13, 'Svar p\xe5 e-mail fra systemet'), (14, 'Besked til bruger ved brugeroprettelse')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='state',
            field=models.IntegerField(default=0, verbose_name='Tilstand', choices=[(0, 'Kladde'), (1, 'Udgiv'), (2, 'Ikke udgivet')]),
        ),
    ]
