# Generated by Django 3.1.5 on 2021-01-04 23:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('switches', '0016_auto_20210104_1444'),
    ]

    operations = [
        migrations.AlterField(
            model_name='switch',
            name='hostname',
            field=models.CharField(blank=True, default='', help_text='The switch hostname as reported via snmp, ssh, etc.', max_length=64, null=True, verbose_name='Hostname'),
        ),
    ]
