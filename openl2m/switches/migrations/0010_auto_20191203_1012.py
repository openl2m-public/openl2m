# Generated by Django 2.2.8 on 2019-12-03 18:12

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('switches', '0009_auto_20191202_1521'),
    ]

    operations = [
        migrations.AlterField(
            model_name='log',
            name='action',
            field=models.PositiveSmallIntegerField(choices=[[0, 'View Switch Groups'], [1, 'View Switch'], [2, 'View Interface'], [3, 'View PoE'], [4, 'View Vlans'], [5, 'View LLDP'], [6, 'Viewing All Logs'], [7, 'Viewing Site Statistics'], [100, 'Reloading Switch Data'], [101, 'New System ObjectID Found'], [102, 'New System Name Found'], [90, 'Login'], [91, 'Logout'], [92, 'Inactivity Logout'], [93, 'Login Failed'], [103, 'Interface Disable'], [104, 'Interface Enable'], [105, 'Interface Toggle'], [106, 'Interface PoE Disable'], [107, 'Interface PoE Enable'], [108, 'Interface PoE Toggle'], [109, 'Interface PVID Vlan Change'], [110, 'Interface Description Change'], [111, 'Saving Configuration'], [112, 'Execute Command'], [113, 'Port PoE Fault'], [114, 'LDAP New SwitchGroup'], [115, 'Bulk Edit'], [256, 'Undefined Vlan'], [257, 'Vlan Name Mismatch'], [258, 'SNMP Error'], [259, 'LDAP User->SwitchGroup Error'], [260, 'LDAP SwitchGroup Error']], default=1, verbose_name='Activity or Action to log'),
        ),
        migrations.AlterField(
            model_name='log',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
