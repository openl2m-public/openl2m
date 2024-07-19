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
Routines to allow Netmiko communications (ie SSH) with switches
to execute various 'show' or 'display' commands
"""
import traceback
import netmiko

from django.conf import settings

from switches.connect.classes import Error
from switches.models import Switch
from switches.utils import dprint


class NetmikoExecute:
    """
    This is the base class where it all happens!
    This implements "Generic" netmiko connection to a switch
    """

    def __init__(self, switch: Switch):
        """
        Initialize the object with all the settings,
        and connect to the switch
        switch -  the Switch() class object we will connect to
        """
        dprint(f"NetmikoConnector __init__ for {switch.name} ({switch.primary_ip4})")
        self.name = "Standard Netmiko"  # what type of class is running!
        self.device_type = ''  # unknown at creation
        self.connection = False  # return from ConnectHandler()
        self.switch = switch
        # self.timeout = settings.SSH_TIMEOUT  # should be SSH timeout/retry values
        # self.retries = settings.SSH_RETRIES
        self.cmd = ''  # command to issue
        self.output = ''  # command output captured
        self.error = Error()
        self.error.status = False
        return

    def connect(self) -> bool:
        """
        Establish the connection
        return True on success, False on error,
        with self.error.status and self.error.description set accordingly
        """
        dprint("Netmiko->connect()")
        if not self.switch.netmiko_profile:
            dprint("Netmiko->connect() - No netmiko profile")
            self.error.status = True
            self.error.description = 'Switch does not have a Netmiko profile! Please ask the admin to correct this.'
            return False

        # try to connect
        device = {
            'device_type': self.switch.netmiko_profile.device_type,
            'host': self.switch.primary_ip4,
            'username': self.switch.netmiko_profile.username,
            'password': self.switch.netmiko_profile.password,
            'port': self.switch.netmiko_profile.tcp_port,
        }

        try:
            handle = netmiko.ConnectHandler(**device)
        except netmiko.NetMikoTimeoutException:
            dprint("Netmiko->connect() Error NetMikoTimeoutException")
            self.error.status = True
            self.error.description = "Connection time-out! Please ask the admin to verify the switch hostname or IP, or change the SSH_COMMAND_TIMEOUT configuration."
            return False
        except netmiko.NetMikoAuthenticationException:
            dprint("Netmiko->connect() Error NetMikoAuthenticationException")
            self.error.status = True
            self.error.description = "Access denied! Please ask the admin to correct the switch credentials."
            return False
        except netmiko.exceptions.ReadTimeout as err:
            dprint(f"  Netmiko.connection ReadTimeout: {repr(err)}")
            self.output = "Error: the connection attempt timed out!"
            self.error.status = True
            self.error.description = "Error: the connection attempt timed out!"
            self.error.details = f"Netmiko Error: {repr(err)}"
            return False
        except Exception as err:
            dprint(f"Netmiko->connect() Generic Error: {str(type(err))}")
            self.error.status = True
            self.error.description = "SSH Connection denied! Please inform your admin."
            self.error.details = f"Netmiko Error: {repr(err)} ({str(type(err))})\n{traceback.format_exc()}"
            return False

        dprint("  connection OK!")
        self.connection = handle
        return True

    def disable_paging(self) -> bool:
        """
        Disable paging, ie the "hit a key" for more
        We call the Netmiko built-in function

        Return:
            (boolean): True on success, False on error.
        """
        if not self.connection:
            dprint("  netmiko.disable_paging(): No connection yet, calling self.connect() (Huh?)")
            if not self.connect():
                return False
        if self.connection:
            if self.switch.netmiko_profile.device_type == 'hp_comware':
                command = 'screen-length disable'
            elif self.switch.netmiko_profile.device_type == 'hp_procurve':
                command = 'no page'
            else:
                # other types just use default command (defaults to Cisco)
                command = 'terminal length 0'
            try:
                self.connection.disable_paging(command)
            except Exception as err:
                self.output = f"Error disabling paging! {err}"
                return False
        return True

    def execute_command(self, command: str) -> bool:
        """
        Execute a single command on the device.
        Save the command output to self.output

        Args:
            command: the string the execute as a command on the device

        Returns:
            (boolean): True if success, False on failure.
        """
        dprint(f"NetmikoConnector execute_command() '{command}'")
        self.output = ''
        if not self.connection:
            dprint("  netmiko.execute_command(): No connection yet, calling self.connect()")
            if not self.connect():
                return False
        if self.connection:
            self.disable_paging()
            try:
                self.output = self.connection.send_command(command, read_timeout=settings.SSH_COMMAND_TIMEOUT)
            except netmiko.exceptions.ReadTimeout as err:
                dprint(f"  Netmiko.connection ReadTimeout: {repr(err)}")
                self.output = "Error: the command timed out!"
                self.error.status = True
                self.error.description = "Error: the command timed out!"
                self.error.details = f"Netmiko Error: {repr(err)}"
                return False
            except Exception as err:
                dprint(f"  Netmiko.connection error: {str(type(err))} - {repr(err)}")
                self.output = "Error sending command!"
                self.error.status = True
                self.error.description = "Error sending command!"
                self.error.details = f"Netmiko Error: {repr(err)} ({str(type(err))})"
                return False
            return True
        else:
            dprint("  Netmiko.connection not found! (Huh?)")
            self.output = "No connection found!"
            self.error.status = True
            self.error.description = "Error sending command!"
            self.error.details = "Netmiko: No Connection found!"
            return False
