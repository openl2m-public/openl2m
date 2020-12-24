# Generated by Django 3.1.5 on 2021-02-01 21:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('switches', '0017_auto_20210104_1520'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='switch',
            name='snmp_bulk_read_count',
        ),
        migrations.RemoveField(
            model_name='switch',
            name='snmp_capabilities',
        ),
        migrations.RemoveField(
            model_name='switch',
            name='snmp_read_count',
        ),
        migrations.RemoveField(
            model_name='switch',
            name='snmp_write_count',
        ),
        migrations.AddField(
            model_name='switch',
            name='details_read_count',
            field=models.PositiveIntegerField(default=0, help_text='Details read count performed on the switch.', verbose_name='Details(arp/lldp) Reads'),
        ),
        migrations.AddField(
            model_name='switch',
            name='read_count',
            field=models.PositiveIntegerField(default=0, help_text='Basic read count performed on the switch.', verbose_name='Reads'),
        ),
        migrations.AddField(
            model_name='switch',
            name='write_count',
            field=models.PositiveIntegerField(default=0, help_text='Write count performed on the switch.', verbose_name='Writes'),
        ),
    ]
