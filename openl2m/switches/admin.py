#
# This file is part of Open Layer 2 Management (OpenL2M).
#
# OpenL2M is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with OpenL2M. If not, see <http://www.gnu.org/licenses/>.
#
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
# local copy of django-ordered-model, with some fixes:
# from libraries.django_ordered_model.ordered_model.admin import OrderedStackedInline, OrderedTabularInline, OrderedInlineModelAdminMixin
from ordered_model.admin import OrderedStackedInline, OrderedTabularInline, OrderedInlineModelAdminMixin

# Register your models here.
from switches.models import (Command, CommandList, CommandTemplate, Switch, SwitchGroup, SwitchGroupMembership,
                             SnmpProfile, NetmikoProfile, VLAN, VlanGroup, Task)

# register with the custom admin site
from openl2m.admin import admin_site


# See:
# https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.filter_horizontal
#

# Change the Switch admin display to add the list of groups where this is used:
class SwitchInline(admin.TabularInline):
    model = SwitchGroup.switches.through


# Change the Switch admin page to show horizontal listing of selected Switch Groups:
# class SwitchAdmin(admin.StackedInline):
class SwitchAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'get_switchgroups')
    readonly_fields = ('hostname', 'snmp_oid', )
    filter_horizontal = ('command_templates', )
    search_fields = ['name']
    inlines = (SwitchInline,)


# class SwitchGroupMembershipStackedInline(OrderedStackedInline):
class SwitchGroupMembershipStackedInline(OrderedTabularInline):
    model = SwitchGroupMembership
    fields = ('switch', 'order', 'move_up_down_links',)
    readonly_fields = ('order', 'move_up_down_links',)
    extra = 1
    ordering = ('order',)


# Change the SwitchGroup admin page to show horizontal listing of selected items:
class SwitchGroupAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    # we just want all fields:
    # list_display = ('name', )
    search_fields = ['name']
    filter_horizontal = ('users', 'vlan_groups', 'vlans')
    list_display = ('name', 'get_switchgroup_users')
    # inlines = (SwitchGroupSwitchesThroughModelTabularInline, )
    inlines = (SwitchGroupMembershipStackedInline, )


# Change the VLAN() admin display to add the list of groups where this is used:
class VlanInline(admin.TabularInline):
    model = VlanGroup.vlans.through


class VlanSwitchInline(admin.TabularInline):
    model = SwitchGroup.vlans.through


# Change the VLAN() admin page to show horizontal listing of selected VLAN Groups:
class VLANAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['name', 'vid']
    # we just want all fields:
    # list_display = ('name', 'vid', 'description')
    inlines = (VlanInline, VlanSwitchInline)


# Change the VlanGroup() admin display to add the list of groups where this is used:
class VlanGroupInline(admin.TabularInline):
    model = SwitchGroup.vlan_groups.through


# Change the VLAN admin page to show horizontal listing of selected VLAN Groups:
class VlanGroupAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['name']
    filter_horizontal = ('vlans',)
    # we just want all fields:
    # list_display = ('name', 'vid', 'description')
    inlines = (VlanGroupInline, )


class SnmpProfileAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['name']


class NetmikoProfileAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['name']


class CommandAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['name']


class CommandListAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['name']
    filter_horizontal = ('global_commands', 'interface_commands', 'global_commands_staff', 'interface_commands_staff',)


class CommandTemplateAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['name']
    fieldsets = (
        (None, {
            'fields': ('name', 'os', 'description', 'template')
        }),
        ('Field 1', {
            'fields': ('field1_name', 'field1_description', 'field1_regex'),
        }),
        ('Field 2', {
            'fields': ('field2_name', 'field2_description', 'field2_regex'),
        }),
        ('Field 3', {
            'fields': ('field3_name', 'field3_description', 'field3_regex'),
        }),
        ('Field 4', {
            'fields': ('field4_name', 'field4_description', 'field4_regex'),
        }),
        ('Field 5', {
            'fields': ('field5_name', 'field5_description', 'field5_regex'),
        }),
        ('Field 6', {
            'fields': ('field6_name', 'field6_description', 'field6_regex'),
        }),
        ('Field 7', {
            'fields': ('field7_name', 'field7_description', 'field7_regex'),
        }),
        ('Field 8', {
            'fields': ('field8_name', 'field8_description', 'field8_regex'),
        }),
        ('List 1', {
            'fields': ('list1_name', 'list1_description', 'list1_values'),
        }),
        ('List 2', {
            'fields': ('list2_name', 'list2_description', 'list2_values'),
        }),
        ('List 3', {
            'fields': ('list3_name', 'list3_description', 'list3_values'),
        }),
        ('List 4', {
            'fields': ('list4_name', 'list4_description', 'list4_values'),
        }),

    )


class TaskAdmin(admin.ModelAdmin):
    search_fields = ['description', 'user', 'group', 'switch']
    # we want all fields read-only:
    # readonly_fields = []

    def has_change_permission(self, request, obj=None):
        return False


# Register your models here.
admin_site.register(Switch, SwitchAdmin)
admin_site.register(SwitchGroup, SwitchGroupAdmin)
admin_site.register(VLAN, VLANAdmin)
admin_site.register(VlanGroup, VlanGroupAdmin)
admin_site.register(SnmpProfile, SnmpProfileAdmin)
admin_site.register(NetmikoProfile, NetmikoProfileAdmin)
admin_site.register(Command, CommandAdmin)
admin_site.register(CommandList, CommandListAdmin)
admin_site.register(CommandTemplate, CommandTemplateAdmin)
admin_site.register(Task, TaskAdmin)
