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
Cisco specific implementation of the SNMP Connection object.
This augments/re-implements some methods found in the base SNMP() class
with Cisco specific ways of doing things...
"""
import random
import time
from django.conf import settings

from switches.models import Log
from switches.constants import *
from switches.connect.classes import *
from switches.connect.snmp import SnmpConnector, oid_in_branch
from switches.utils import *

from .constants import *


class SnmpConnectorCisco(SnmpConnector):
    """
    CISCO specific implementation of the base SNMP class.
    We override various functions as needed for the Cisco way of doing things.
    """

    def __init__(self, request, group, switch):
        # for now, just call the super class
        dprint("CISCO SnmpConnector __init__")
        super().__init__(request, group, switch)
        self.vendor_name = "Cisco"

    def _parse_oid(self, oid, val):
        """
        Parse a single OID with data returned from a switch through some "get" function
        THIS NEEDS WORK TO IMPROVE PERFORMANCE !!!
        Returns True if we parse the OID and we should cache it!
        """
        dprint(f"CISCO Parsing OID {oid}")

        if_index = oid_in_branch(vmVoiceVlanId, oid)
        if if_index:
            voiceVlanId = int(val)
            iface = self.get_interface_by_key(if_index)
            if iface and voiceVlanId in self.vlans.keys():
                iface.voice_vlan = voiceVlanId
            return True

        """
        Stack-MIB PortId to ifIndex mapping
        """
        stack_port_id = oid_in_branch(portIfIndex, oid)
        if stack_port_id:
            self.stack_port_to_if_index[stack_port_id] = int(val)
            return True

        if self._parse_mibs_cisco_vtp(oid, val):
            return True

        if self._parse_mibs_cisco_poe(oid, val):
            return True

        if self._parse_mibs_cisco_config(oid, val):
            return True

        if self._parse_mibs_cisco_if_opermode(oid, val):
            return True

        if self._parse_mibs_cisco_syslog_msg(oid, val):
            return True

        # if not Cisco specific, call the generic parser
        return super()._parse_oid(oid, val)

    def _get_interface_data(self):
        """
        Implement an override of the interface parsing routine,
        so we can add Cisco specific interface MIBs
        """
        # first call the base class to populate interfaces:
        super()._get_interface_data()

        # now add Comware data, and cache it:
        if self.get_branch_by_name('cL2L3IfModeOper', True, self._parse_mibs_cisco_if_opermode) < 0:
            dprint("Cisco cL2L3IfModeOper returned error!")
            return False

        return True

    def _get_vlan_data(self):
        """
        Implement an override of vlan parsing to read Cisco specific MIB
        Return 1 on success, -1 on failure
        """
        dprint("_get_vlan_data(Cisco)\n")
        # first, read existing vlan id's
        retval = self.get_branch_by_name('vtpVlanState', True, self._parse_mibs_cisco_vtp)
        if retval < 0:
            return retval
        # vlan types are next
        retval = self.get_branch_by_name('vtpVlanType', True, self._parse_mibs_cisco_vtp)
        if retval < 0:
            return retval
        # next, read vlan names
        retval = self.get_branch_by_name('vtpVlanName', True, self._parse_mibs_cisco_vtp)
        if retval < 0:
            return False
        # find out if a port is configured as trunk or not, read port trunk(802.1q tagged) status
        retval = self.get_branch_by_name('vlanTrunkPortDynamicState', True, self._parse_mibs_cisco_vtp)
        if retval < 0:
            return False
        # now, find out if interfaces are access or trunk (tagged) mode
        # this is the actual status, not what is configured; ie NOT trunk if interface is down!!!
        # retval = self.get_branch_by_name(vlanTrunkPortDynamicStatus):  # read port trunk(802.1q tagged) status
        #    dprint("Cisco PORT TRUNK STATUS data FALSE")
        #    return False
        # and read the native vlan for trunked ports
        retval = self.get_branch_by_name('vlanTrunkPortNativeVlan', True, self._parse_mibs_cisco_vtp)  # read trunk native vlan membership
        if retval < 0:
            return False
        # finally, if not trunked, read untagged interfaces vlan membership
        retval = self.get_branch_by_name('vmVlan')
        if retval < 0:
            return False
        # and just for giggles, read Voice vlan
        retval = self.get_branch_by_name('vmVoiceVlanId')
        if retval < 0:
            return False

        return 1

    def _get_known_ethernet_addresses(self):
        """
        Read the Bridge-MIB for known ethernet address on the switch.
        On Cisco switches, you have to append the vlan ID after the v1/2c community,
        eg. public@13 for vlan 13
        Return 1 on success, -1 on failure
        """
        dprint("_get_known_ethernet_addresses(Cisco)\n")
        for vlan_id in self.vlans.keys():
            # little hack for Cisco devices, to see various vlan-specific tables:
            self.vlan_id_context = int(vlan_id)
            com_or_ctx = ''
            if self.switch.snmp_profile.version == SNMP_VERSION_2C:
                # for v2, set community string to "Cisco format"
                com_or_ctx = f"{self.switch.snmp_profile.community}@{vlan_id}"
            else:
                # v3, set context to "Cisco format":
                com_or_ctx = f"vlan-{vlan_id}"
            self._set_snmp_session(com_or_ctx)
            # first map Q-Bridge ports to ifIndexes:
            retval = self.get_branch_by_name('dot1dBasePortIfIndex')
            if retval < 0:
                return retval
            # next, read the known ethernet addresses, and add to the Interfaces
            retval = self.get_branch_by_name('dot1dTpFdbPort', False, self._parse_mibs_dot1d_bridge_eth)
            if retval < 0:
                return False
        # reset the snmp session back!
        self.vlan_id_context = 0
        self._set_snmp_session()
        return True

    def _get_poe_data(self):
        """
        Implement reading Cisco-specific PoE mib.
        Returns 1 on success, -1 on failure
        """
        dprint("_get_poe_data(Cisco)\n")

        # get Cisco Stack MIB port to ifIndex map first
        # this may be used to find the POE port index
        retval = self.get_branch_by_name('portIfIndex')
        if retval < 0:
            return retval

        # check to see if standard PoE MIB is supported
        retval = super()._get_poe_data()
        if retval < 0:
            return retval

        # probe Cisco specific Extended POE mibs to add data
        # this is what is shown via "show power inline" command:
        retval = self.get_branch_by_name('cpeExtPsePortPwrAvailable')
        if retval < 0:
            return retval
        # this is the consumed power, shown in 'show power inline <name> detail'
        retval = self.get_branch_by_name('cpeExtPsePortPwrConsumption')
        if retval < 0:
            return retval
        # max power consumed since interface power reset
        retval = self.get_branch_by_name('cpeExtPsePortMaxPwrDrawn')
        return retval

    def _get_syslog_msgs(self):
        """
        Read the CISCO-SYSLOG-MSG-MIB
        """
        retval = self.get_branch_by_name('ciscoSyslogMIBObjects', True, self._parse_mibs_cisco_syslog_msg)
        if retval < 0:
            # something bad happened
            self.add_warning("Error getting Cisco Syslog Messages (ciscoSyslogMIBObjects)")
            self.log_error()
            return 0    # for now

    def _map_poe_port_entries_to_interface(self):
        """
        This function maps the "pethPsePortEntry" indices that are stored in self.poe_port_entries{}
        to interface ifIndex values, so we can store them with the interface and display as needed.
        If we have found the Cisco-Stack-Mib 'portIfIndex' table, we use it to map to ifIndexes.
        If not, we use the generic approach, as it appears the port entry is in the format "modules.port"
        In general, you can generate the interface ending "x/y" from the index by substituting "." for "/"
        E.g. "5.12" from the index becomes "5/12", and you then search for an interface with matching ending
        e.g. GigabitEthernet5/12
        """
        for (pe_index, port_entry) in self.poe_port_entries.items():
            if len(self.stack_port_to_if_index) > 0:
                if pe_index in self.stack_port_to_if_index.keys():
                    if_index = str(self.stack_port_to_if_index[pe_index])
                    iface = self.get_interface_by_key(if_index)
                    if iface:
                        iface.poe_entry = port_entry
                        if port_entry.detect_status == POE_PORT_DETECT_FAULT:
                            warning = f"PoE FAULT status ({port_entry.detect_status} = {poe_status_name[port_entry.detect_status]}) on interface {iface.name}"
                            self.add_warning(warning)
                            # log my activity
                            log = Log(user=self.request.user,
                                      type=LOG_TYPE_ERROR,
                                      ip_address=get_remote_ip(self.request),
                                      action=LOG_PORT_POE_FAULT,
                                      description=warning)
                            log.save()

            else:
                # map "mod.port" to "mod/port"
                end = port_entry.index.replace('.', '/')
                count = len(end)
                for (if_index, iface) in self.interfaces.items():
                    if iface.name[-count:] == end:
                        iface.poe_entry = port_entry
                        if port_entry.detect_status == POE_PORT_DETECT_FAULT:
                            warning = f"PoE FAULT status ({port_entry.status_name}) on interface {iface.name}"
                            self.add_warning(warning)
                            # log my activity
                            log = Log(user=self.request.user,
                                      type=LOG_TYPE_ERROR,
                                      ip_address=get_remote_ip(request),
                                      action=LOG_PORT_POE_FAULT,
                                      description=warning)
                            log.save()
                        break

    def set_interface_untagged_vlan(self, interface, new_vlan_id):
        """
        Override the VLAN change, this is done Cisco specific using the VTP MIB
        Returns True or False
        """
        dprint("set_interface_untagged_vlan(Cisco)")
        if interface:
            if interface.is_tagged:
                # set the TRUNK_NATIVE_VLAN OID:
                retval = self.set(f"{vlanTrunkPortNativeVlan}.{interface.index}", int(new_vlan_id), "i")
            else:
                # regular access mode port:
                retval = self.set(f"{vmVlan}.{interface.index}", int(new_vlan_id), "i")
                if retval < 0:
                    # some Cisco devices want unsigned integer value:
                    retval = self.set(f"{vmVlan}.{interface.index}", int(new_vlan_id), "u")
            if retval == -1:
                return False
            else:
                return True
        # interface not found:
        return False

    def get_more_info(self):
        """
        Implement the get_more_info() class from the base object.
        Does not return anything.
        """
        dprint("get_more_info(Cisco)")
        self.get_branch_by_name('ccmHistory', True, self._parse_mibs_cisco_config)

    def _parse_mibs_cisco_if_opermode(self, oid, val):
        """
        Parse Cisco specific Interface Config MIB for operational mode
        """
        if_index = oid_in_branch(cL2L3IfModeOper, oid)
        if if_index:
            dprint(f"Cisco Interface Operation mode if_index {if_index} mode {val}")
            if int(val) == CISCO_ROUTE_MODE:
                self.set_interface_attribute_by_key(if_index, "is_routed", True)
            return True
        return False

    def _parse_mibs_cisco_poe(self, oid, val):
        """
        Parse Cisco POE Extension MIB database
        """
        # the actual consumed power, shown in 'show power inline <name> detail'
        pe_index = oid_in_branch(cpeExtPsePortPwrConsumption, oid)
        if pe_index:
            if pe_index in self.poe_port_entries.keys():
                self.poe_port_entries[pe_index].power_consumption_supported = True
                self.poe_port_entries[pe_index].power_consumed = int(val)
            return True

        # this is what is shown via 'show power inline interface X' command:
        pe_index = oid_in_branch(cpeExtPsePortPwrAvailable, oid)
        if pe_index:
            if pe_index in self.poe_port_entries.keys():
                self.poe_port_entries[pe_index].power_consumption_supported = True
                self.poe_port_entries[pe_index].power_available = int(val)
            return True

        pe_index = oid_in_branch(cpeExtPsePortMaxPwrDrawn, oid)
        if pe_index:
            if pe_index in self.poe_port_entries.keys():
                self.poe_port_entries[pe_index].power_consumption_supported = True
                self.poe_port_entries[pe_index].max_power_consumed = int(val)
            return True

        return False

    def _parse_mibs_cisco_vtp(self, oid, val):
        """
        Parse Cisco specific VTP MIB
        """
        # vlan id
        vlan_id = int(oid_in_branch(vtpVlanState, oid))
        if vlan_id:
            if (int(val) == 1):
                self.vlans[vlan_id] = Vlan(vlan_id)
            return True

        # vlan type
        vlan_id = int(oid_in_branch(vtpVlanType, oid))
        if vlan_id:
            type = int(val)
            if vlan_id in self.vlans.keys():
                if type == CISCO_VLAN_TYPE_NORMAL:
                    self.vlans[vlan_id].type = VLAN_TYPE_NORMAL
                else:
                    self.vlans[vlan_id].type = type
            return True

        # vlan name
        vlan_id = int(oid_in_branch(vtpVlanName, oid))
        if vlan_id:
            if vlan_id in self.vlans.keys():
                self.vlans[vlan_id].name = str(val)
            return True

        # access or trunk mode configured?
        if_index = oid_in_branch(vlanTrunkPortDynamicState, oid)
        if if_index:
            if(int(val) == VTP_TRUNK_STATE_ON):
                # trunk/tagged port
                self.set_interface_attribute_by_key(if_index, "is_tagged", True)
            return True

        # access or trunk mode actual status?
        # this is the actual status, not what is configured; ie NOT trunk if interface is down!!!
        # if_index = oid_in_branch(vlanTrunkPortDynamicStatus, oid)
        # if if_index:
        #    dprint(f"Cisco PORT TRUNK STATUS ifIndex {if_index} = {val}")
        #    if(int(val) == VTP_PORT_TRUNK_ENABLED):
        #        # trunk/tagged port
        #        dprint("  TRUNKED!")
        #        self.set_interface_attribute_by_key(if_index, "is_tagged", True)
        #    return True

        # if trunk, what is the native mode?
        if_index = oid_in_branch(vlanTrunkPortNativeVlan, oid)
        if if_index:
            # trunk/tagged port native vlan
            iface = self.get_interface_by_key(if_index)
            if iface:
                # make sure this is a trunked interface and vlan is valid
                if iface.is_tagged and int(val) in self.vlans.keys():
                    iface.untagged_vlan = int(val)
                else:
                    dprint("  TRUNK NATIVE found, but NOT TRUNK PORT")
            return True

        if_index = oid_in_branch(vmVlan, oid)
        if if_index:
            iface = self.get_interface_by_key(if_index)
            if iface:
                untagged_vlan = int(val)
                if not iface.is_tagged and untagged_vlan in self.vlans.keys():
                    iface.untagged_vlan = untagged_vlan
                    iface.untagged_vlan_name = self.vlans[untagged_vlan].name
            else:
                dprint("   UNTAGGED VLAN for invalid trunk port")
            return True

        return False

    def _parse_mibs_cisco_config(self, oid, val):
        """
        Parse Cisco specific ConfigMan MIBs for running-config info
        This gets added to the Information tab!
        """
        sub_oid = oid_in_branch(ccmHistoryRunningLastChanged, oid)
        if sub_oid:
            # ticks in 1/100th of a second
            ago = str(datetime.timedelta(seconds=(int(val) / 100)))
            self.add_more_info("Configuration", "Running Last Modified", ago)
            return True

        sub_oid = oid_in_branch(ccmHistoryRunningLastSaved, oid)
        if sub_oid:
            # ticks in 1/100th of a second
            ago = str(datetime.timedelta(seconds=(int(val) / 100)))
            self.add_more_info("Configuration", "Running Last Saved", ago)
            return True

        sub_oid = oid_in_branch(ccmHistoryStartupLastChanged, oid)
        if sub_oid:
            # ticks in 1/100th of a second
            ago = str(datetime.timedelta(seconds=(int(val) / 100)))
            self.add_more_info("Configuration", "Startup Last Changed", ago)
            return True
        return False

    def _parse_mibs_cisco_syslog_msg(self, oid, val):
        """
        Parse Cisco specific Syslog MIB to read syslog messages stored.
        """
        sub_oid = oid_in_branch(clogHistTableMaxLength, oid)
        if sub_oid:
            # this is the max number of syslog messages stored.
            self.syslog_max_msgs = int(val)
            return True

        sub_oid = oid_in_branch(clogHistIndex, oid)
        if sub_oid:
            # this is the index, create a new object.
            # note that not all implementation return this value, as it is implied in the other entries!
            index = int(sub_oid)
            self.syslog_msgs[index] = SyslogMsg(index)
            return True

        sub_oid = oid_in_branch(clogHistFacility, oid)
        if sub_oid:
            # verify we have an object for this index
            index = int(sub_oid)
            if index in self.syslog_msgs.keys():
                self.syslog_msgs[index].facility = val
            else:
                msg = SyslogMsg(index)
                msg.facility = val
                self.syslog_msgs[index] = msg
            return True

        # from this point on we "should" have the object created!
        sub_oid = oid_in_branch(clogHistSeverity, oid)
        if sub_oid:
            # verify we have an object for this index
            index = int(sub_oid)
            if index in self.syslog_msgs.keys():
                self.syslog_msgs[index].severity = int(val)
            else:
                # be save, create; "should" never happen
                msg = SyslogMsg(index)
                msg.severity = int(val)
                self.syslog_msgs[index] = msg
            return True

        sub_oid = oid_in_branch(clogHistMsgName, oid)
        if sub_oid:
            # verify we have an object for this index
            index = int(sub_oid)
            if index in self.syslog_msgs.keys():
                self.syslog_msgs[index].name = val
            else:
                # be save, create; "should" never happen
                msg = SyslogMsg(index)
                msg.name = val
                self.syslog_msgs[index] = msg
            return True

        sub_oid = oid_in_branch(clogHistMsgText, oid)
        if sub_oid:
            # verify we have an object for this index
            index = int(sub_oid)
            if index in self.syslog_msgs.keys():
                self.syslog_msgs[index].message = val
            else:
                # be save, create; "should" never happen
                msg = SyslogMsg(index)
                msg.message = val
                self.syslog_msgs[index] = msg
            return True

        sub_oid = oid_in_branch(clogHistTimestamp, oid)
        if sub_oid:
            # verify we have an object for this index
            index = int(sub_oid)
            # val is sysUpTime value when message was generated, ie. timetick!
            timetick = int(val)
            if index in self.syslog_msgs.keys():
                # approximate / calculate the datetime value:
                # msg timestamp = time when sysUpTime was read minus seconds between sysUptime and msg timetick
                dprint(f"TIMES ARE: {self.sys_uptime_timestamp}  {self.sys_uptime}  {timetick}")
                self.syslog_msgs[index].datetime = datetime.datetime.fromtimestamp(self.sys_uptime_timestamp - int((self.sys_uptime - timetick)/100))
            else:
                # be save, create; "should" never happen
                msg = SyslogMsg(index)
                # approximate / calculate the datetime value:
                # msg time = time when sysUpTime was read minus seconds between sysUptime and msg timetick
                msg.datetime = datetime.datetime.fromtimestamp(self.time - int((self.sys_uptime - timetick)/100))
                self.syslog_msgs[index] = msg
            return True

        return False

    def can_save_config(self):
        """
        If True, this instance can save the running config to startup
        Ie. "write mem" is implemented via an SNMP interfaces
        """
        return True

    def save_running_config(self):
        """
        Cisco interface to save the current config to startup
        Returns 0 is this succeeds, -1 on failure. self.error() will be set in that case
        """
        dprint("\nCISCO save_running_config()\n")
        # set this OID, but do not update local cache.
        # first try old method, prios to IOS 12. This work on older 29xx and similar switches
        retval = self._set(oid=ciscoWriteMem, value=int(1), snmp_type='i', update_oidcache=False)
        if retval == -1:
            # error occured, most likely timeout. Try Cisco-CONFIG-COPY mib
            dprint("   Trying CONFIG-COPY method")
            some_number = random.randint(1, 254)
            # first, set source to running config
            retval = self._set(oid=f"{ccCopySourceFileType}.{some_number}",
                               value=int(runningConfig),
                               snmp_type='i',
                               update_oidcache=False)
            # next, set destination to startup co -=nfig
            retval = self._set(oid=f"{ccCopyDestFileType}.{some_number}",
                               value=int(startupConfig),
                               snmp_type="i",
                               update_oidcache=False)
            # and then activate the copy:
            retval = self._set(oid=f"{ccCopyEntryRowStatus}.{some_number}",
                               value=int(rowStatusActive),
                               snmp_type="i",
                               update_oidcache=False)
            # now wait for this row to return success or fail:
            waittime = settings.CISCO_WRITE_MEM_MAX_WAIT
            while(waittime):
                time.sleep(1)
                (error_status, snmp_ret) = self._get(oid=f"{ccCopyState}.{some_number}",
                                                     update_oidcache=False)
                if error_status:
                    break
                if int(snmp_ret.value) == copyStateSuccess:
                    # write completed, so we are done!
                    return 0
                if int(snmp_ret.value) == copyStateFailed:
                    break
                waittime -= 1

            # we timed-out, or errored-out
            self.error.status = True
            if error_status:
                self.error.description = "SNMP get copy-status returned error! (no idea why?)"
            elif snmp_ret.value == copyStateFailed:
                self.error.description = "Copy running to startup failed!"
            elif snmp_ret.value == copyStateRunning:
                self.error.description = "Copy running to startup not completed yet! (huh?)"
            elif snmp_ret.value == copyStateWaiting:
                self.error.description = "Copy running to startup still waiting! (for what?)"
            # log error
            log = Log(user=self.request.user,
                      type=LOG_TYPE_ERROR,
                      ip_address=get_remote_ip(self.request),
                      action=LOG_SAVE_SWITCH,
                      description=self.error.description)
            log.save()
            # return error status
            return -1

        # the original or new-style write-mem worked.
        return 0
