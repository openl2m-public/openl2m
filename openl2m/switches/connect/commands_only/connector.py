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
"""
Commands-Only Connector: this implements an SSH connection to the devices
that is used for excuting commands only!
"""
from django.http.request import HttpRequest

from switches.connect.connector import Connector
from switches.models import Switch, SwitchGroup
from switches.utils import dprint


class CommandsOnlyConnector(Connector):
    """
    This implements a "Dummy" connector object.
    All activity here is simulated, no actual network device calls are made.
    This is purely for testing and to show how to implement a new device interface.
    """

    def __init__(self, request: HttpRequest, group: SwitchGroup, switch: Switch):
        # for now, just call the super class
        dprint("Commands-Only Connector __init__")
        super().__init__(request, group, switch)
        self.description = 'Commands-Only (Netmiko) driver'
        self.vendor_name = "Netmiko (Commands-Only)"
        # force READ-ONLY
        self.read_only = True
        if switch.description:
            self.add_more_info('System', 'Description', switch.description)
        self.show_interfaces = False  # do NOT show interfaces, vlans etc...

    def get_my_basic_info(self) -> bool:
        """
        placeholder, we are not actually gathering information here
        Implemented to surpress the warning if not implemented.
        """
        dprint("Commands-Only Connector get_my_basic_info()")
        self.hostname = self.switch.hostname
        return True
