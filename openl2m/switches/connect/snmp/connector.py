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
SNMP Library for OpenL2M, based on MIB-2 based RFC standards. Uses the pysnmp library.
Some of the code here is inspired by the NAV (Network Administration Visualized) tool
Various vendor specific implementations that augment this class exist.
"""
import datetime
import ezsnmp
import pprint
import time
from typing import Dict
import traceback

from django.conf import settings
from django.http.request import HttpRequest

# note that we use v3 of the new pysnmp HLAPI. This uses asyncio, instead of the old synchronous.
# see https://docs.lextudio.com/pysnmp/v7.1/
import asyncio
from pysnmp.hlapi.v3arch.asyncio import (
    # get_cmd,
    set_cmd,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    SnmpEngine,
    CommunityData,
    UsmUserData,
    usmHMACSHAAuthProtocol,
    usmHMAC128SHA224AuthProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMAC256SHA384AuthProtocol,
    usmHMAC384SHA512AuthProtocol,
    usmHMACMD5AuthProtocol,
    usmAesCfb128Protocol,
    usmAesCfb192Protocol,
    usmAesCfb256Protocol,
    usmAesBlumenthalCfb192Protocol,
    usmAesBlumenthalCfb256Protocol,
    usmDESPrivProtocol,
)
from pysnmp.proto.rfc1902 import ObjectName, OctetString

from switches.constants import (
    LOG_TYPE_ERROR,
    LOG_TYPE_WARNING,
    LOG_SNMP_ERROR,
    LOG_UNDEFINED_VLAN,
    LOG_NEW_HOSTNAME_FOUND,
    SNMP_VERSION_2C,
    SNMP_VERSION_3,
    SNMP_V3_SECURITY_NOAUTH_NOPRIV,
    SNMP_V3_SECURITY_AUTH_NOPRIV,
    SNMP_V3_AUTH_MD5,
    SNMP_V3_AUTH_SHA,
    SNMP_V3_AUTH_SHA224,
    SNMP_V3_AUTH_SHA256,
    SNMP_V3_AUTH_SHA384,
    SNMP_V3_AUTH_SHA512,
    SNMP_V3_PRIV_AES,
    SNMP_V3_PRIV_DES,
    SNMP_V3_PRIV_AES192,
    SNMP_V3_PRIV_AES256,
    SNMP_V3_PRIV_AES192C,
    SNMP_V3_PRIV_AES256C,
    SNMP_V3_SECURITY_AUTH_PRIV,
)
from switches.models import Log, Switch, SwitchGroup
from switches.utils import dprint, get_remote_ip

from switches.connect.utils import get_vlan_id_from_l3_interface

# from switches.connect.snmp.utils import *
from switches.connect.constants import (
    IF_TYPE_ETHERNET,
    IF_TYPE_LAGG,
    LACP_IF_TYPE_AGGREGATOR,
    LACP_IF_TYPE_MEMBER,
    LLDP_CHASSIS_TYPE_NONE,
    LLDP_CHASSIC_TYPE_ETH_ADDR,
    LLDP_CHASSIC_TYPE_NET_ADDR,
    LLDP_PORT_SUBTYPE_CHASSIS_COMPONENT,
    LLDP_PORT_SUBTYPE_PORT_COMPONENT,
    LLDP_PORT_SUBTYPE_LOCAL,
    GVRP_ENABLED,
    ENTITY_CLASS_STACK,
    ENTITY_CLASS_CHASSIS,
    ENTITY_CLASS_MODULE,
    IANA_TYPE_IPV4,
    IANA_TYPE_IPV6,
    POE_PORT_ADMIN_ENABLED,
    POE_PORT_ADMIN_DISABLED,
)
from switches.connect.classes import (
    Error,
    Interface,
    StackMember,
    PoePSE,
    PoePort,
    EthernetAddress,
    NeighborDevice,
    PortList,
    Vlan,
)

# from switches.connect.connect import *
from switches.connect.connector import Connector
from switches.connect.snmp.utils import decimal_to_hex_string_ethernet, bytes_ethernet_to_string, get_ip_from_oid_index
from switches.connect.snmp.constants import (
    snmp_mib_variables,
    ifIndex,
    ifDescr,
    ifType,
    ifMtu,
    ifSpeed,
    ifPhysAddress,
    ifAdminStatus,
    ifOperStatus,
    ifName,
    ifAlias,
    ifHighSpeed,
    sysName,
    sysUpTime,
    sysObjectID,
    sysDescr,
    sysContact,
    sysLocation,
    dot3StatsDuplexStatus,
    dot1qTpFdbPort,
    dot1qNumVlans,
    dot1qGvrpStatus,
    dot1qPortGvrpStatus,
    dot1qVlanCurrentEgressPorts,
    dot1qVlanStatus,
    dot1qVlanStaticEgressPorts,
    dot1qVlanStaticName,
    dot1qVlanStaticUntaggedPorts,
    dot1qVlanStaticRowStatus,
    dot1qPvid,
    dot1dBasePortIfIndex,
    ipAdEntIfIndex,
    ipAdEntNetMask,
    entPhysicalClass,
    entPhysicalDescr,
    entPhysicalSerialNum,
    entPhysicalSoftwareRev,
    entPhysicalModelName,
    syslogMsgTableMaxSize,
    pethMainPsePower,
    pethMainPseOperStatus,
    pethMainPseConsumptionPower,
    pethMainPseUsageThreshold,
    pethPsePortAdminEnable,
    pethPsePortDetectionStatus,
    dot3adAggActorAdminKey,
    dot3adAggPortActorAdminKey,
    ieee8021QBridgeMvrpEnabledStatus,
    ieee8021QBridgeVlanStaticName,
    ieee8021QBridgePortVlanEntry,
    ieee8021QBridgeVlanCurrentEgressPorts,
    ieee8021QBridgeVlanCurrentUntaggedPorts,
    dot1dTpFdbPort,
    ipNetToMediaPhysAddress,
    ipNetToPhysicalPhysAddress,
    ipAddressIfIndex,
    lldpRemChassisId,
    lldpRemPortId,
    lldpRemPortIdSubType,
    lldpRemPortDesc,
    lldpRemSysName,
    lldpRemSysDesc,
    lldpRemSysCapEnabled,
    lldpRemChassisIdSubtype,
    lldpRemManAddrIfSubtype,
    LLDP_REM_MAN_ADDR_TYPE_IFINDEX,
    LLDP_REM_MAN_ADDR_TYPE_SYSTEMPORTNUMBER,
    enterprises,
    enterprise_id_info,
    IF_ADMIN_STATUS_UP,
    IF_OPER_STATUS_UP,
    IF_OPER_STATUS_DOWN,
    vlan_createAndGo,
    vlan_destroy,
    mplsL3VpnVrfName,
    mplsL3VpnVrfDescription,
    mplsL3VpnVrfRD,
    mplsL3VpnVrfOperStatus,
    mplsL3VpnVrfActiveInterfaces,
    MPLS_VRF_STATE_ENABLED,
    mplsL3VpnIfVpnClassification,
    mplsL3VpnIfVpnRouteDistProtocol,
)


class pysnmpHelper:
    """
    Implement functionality we need to do a few simple things to handle snmp data objects
    that are OctetString / BitMap values.

    We use the "pysnmp" library for this, as ezsnmp cannot handle this cleanly,
    especially for uneven byte counts, due to how it maps everything to a unicode string internally!

    Based on the (new) async pysnmp HLAPI version 3 at
        https://docs.lextudio.com/pysnmp/v7.1/docs/api-reference
    with examples at
        https://docs.lextudio.com/pysnmp/v7.1/examples/
    """

    def __init__(self, switch: Switch):
        """
        Initialize the PySnmp bindings
        """
        self.switch = switch  # the Switch() object
        self.error = Error()
        if not self._set_auth_data():
            # cannot set auth data, throw an exception:
            raise Exception(f"{self.error.description}: {self.error.details}")

    # async def run_get(self, oid: str):

    #     snmpEngine = SnmpEngine()

    #     # Get a variable using an SNMP GET
    #     iterator = get_cmd(
    #         snmpEngine,
    #         self._auth_data,
    #         UdpTransportTarget((self.switch.primary_ip4, self.switch.snmp_profile.udp_port)).create(),
    #         ContextData(),
    #         ObjectType(ObjectName(oid)),
    #         lookupMib=False,
    #     )

    #     errorIndication, errorStatus, errorIndex, varBinds = await iterator

    #     if errorIndication:
    #         details = f"ERROR 'errorIndication' in pySNMP Engine: {pprint.pformat(errorStatus)} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"
    #         snmpEngine.close_dispatcher()
    #         return (True, details)

    #     elif errorStatus:
    #         details = f"ERROR 'errorStatus' in pySNMP PDU: {pprint.pformat(errorStatus)} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"
    #         snmpEngine.close_dispatcher()
    #         return (True, details)

    #     else:
    #         # store the returned data
    #         (oid, retval) = varBinds
    #         snmpEngine.close_dispatcher()
    #         return (False, retval)

    # def get(self, oid: str) -> tuple[bool, str]:
    #     """
    #     Get a single specific OID value via SNMP
    #     Returns a tuple with (error_status (bool), return_value)
    #     if error, then return_value is string with reason for error
    #     """
    #     if not self.switch:
    #         return (True, "Switch() NOT set!")
    #     if not self._auth_data:
    #         return (True, "Auth Data NOT set!")

    #     return asyncio.run(self.run_get(oid))

    async def run_set_vars(self, vars: tuple):
        """Asyncio implementation of snmp set call. See
        https://docs.lextudio.com/pysnmp/v7.1/docs/hlapi/v3arch/asyncio/manager/cmdgen/setcmd

        Args:
            self: the class instance
            vars (tuple): a tuple of snmp oid (str), and the value (snmp object type) to set.

        Returns:
            (bool): True on success, False on failure and will set self.error accordinglu
        """
        dprint("pysnmpHelper.run_set_vars() running...")

        snmpEngine = SnmpEngine()

        iterator = set_cmd(
            snmpEngine,
            self._auth_data,
            await UdpTransportTarget.create((self.switch.primary_ip4, self.switch.snmp_profile.udp_port)),
            ContextData(),
            *vars,
            lookupMib=False,
        )

        errorIndication, errorStatus, errorIndex, varBinds = await iterator

        if errorIndication:
            self.error.status = True
            self.error.description = "An SNMP error occurred!"
            self.error.details = f"ERROR 'errorIndication' pySNMP Engine: {pprint.pformat(errorStatus)} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"
            dprint("pysnmp.set_vars() SNMP engine error!")
            snmpEngine.close_dispatcher()
            return False

        elif errorStatus:
            self.error.status = True
            self.error.description = "An SNMP error occurred!"
            self.error.details = f"ERROR 'errorStatus' in pySNMP PDU: {pprint.pformat(errorStatus)} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"
            dprint("pysnmp.set_vars() SNMP PDU error!")
            snmpEngine.close_dispatcher()
            return False

        dprint("pysnmpHelper.run_set_vars() OK!")
        return True

    def set_vars(self, vars: tuple) -> bool:
        """
        Set a single OID value. Note that 'value' has to be properly typed, see
        https://docs.lextudio.com/pysnmp/v7.1/docs/hlapi/v3arch/asyncio/manager/cmdgen/setcmd

        Args:
            self: the class instance
            vars (tuple): a tuple of snmp oid (str), and the value (snmp object type) to set.

        Returns:
            (bool): True on success, False on failure and will set self.error accordinglu
        """
        dprint("pysnmpHelper.set_vars()")
        if not self._auth_data:
            self.error.status = True
            self.error.description = "Auth Data NOT set!"
            self.error.details = "SNMP authentication data NOT set in config, please update!"
            dprint("pysnmp.set_vars() no auth_data!")
            return False

        dprint("pysnmpHelper.set_vars() about to call async")
        # we now call the worker function to perform this asynchronously
        retval = asyncio.run(self.run_set_vars(vars))

        if not retval:
            dprint("pysnmpHelper().set_vars() returns False")
            return False

        # no errors
        self.error.clear()
        dprint("pysnmpHelper.set_vars() OK")
        return True

    def set(self, oid: str, value) -> bool:
        """
        Set a single OID value. Note that 'value' has to be properly typed, see
        http://snmplabs.com/pysnmp/docs/api-reference.html#pysnmp.smi.rfc1902.ObjectType
        Returns True if success.
        On failure, returns False, and self.error.X will be set
        """
        dprint("pysnmpHelper.set()")
        var = []
        var.append(ObjectType(ObjectIdentity(ObjectName(oid)), value))
        return self.set_vars(var)

    def set_multiple(self, oid_values: list) -> bool:
        """
        Set multiple OIDs in a single atomic snmp set()
        oid_tuples is a list of tuples (oid, value) containing
        the oid as a string, and a properly typed value,
        e.g. OctetString, Integer32, etc...
        Returns True if success.
        On failure, returns False, and self.error.X will be set
        """
        dprint("pysnmpHelper.set_multiple()")
        # first format in the varBinds format needed by pysnmp:
        vars = []
        for oid, value in oid_values:
            vars.append(ObjectType(ObjectIdentity(ObjectName(oid)), value))
        # now call set_vars() to do the work:
        return self.set_vars(vars)

    def _set_auth_data(self) -> bool:
        """
        Set the UsmUserData() for v3 or CommunityData() for v2 based on the device snmp_profile.
        Set the object in the self._auth_data variable.

        Returns:
            (bool): True on success, False on failure, and set the
        """
        if not self.switch:
            # we need a Switch() object!
            self.error.status = True
            self.error.description = "No device found!"
            self.error.details = "Cannot set SNMP authentication, as no device is found!"
            return False

        if self.switch.snmp_profile.version == SNMP_VERSION_2C:
            self._auth_data = CommunityData(self.switch.snmp_profile.community)
            return True

        if self.switch.snmp_profile.version == SNMP_VERSION_3:
            # NoAuthNoPriv
            if self.switch.snmp_profile.sec_level == SNMP_V3_SECURITY_NOAUTH_NOPRIV:
                self._auth_data = UsmUserData(self.switch.snmp_profile.username)
                return True

            # AuthNoPriv
            elif self.switch.snmp_profile.sec_level == SNMP_V3_SECURITY_AUTH_NOPRIV:
                if self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_MD5:
                    auth_protocol = usmHMACMD5AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA:
                    auth_protocol = usmHMACSHAAuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA224:
                    auth_protocol = usmHMAC128SHA224AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA256:
                    auth_protocol = usmHMAC192SHA256AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA384:
                    auth_protocol = usmHMAC256SHA384AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA512:
                    auth_protocol = usmHMAC384SHA512AuthProtocol

                self._auth_data = UsmUserData(
                    self.switch.snmp_profile.username,
                    self.switch.snmp_profile.passphrase,
                    authProtocol=auth_protocol,
                )
                return True

            # AuthPriv
            elif self.switch.snmp_profile.sec_level == SNMP_V3_SECURITY_AUTH_PRIV:
                # authentication protocol
                auth_protocol = usmHMACSHAAuthProtocol  # default to SHA-1
                if self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_MD5:
                    auth_protocol = usmHMACMD5AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA:
                    auth_protocol = usmHMACSHAAuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA224:
                    auth_protocol = usmHMAC128SHA224AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA256:
                    auth_protocol = usmHMAC192SHA256AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA384:
                    auth_protocol = usmHMAC256SHA384AuthProtocol
                elif self.switch.snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA512:
                    auth_protocol = usmHMAC384SHA512AuthProtocol

                # privacy protocol
                priv_protocol = usmAesCfb128Protocol  # default to AES-128
                if self.switch.snmp_profile.priv_protocol == SNMP_V3_PRIV_DES:
                    priv_protocol = usmDESPrivProtocol
                elif self.switch.snmp_profile.priv_protocol == SNMP_V3_PRIV_AES:
                    priv_protocol = usmAesCfb128Protocol
                elif self.switch.snmp_profile.priv_protocol == SNMP_V3_PRIV_AES192:
                    priv_protocol = usmAesCfb192Protocol
                elif self.switch.snmp_profile.priv_protocol == SNMP_V3_PRIV_AES256:
                    priv_protocol = usmAesCfb256Protocol
                elif self.switch.snmp_profile.priv_protocol == SNMP_V3_PRIV_AES192C:
                    priv_protocol = usmAesBlumenthalCfb192Protocol
                elif self.switch.snmp_profile.priv_protocol == SNMP_V3_PRIV_AES256C:
                    priv_protocol = usmAesBlumenthalCfb256Protocol

                self._auth_data = UsmUserData(
                    self.switch.snmp_profile.username,
                    self.switch.snmp_profile.passphrase,
                    self.switch.snmp_profile.priv_passphrase,
                    authProtocol=auth_protocol,
                    privProtocol=priv_protocol,
                )
                return True
            else:
                # unknown security level! Should not happen...
                self.error.status = True
                self.error.description = "Unknown Security Level!"
                self.error.description = f"Security Level requested: {self.switch.snmp_profile.sec_level}"
                return False

        # unknown version!
        self.error.status = True
        self.error.description = f"SNMP Version {self.switch.snmp_profile.version} not supported!"
        return False

    # def _parse_oid_with_fixup(self, oid: str, value: Any, snmp_type: str, parser):
    #     """
    #     Parse OID data from the pysnmp library. We need to map data types, as
    #     ezsnmp returns everything as a Python str() object!
    #     Function does not return anything.
    #     """
    #     dprint("\n_parse_oid_with_fixup()")
    #     dprint(f"HANDLING OID: {str(oid)}")
    #     dprint(f" value type = {str(type(value))}")
    #     dprint(f"  snmp_type = {snmp_type}")
    #     dprint(f"     length = {len(value)}")
    #     # change some types, and pass
    #     # pysnmp types:
    #     if 'DisplayString' in snmp_type:
    #         newvalue = str(value)
    #     elif 'OctetString' in snmp_type:
    #         newvalue = str(value)
    #     # ezsnmp types, already str() !
    #     # elif ('OCTETSTR' in snmp_type):
    #     #    dprint("   OCTETSTRING already as str()")
    #     #    #see https://github.com/kamakazikamikaze/easysnmp/issues/91
    #     #    newvalue = value
    #     # elif ('INTEGER' in snmp_type):
    #     #    dprint("   INTEGER to int()")
    #     #    newvalue = int(value)
    #     # elif ('GAUGE' in snmp_type):
    #     #    dprint("   GAUGE to int()")
    #     #    newvalue = int(value)
    #     # elif ('TICKS' in snmp_type):
    #     #    dprint("   TICKS to int()")
    #     #    newvalue = int(value)
    #     # elif ('OBJECTID' in snmp_type):
    #     #    dprint("   OBJECTID already as str()")
    #     #    newvalue = value
    #     else:
    #         # default is already string
    #         newvalue = value

    #     # go parse the oid data
    #     if parser:
    #         # specific data parser
    #         parser(oid, newvalue)
    #     else:
    #         # default parser
    #         self._parse_oid(oid, newvalue)


class SnmpConnector(Connector):
    """
    This class implements a "Generic SNMP" standards-based switch connection interface.
    Note: in "vendors" folder are several classes that implement vendor-specific parts of this generic class.
    """

    def __init__(self, request: HttpRequest, group: SwitchGroup, switch: Switch):
        """
        Initialize the SNMP object

        params:
            request: the HttpRequest object from Django
            group: the SwitchGroup the deviec is a member of.
            switch: the Switch() object for this device.
        """
        dprint("SnmpConnector() __init__")
        super().__init__(request=request, group=group, switch=switch)

        self.vendor_name = "Generic SNMP device"
        self.description = "Generic SNMP connector"  # what type of class is running!

        if self.__class__.__name__ == "SnmpConnector":
            self.add_warning(
                "Device is using the Generic SNMP driver! This means it is not tested, and will likely have unexpected behaviour. Please proceed with caution!"
            )

        # SNMP specific attributes:
        self.object_id = ""  # SNMP system OID value, used to find type of switch
        self.sys_uptime = 0  # sysUptime is a tick count in 1/100th of seconds per tick, since boot
        self.sys_uptime_timestamp = 0  # timestamp when sysUptime was read.
        self.qbridge_port_to_if_index: Dict[int, str] = (
            {}
        )  # this maps Q-Bridge port id as key (int) to MIB-II ifIndex (str)
        self.dot1tp_fdb_to_vlan_index: Dict[int, int] = (
            {}
        )  # forwarding database index to vlan index mapping. Note many switches do not use this...
        self.ip4_to_if_index: Dict[str, str] = (
            {}
        )  # the IPv4 addresses as keys, with stored value ifIndex (string); needed to map netmask to interface
        # self.has_connector = True   # value of IFMIB_CONNECTOR

        # VLAN related variables
        self.vlan_id_by_index: Dict[int, int] = (
            {}
        )  # list of vlan indexes and their vlan ID's. Note on many switches these two are the same!

        # SNMP context related (used in v3 only, for most devices)
        self.vlan_id_context = 0  # non-zero if the current function is running in the context of a specific vlan

        # PoE related:
        self.poe_port_entries: Dict[str, PoePort] = (
            {}
        )  # PoePort() port power entries, used to store until we can map to interface

        # Netmiko is used for SSH connections. Here are some defaults a class can set.
        # Note that for this 'generic' SNMP driver, we don't set defaults!
        # this needs to be overwritten in sub-classes that inherited from us.
        self.netmiko_device_type = ""
        # the command that should be sent to disable screen paging
        # let Netmiko decide this...
        # self.netmiko_disable_paging_command = ""

        # if no Snmp Profile, or profile is R/O, then set connector to read-only:
        if not self.switch.snmp_profile or self.switch.snmp_profile.read_only:
            self.read_only = True

        # capabilities of the snmp drivers:
        self.can_change_admin_status = True
        self.can_change_vlan = True
        self.can_edit_vlans = True
        self.can_change_poe_status = True
        self.can_change_description = True
        self.can_save_config = False  # do we have the ability (or need) to execute a 'save config' or 'write memory' ?
        self.can_reload_all = True  # if true, we can reload all our data (and show a button on screen for this)

        """
        attributes to track ezsnmp library
        """
        self._snmp_session = False  # ezsnmp session object
        # initialize the snmp "connection/session"
        if not self._set_snmp_session():
            dprint("   ERROR: cannot get SNMP session!")
            self.log_error()
            raise Exception("Cannot get SNMP session, did you configure a profile?")

        # caching related. Add attributes that do not get cached:
        self.set_do_not_cache_attribute("_snmp_session")
        self.set_do_not_cache_attribute("poe_port_entries")

    def _set_snmp_session(self, com_or_ctx: str = '') -> bool:
        """
        Get a ezsnmp Session() object for this snmp connection.

        params:
            com_or_ctx - the community to override the snmp profile settings if v2,
                         or the snmp v3 context to use.

        Return:
            (bool) - True if succesful, False if not!

        """
        dprint("_set_snmp_session()")
        if not self.switch.snmp_profile:
            # should never happen!
            dprint("  ERROR: switch.snmp_profile NOT set!")
            return False

        snmp_profile = self.switch.snmp_profile
        if snmp_profile.version == SNMP_VERSION_2C:
            dprint("version 2c")
            # use specific given community, if set:
            if com_or_ctx:
                community = com_or_ctx
            else:
                # use profile setting
                community = snmp_profile.community
            try:
                self._snmp_session = ezsnmp.Session(
                    hostname=self.switch.primary_ip4,
                    version=snmp_profile.version,
                    community=community,
                    remote_port=snmp_profile.udp_port,
                    use_numeric=True,
                    use_sprint_value=False,
                    timeout=settings.SNMP_TIMEOUT,
                    retries=settings.SNMP_RETRIES,
                )
            except Exception as err:
                dprint(f"ERROR with snmp v2 session: {repr(err)}")
                self.add_log(
                    description=f"ERROR with snmp v2 session: {err}", type=LOG_TYPE_ERROR, action=LOG_SNMP_ERROR
                )
                return False

            return True

        # everything else is version 3
        if snmp_profile.version == SNMP_VERSION_3:
            # EzSNMPO does not like empty auth and priv, so set low defaults.
            auth_protocol = "MD5"
            privacy_protocol = "DES"
            security_level = ""
            # NoAuthNoPriv
            if snmp_profile.sec_level == SNMP_V3_SECURITY_NOAUTH_NOPRIV:
                dprint("version 3 NoAuth-NoPriv")
                security_level = u"no_auth_or_privacy"

            # AuthNoPriv
            elif snmp_profile.sec_level == SNMP_V3_SECURITY_AUTH_NOPRIV:
                dprint("version 3 Auth-NoPriv")
                security_level = u"auth_without_privacy"
                if snmp_profile.auth_protocol == SNMP_V3_AUTH_MD5:
                    auth_protocol = u"MD5"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA:
                    auth_protocol = u"SHA"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA224:
                    auth_protocol = u"SHA-224"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA256:
                    auth_protocol = u"SHA-256"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA384:
                    auth_protocol = u"SHA-384"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA512:
                    auth_protocol = u"SHA-512"
                else:
                    return False

            # AuthPriv
            elif snmp_profile.sec_level == SNMP_V3_SECURITY_AUTH_PRIV:
                dprint("version 3 Auth-Priv")
                security_level = "auth_with_privacy"
                # auth protocols first
                if snmp_profile.auth_protocol == SNMP_V3_AUTH_MD5:
                    auth_protocol = u"MD5"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA:
                    auth_protocol = u"SHA"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA224:
                    auth_protocol = u"SHA-224"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA256:
                    auth_protocol = u"SHA-256"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA384:
                    auth_protocol = u"SHA-384"
                elif snmp_profile.auth_protocol == SNMP_V3_AUTH_SHA512:
                    auth_protocol = u"SHA-512"
                else:
                    dprint(f"Invalid AUTH protocol: {snmp_profile.auth_protocol}")
                    return False

                # priv protocols next:
                if snmp_profile.priv_protocol == SNMP_V3_PRIV_DES:
                    privacy_protocol = u"DES"
                elif snmp_profile.priv_protocol == SNMP_V3_PRIV_AES:
                    privacy_protocol = u"AES"
                elif snmp_profile.priv_protocol == SNMP_V3_PRIV_AES192:
                    privacy_protocol = u"AES-192"
                elif snmp_profile.priv_protocol == SNMP_V3_PRIV_AES256:
                    privacy_protocol = u"AES-256"
                elif snmp_profile.priv_protocol == SNMP_V3_PRIV_AES192C:
                    privacy_protocol = u"AES-192C"
                elif snmp_profile.priv_protocol == SNMP_V3_PRIV_AES256C:
                    privacy_protocol = u"AES-256C"
                else:
                    dprint(f"Invalid PRIV protocol: {snmp_profile.priv_protocol}")
                    return False

            else:
                # should never happen:
                dprint(f"  Unknown auth-priv security level: {snmp_profile.sec_level}")
                return False

            # now try to connect with SNMP v3:
            dprint(f"  Trying v3 with: sec_level={security_level}, auth={auth_protocol}, priv={privacy_protocol}")
            if not snmp_profile.passphrase:
                passphrase = ""
            else:
                passphrase = snmp_profile.passphrase
            if not snmp_profile.priv_passphrase:
                priv_passphrase = ""
            else:
                priv_passphrase = snmp_profile.priv_passphrase
            try:
                self._snmp_session = ezsnmp.Session(
                    hostname=self.switch.primary_ip4,
                    version=snmp_profile.version,
                    remote_port=snmp_profile.udp_port,
                    use_numeric=True,
                    use_sprint_value=False,
                    timeout=settings.SNMP_TIMEOUT,
                    retries=settings.SNMP_RETRIES,
                    # here are the v3 specific entries:
                    security_level=security_level,
                    security_username=snmp_profile.username,
                    auth_protocol=auth_protocol,
                    auth_password=passphrase,
                    privacy_protocol=privacy_protocol,
                    privacy_password=priv_passphrase,
                    context=str(com_or_ctx),
                )
                return True

            except Exception as err:
                dprint(f"ERROR with snmp v3 session: {repr(err)}")
                self.add_log(
                    description=f"ERROR with snmp v3 session: {err}", type=LOG_TYPE_ERROR, action=LOG_SNMP_ERROR
                )
                return False

        # unknown SNMP version - this *should* never happen:
        self._snmp_session = False
        self.add_log(
            description=f"ERROR: UNKNOWN snmp version '{snmp_profile.version}'",
            type=LOG_TYPE_ERROR,
            action=LOG_SNMP_ERROR,
        )
        dprint("UNKNOWN snmp version!")
        return False

    """
    The following methods implement basic snmp functionality based on the ezsnmp library (for speed reasons).
    If you want to use some other snmp library, inherit from SnmpConnector()
    and override the basic snmp interfaces get(), get_snmp_branch() set(), set_multiple() and _set_snmp_session()
    This would allow you to implement using pysnmp, netsnmp-python, etc.
    """

    def get(self, oid: str, parser) -> tuple:
        """
        Get a single specific OID value via SNMP
        Returns a tuple with (error_status, return_value)
        if error, then return_value is not defined

        Params:
            oid (str): string name of SNMP OID (e.g. "ifIndex")
            parser (function): pointer name of the function used to parse the result of this MIB walk.

        Returns:
            (error, ret_val): tuple where error is True on error, and self.error() is set.
                            ret_val is the return value from ezsnmp.get() call.
        """
        dprint(f"SnmpConnector.get(oid={oid})")
        self.error.clear()

        # Set a variable using an SNMP SET
        try:
            retval = self._snmp_session.get(oids=oid)
        except Exception as e:
            self.error.status = True
            self.error.description = "Timeout or Access denied"
            self.error.details = f"SNMP Get Error in {e.__class__.__name__}: oid '{oid}': {repr(e)} ({str(type(e))})\n{traceback.format_exc()}"
            dprint(f"   ERROR in get() - Details:\n{self.error.details}\n")
            return (True, None)

        # parse the data, just like returns from get_branch()
        if parser:
            parser(f"{retval.oid}.{retval.oid_index}", str(retval.value))
        else:
            dprint("SnmpConnector.get(): Warning - Return NOT parsed!")

        return (False, retval)

    def get_snmp_branch(self, branch_name: str, parser, max_repetitions: int = settings.SNMP_MAX_REPETITIONS) -> int:
        """
        Bulk-walk a branch of the snmp mib, fill the data in the oid store.
        This finishes when we leave this branch.

        Args:
            branch_name(str):   SNMP OID name, e.g. "system".
            parser(*function):  function to call to parse the MIB data.

        Returns:
            (int): the count of objects returned from the snmp walk, or -1 if error.
            On error, self.error() is set appropriately.
        """
        dprint(f"\n\n### get_snmp_branch({branch_name}) ###\n")
        if branch_name not in snmp_mib_variables.keys():
            self.error.status = True
            self.error.description = f"ERROR: invalid branch name '{branch_name}'"
            dprint(f"+++> INVALID BRANCH NAME: {branch_name}")
            self.add_warning(f"Invalid snmp branch '{branch_name}'")
            # log this as well
            self.add_log(
                type=LOG_TYPE_ERROR,
                action=LOG_SNMP_ERROR,
                description=f"ERROR getting '{branch_name}': invalid branch name",
            )
            return -1

        start_oid = snmp_mib_variables[branch_name]
        # Perform an SNMP walk
        self.error.clear()
        count = 0
        try:
            dprint(f"   Calling BulkWalk {start_oid}")
            start_time = time.time()
            items = self._snmp_session.bulkwalk(oids=start_oid, non_repeaters=0, max_repetitions=max_repetitions)
            stop_time = time.time()
            # Each returned item can be used normally as its related type (str or int)
            # but also has several extended attributes with SNMP-specific information
            for item in items:
                count = count + 1
                oid_found = f"{item.oid}.{item.oid_index}"
                # Note: with ezsnmp, the returned "item.value" is ALWAYS of type str!
                # the real SNMP type is indicated in item.snmp_type !!!
                if item.snmp_type == 'OCTETSTR':
                    if item.value.isprintable():
                        value = item.value
                    else:
                        # for non-printable octetstring, you can use this:
                        # https://github.com/kamakazikamikaze/easysnmp/issues/91
                        value = "CAN NOT PRINT!"
                else:
                    value = item.value
                dprint(f"\n\n====> SNMP READ: {oid_found} {item.snmp_type} = {value}")

                # call the mib parser
                parser(oid_found, item.value)

            # add to timing data, for admin use!
            self.add_timing(branch_name, count, stop_time - start_time)

        except Exception as e:
            self.error.status = True
            self.error.description = "A timeout or network error occured!"
            self.error.details = (
                f"SNMP Error: get_snmp_branch {branch_name}, {repr(e)} ({str(type(e))})\n{traceback.format_exc()}"
            )
            dprint(f"   get_snmp_branch({branch_name}): Exception: {e.__class__.__name__}\n{self.error.details}\n")
            # log this as well
            self.add_log(
                type=LOG_TYPE_ERROR,
                action=LOG_SNMP_ERROR,
                description=f"ERROR getting '{branch_name}': {self.error.details}",
            )
            return -1

        dprint(f"get_snmp_branch() returns {count}")
        return count

    def set(self, oid: str, value, snmp_type, parser) -> bool:
        """
        Set a single OID value. Note that 'value' has to be properly typed!
        Returns True if success.
        On failure, returns False, and self.error.X will be set
        """
        dprint(f"SnmpConnector.set(oid={oid}, value={value}, snmp_type={snmp_type})")
        # Set a variable using an SNMP SET
        self.error.clear()
        try:
            self._snmp_session.set(oid=oid, value=value, snmp_type=snmp_type)

        except Exception as e:
            self.error.status = True
            self.error.description = "Access denied"
            self.error.details = f"SNMP Set Error in {e.__class__.__name__}: oid '{oid}', value '{value}', value type '{type(value)}' snmp_type '{snmp_type}', Details: {repr(e)} ({str(type(e))})\n{traceback.format_exc()}"
            dprint(f"   ERROR in set() - Details:\n{self.error.details}\n")
            return False
        dprint("SnmpConnector.set() OK!")

        # parse the data, just like returns from get_branch()
        if parser:
            dprint("SnmpConnector.set() parsing return:")
            parser(str(oid), str(value))
        else:
            dprint("SnmpConnector.set() OK, BUT Return NOT parsed!")

        return True

    def set_multiple(self, oid_values: list) -> bool:
        """
        Set multiple OIDs at the same time, in a single snmp request
        oid_values is a list of tuples (oid, value, type)
        Returns True if success, and if requested, then we also update the
        local oid cache to track the change.
        On failure, returns False, and self.error.X will be set
        """
        dprint(f"SnmpConnector.set_multiple(oid_values={oid_values})")
        # here we go:
        self.error.clear()
        try:
            self._snmp_session.set_multiple(oid_values=oid_values)

        except Exception as e:
            self.error.status = True
            self.error.description = "Access denied"
            self.error.details = f"SNMP Set-Multiple Error in {e.__class__.__name__}: oid values '{oid_values}', error {repr(e)} ({str(type(e))})\n{traceback.format_exc()}"
            dprint(f"   ERROR in set_multiple() - Details:\n{self.error.details}\n")
            return False

        return True

    """
    end of the ezsnmp interfaces
    """

    """
    various methods from the base Connector() class implemented here.
    """

    def get_my_basic_info(self) -> bool:
        """
        Get the basic info for this class of devices (ie snmp devices)
        Bulk-walk the needed MIBs to get the basics of this device:
        System, Interfaces, Aliases, Qbridge and PoE MIBs
        """
        dprint("get_my_basic_info()")
        self.error.clear()
        retval = self._get_system_data()
        if retval != -1:
            retval = self._get_interface_data()
            if retval != -1:
                retval = self._get_vlan_data()
                if retval != -1:
                    retval = self._get_my_ip4_addresses()
                    if retval != -1:
                        retval = self._get_lacp_data()
                        if retval != -1:
                            retval = self._get_poe_data()
                            if retval != -1:
                                # try to map poe port info to actual interfaces
                                self._map_poe_port_entries_to_interface()
                                return True
        return False

    def get_my_client_data(self) -> bool:
        """
        Get additional information about switch ports, eg. ethernet address, counters...
        Note this is never cached, so anytime we get fresh, "live" data!
        """
        # now load the ethernet tables every time, without caching
        if self._get_known_ethernet_addresses():  # no error
            # read LLDP as well
            self._get_lldp_data()
            # and the arp tables (after we found ethernet address, so we can update with IP)
            self._get_arp_data()
            self.switch.save()  # update counters
            return True
        return False

    def get_my_hardware_details(self) -> bool:
        """
        Get all (possible) hardware info, stacking details, etc.
        return True if success, and False if not
        """
        # call the vendor-specific data first, if implemented
        self._get_hardware_data()
        # read Syslog data, if any
        self._get_syslog_msgs()
        return True

    """
    internal class-specific functions
    """

    def _get_ports_from_vlan_bitmap(self, vlan_id: int, byte_string: bytes):
        """Parse the list of all egress ports of a VLAN (tagged + untagged) as a hex byte string
        now look at all the bits in this multi-byte value to find ports on this vlan:

        Args:
            vlan_id (int): the vlan id that this byte string applies to
            byte_string (bytes)): the bitmap showing which ports are a member of this vlan

        Returns:
            n/a
        """
        offset = 0
        for byte in byte_string:
            byte = ord(byte)
            # which bits are set? A hack but it works!
            # note that the bits are actually in system order,
            # ie. bit 1 is first bit in stream, i.e. HIGH order bit!
            if byte & 128:
                port_id = (offset * 8) + 1
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 64:
                port_id = (offset * 8) + 2
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 32:
                port_id = (offset * 8) + 3
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 16:
                port_id = (offset * 8) + 4
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 8:
                port_id = (offset * 8) + 5
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 4:
                port_id = (offset * 8) + 6
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 2:
                port_id = (offset * 8) + 7
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 1:
                port_id = (offset * 8) + 8
                self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
            offset += 1

    def _get_untagged_ports_from_vlan_bitmap(self, vlan_id: int, byte_string: bytes):
        """Parse the list of current untagged ports of a VLAN as a hex byte string
        Look at all the bits in this multi-byte value to find ports on this vlan:

        Args:
            vlan_id (int): the vlan id that this byte string applies to
            byte_string (bytes)): the bitmap showing which ports are a member of this vlan

        Returns:
            none
        """
        dprint(f"_get_untagged_ports_from_vlan_bitmap() for vlan {vlan_id}")
        offset = 0
        for byte in byte_string:
            byte = ord(byte)
            # which bits are set? A hack but it works!
            # note that the bits are actually in system order,
            # ie. bit 1 is first bit in stream, i.e. HIGH order bit!
            if byte & 128:
                port_id = (offset * 8) + 1
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 64:
                port_id = (offset * 8) + 2
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 32:
                port_id = (offset * 8) + 3
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 16:
                port_id = (offset * 8) + 4
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 8:
                port_id = (offset * 8) + 5
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 4:
                port_id = (offset * 8) + 6
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 2:
                port_id = (offset * 8) + 7
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            if byte & 1:
                port_id = (offset * 8) + 8
                self._add_untagged_vlan_to_interface_by_port_id(port_id, vlan_id)
            offset += 1

        #
        # 802.1Q / VLAN related MIB parsers
        #

    def _parse_mib_dot1q_base(self, oid: str, val: str) -> bool:
        """Parse entries in the 'dot1qBase' part of the Q-Bridge mib.
        This contains various 'counters' about numbers of vlans, etc.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"Base _parse_mib_dot1q_base() {str(oid)}")

        # these are part of "dot1qBase":
        sub_oid = oid_in_branch(dot1qNumVlans, oid)
        if sub_oid:
            self.vlan_count = int(val)
            return True

        sub_oid = oid_in_branch(dot1qGvrpStatus, oid)
        if sub_oid:
            if int(val) == GVRP_ENABLED:
                self.gvrp_enabled = True
            return True
        # we did not parse the OID.
        return False

    def _parse_mibs_if_table(self, oid: str, val: str) -> bool:
        """Function to parse the original(old) MIB-II ifTable entries
        This contains the interface index, and a number of other attributes
        The newer IF-MIB (see below) also contains interface attributes.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"Base _parse_mibs_if_table() {str(oid)}")

        oid_end = oid_in_branch(ifIndex, oid)
        if oid_end:
            # ifIndex branch is special, the snmp return "val" is the index, not the oid ending!
            # create new interface object and store, with index as string key!
            return self.add_interface(Interface(val))

        # this is the old ifDescr, superceded by the IF-MIB name
        if_index = oid_in_branch(ifDescr, oid)
        if if_index:
            # set new 'name'. Latter will later be overwritten with ifName bulkwalk
            return self.set_interface_attribute_by_key(if_index, "name", str(val))

        if_index = oid_in_branch(ifType, oid)
        if if_index:
            if_type = int(val)
            if self.set_interface_attribute_by_key(if_index, "type", if_type):
                if if_type != IF_TYPE_ETHERNET:
                    # non-Ethernet interfaces are NOT manageable, no matter who
                    self.set_interface_attribute_by_key(if_index, "manageable", False)
                    self.set_interface_attribute_by_key(
                        if_index, "unmanage_reason", "Access denied: not an Ethernet interface!"
                    )
            return True

        if_index = oid_in_branch(ifMtu, oid)
        if if_index:
            return self.set_interface_attribute_by_key(if_index, "mtu", int(val))

        # the old speed, but really we want HCSpeed from IF-MIB, see below
        if_index = oid_in_branch(ifSpeed, oid)
        if if_index:
            # save this in 1Mbps, as per IF-MIB hcspeed
            return self.set_interface_attribute_by_key(if_index, "speed", int(val) / 1000000)

        # do we care about this one?
        if_index = oid_in_branch(ifPhysAddress, oid)
        if if_index:
            return self.set_interface_attribute_by_key(if_index, "phys_addr", val)

        if_index = oid_in_branch(ifAdminStatus, oid)
        if if_index:
            status = True if int(val) == IF_ADMIN_STATUS_UP else False
            return self.set_interface_attribute_by_key(if_index, "admin_status", status)

        if_index = oid_in_branch(ifOperStatus, oid)
        if if_index:
            status = True if int(val) == IF_OPER_STATUS_UP else False
            return self.set_interface_attribute_by_key(if_index, "oper_status", status)

        """
        if_index = int(oid_in_branch(ifLastChange, oid))
        if if_index:
            return self.set_interface_attribute_by_key(if_index, "last_change", int(val))
        """

        # we did not parse the OID.
        return False

    def _parse_mibs_if_x_table(self, oid: str, val: str) -> bool:
        """Function to parse the more modern IF-MIB "ifXTable" entries
        that contains additional interface information.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"Base _parse_mibs_if_x_table() {str(oid)}")

        if_index = oid_in_branch(ifName, oid)
        if if_index:
            return self.set_interface_attribute_by_key(if_index, "name", str(val))

        if_index = oid_in_branch(ifAlias, oid)
        if if_index:
            return self.set_interface_attribute_by_key(if_index, "description", str(val))

        # ifMIB high speed counter:
        if_index = oid_in_branch(ifHighSpeed, oid)
        if if_index:
            return self.set_interface_attribute_by_key(if_index, "speed", int(val))

        """
        if_index = int(oid_in_branch(ifConnectorPresent, oid))
        if if_index:
            val = int(val)
            if if_index in self.interfaces.keys():
                if val == SNMP_TRUE:
                    self.set_interface_attribute_by_key(if_index, "has_connector", True)
                else:
                    self.set_interface_attribute_by_key(if_index, "has_connector", False)
                    self.set_interface_attribute_by_key(if_index, "manageable", False)
            return True
        """

        # we did not parse the OID.
        return False

    def _parse_mibs_vlan_related(self, oid: str, val: str) -> bool:
        """Function to parse various VLAN related MIB entries
        that contains vlans and vlan-membership information.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"SnmpConnector()._parse_mibs_vlan_related(oid={str(oid)}, val={val}")

        # Map the Q-BRIDGE port id to the MIB-II if_indexes.
        # PortID=0 indicates known ethernet, but unknown port, i.e. ignore
        port_id = int(oid_in_branch(dot1dBasePortIfIndex, oid))
        if port_id:
            dprint(f"  Found dot1dBasePortIfIndex = {port_id}")
            # map port ID (as str) to interface ID (as str)
            if_index = str(val)
            if if_index in self.interfaces.keys():
                dprint(f"  Mapping to if_index = {if_index}")
                self.qbridge_port_to_if_index[port_id] = if_index
                # and map Interface() object back to port ID as well:
                self.set_interface_attribute_by_key(if_index, "port_id", port_id)
            # we parsed it, return true:
            return True

        # List of all available vlans on this switch as by the command "show vlans"
        vlan_id = int(oid_in_branch(dot1qVlanStaticRowStatus, oid))
        if vlan_id:
            dprint(f"  Found dot1qVlanStaticRowStatus for vlan {vlan_id}")
            # for now, just add to the dictionary,
            # we will fill in the initial name below at "VLAN_NAME"
            if vlan_id in self.vlans.keys():
                # currently we don't parse the status, so nothing to do here
                return True
            # else add entry, should never happen!
            self.add_vlan_by_id(vlan_id=vlan_id)
            # assume vlan_id = vlan_index = fdb_index, unless we learn otherwize
            self.vlan_id_by_index[vlan_id] = vlan_id
            self.dot1tp_fdb_to_vlan_index[vlan_id] = vlan_id
            return True

        # The VLAN name
        vlan_id = int(oid_in_branch(dot1qVlanStaticName, oid))
        if vlan_id:
            dprint(f"  Found dot1qVlanStaticName for vlan {vlan_id}")
            # not yet sure how to handle this
            if vlan_id in self.vlans.keys():
                self.vlans[vlan_id].name = val
            else:
                # vlan not found yet, create it
                self.add_vlan_by_id(vlan_id=vlan_id)
                self.vlans[vlan_id].name = val
            return True

        # see if this is static or dynamic vlan
        sub_oid = oid_in_branch(dot1qVlanStatus, oid)
        if sub_oid:
            dprint(f"  Found dot1qVlanStatus for sub_oid {sub_oid}")
            (dummy, v) = sub_oid.split('.')
            vlan_id = int(v)
            status = int(val)
            if vlan_id in self.vlans.keys():
                self.vlans[vlan_id].status = status
            else:
                # only should happen for non-permanent vlans, we should know static vlans by now!
                self.add_vlan_by_id(vlan_id=vlan_id)
                self.vlans[vlan_id].status = status
            return True

        # The VLAN ID assigned to ***untagged*** frames - dot1qPvid, indexed by dot1dBasePort
        # ie. lookup ifIndex with _get_if_index_from_port_id(port_id)
        # IMPORTANT: IF THE INTERFACE IS TAGGED, this value is 1, and typically incorrect!!!
        port_id = int(oid_in_branch(dot1qPvid, oid))
        if port_id:
            dprint(f"  Found dot1qPvid for port_id {port_id}")
            if_index = self._get_if_index_from_port_id(port_id)
            # not yet sure how to handle this. val is 'untagged vlan'
            untagged_vlan = int(val)
            self.set_interface_attribute_by_key(if_index, "untagged_vlan", untagged_vlan)
            if untagged_vlan not in self.vlans.keys():
                # vlan not defined on switch!
                self.set_interface_attribute_by_key(if_index, "disabled", True)
                self.set_interface_attribute_by_key(
                    if_index, "unmanage_reason", f"Untagged vlan {untagged_vlan} is NOT defined on switch"
                )
                warning = f"Undefined vlan {untagged_vlan} on {self.interfaces[if_index].name}"
                self.add_warning(warning)
                # log this as well
                log = Log(
                    user=self.request.user,
                    group=self.group,
                    switch=self.switch,
                    ip_address=get_remote_ip(self.request),
                    if_index=if_index,
                    type=LOG_TYPE_ERROR,
                    action=LOG_UNDEFINED_VLAN,
                    description=f"ERROR: {warning}",
                )
                if self.request:
                    log.user = self.request.user
                log.save()
                # not sure what to do here
            return True

        # The .0 is the timefilter that we set to 0 to (hopefully) deactivate the filter
        # The set of ports that are transmitting traffic for this VLAN as either tagged or untagged frames.
        # CURRENT_VLAN_EGRESS_PORTS = QBRIDGENODES['dot1qVlanCurrentEgressPorts']['oid'] + '.0'
        # NOTE: this is a READ-ONLY variable!

        """
        # this is the bitmap of current untagged ports in vlans (see also above dot1qVlanStaticEgressPorts)
        sub_oid = oid_in_branch(dot1qVlanCurrentUntaggedPorts, oid)
        if sub_oid:
            dprint(f"  Found dot1qVlanCurrentUntaggedPorts for sub_oid {sub_oid}")
            (dummy, v) = sub_oid.split('.')
            vlan_id = int(v)
            if vlan_id not in self.vlans.keys():
                # not likely, but just in case:
                self.add_vlan_by_id(vlan_id=vlan_id)
            # store bitmap for later use
            self.vlans[vlan_id].untagged_ports_bitmap = val
            return True
        """

        """
        # List of all static egress ports of a VLAN (tagged + untagged) as a hexstring
        # dot1qVlanStaticEgressPorts - READ-WRITE variable
        # we read and store this so we have it ready to WRITE by setting a bit value, when we update the vlan on a port!
        vlan_id = int(oid_in_branch(dot1qVlanStaticEgressPorts, oid))
        if vlan_id:
            dprint(f"  Found dot1qVlanStaticEgressPorts for vlan {vlan_id}")
            if vlan_id not in self.vlans.keys():
                # not likely, we should know by now, but just in case.
                self.add_vlan_by_id(vlan_id=vlan_id)
            # store it!
            self.vlans[vlan_id].static_egress_portlist.from_unicode(val)
            return True
        """

        # this is the bitmap of static untagged ports in vlans (see also above dot1qVlanCurrentEgressPorts)
        vlan_id = int(oid_in_branch(dot1qVlanStaticUntaggedPorts, oid))
        if vlan_id:
            dprint(f"  Found dot1qVlanStaticUntaggedPorts for vlan {vlan_id}")
            if vlan_id not in self.vlans.keys():
                # unlikely, we should know by now, but just in case
                self.add_vlan_by_id(vlan_id=vlan_id)
            # store for later use:
            # self.vlans[vlan_id].untagged_ports_bitmap.from_unicode(val)
            # now look at all the bits in this multi-byte value to find ports on this vlan:
            self._get_untagged_ports_from_vlan_bitmap(vlan_id=int(vlan_id), byte_string=val)
            return True

        # List of all egress ports of a VLAN (tagged + untagged) as a hexstring
        # dot1qVlanCurrentEgressPorts
        sub_oid = oid_in_branch(dot1qVlanCurrentEgressPorts, oid)
        if sub_oid:
            dprint(f"  Found dot1qVlanCurrentEgressPorts for sub_oid {sub_oid}")
            # sub oid part is dot1qVlanCurrentEgressPorts.timestamp.vlan_id = bitmap
            (time_val, v) = sub_oid.split('.')
            vlan_id = int(v)
            # check if vlan is globally defined on switch:
            if vlan_id not in self.vlans.keys():
                # not likely, we should know vlan by now, but just in case!
                self.add_vlan_by_id(vlan_id=vlan_id)
            # store the egress port list, as some switches need this when setting untagged vlans
            self.vlans[vlan_id].current_egress_portlist.from_unicode(val)
            # now look at all the bits in this multi-byte value to find ports on this vlan:
            offset = 0
            for byte in val:
                byte = ord(byte)
                # which bits are set? A hack but it works!
                # note that the bits are actually in system order,
                # ie. bit 1 is first bit in stream, i.e. HIGH order bit!
                if byte & 128:
                    port_id = (offset * 8) + 1
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                if byte & 64:
                    port_id = (offset * 8) + 2
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                if byte & 32:
                    port_id = (offset * 8) + 3
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                if byte & 16:
                    port_id = (offset * 8) + 4
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                if byte & 8:
                    port_id = (offset * 8) + 5
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                if byte & 4:
                    port_id = (offset * 8) + 6
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                if byte & 2:
                    port_id = (offset * 8) + 7
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                if byte & 1:
                    port_id = (offset * 8) + 8
                    self._add_vlan_to_interface_by_port_id(port_id, vlan_id)
                offset += 1
            return True

        # we did not parse the OID.
        return False

    def _parse_mibs_mvrp(self, oid: str, val: str) -> bool:
        """Parse all the GRVP / MVRP related mib entries

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"Base _parse_mibs_mvrp() {str(oid)}")

        # the per-switchport GVRP setting:
        port_id = int(oid_in_branch(dot1qPortGvrpStatus, oid))
        if port_id:
            if_index = self._get_if_index_from_port_id(port_id)
            if int(val) == GVRP_ENABLED:
                self.set_interface_attribute_by_key(if_index, "gvrp_enabled", True)
            return True

        # is MVRP globally enabled on device ?
        sub_oid = oid_in_branch(ieee8021QBridgeMvrpEnabledStatus, oid)
        if sub_oid:
            if int(val) == GVRP_ENABLED:
                self.gvrp_enabled = True
            return True

        # we did not parse the OID.
        return False

    def _parse_mibs_ether_like(self, oid: str, val: str) -> bool:
        """Parse a few entries in the ETHER-LIKE MIB.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"Base _parse_mibs_ether_like() {str(oid)} = {val}")

        # dot3 interface duplex status information:
        if_index = oid_in_branch(dot3StatsDuplexStatus, oid)
        if if_index:
            return self.set_interface_attribute_by_key(if_index, "duplex", int(val))

        # we did not parse the OID.
        return False

    # def _parse_mibs_if_stack(self, oid: str, val: str) -> bool:
    #     """Parse a few entries in the IF-MIB ifStack entries."""
    #     # TO ADD:
    #     # ifStackHigherLayer = '.1.3.6.1.2.1.31.1.2.1.1'
    #     # ifStackLowerLayer =  '.1.3.6.1.2.1.31.1.2.1.2'
    #     # ifStackStatus =      '.1.3.6.1.2.1.31.1.2.1.3'

    #     # we did not parse the OID.
    #     return False

    def _parse_mibs_ieee_qbridge(self, oid: str, val: str) -> bool:
        """
        Parse ieee 802.1q bridge Mibs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_ieee_qbridge() {oid} = {val}")

        retval = oid_in_branch(ieee8021QBridgeVlanStaticName, oid)
        if retval:
            vlan_id = int(retval)
            # dprint(f"Aruba VLAN {vlan_id} name '{val}'")
            v = Vlan(id=vlan_id, name=val)
            self.add_vlan(v)
            return True

        retval = oid_in_branch(ieee8021QBridgePortVlanEntry, oid)
        if retval:
            # retval is in format 1.1.1, for name 1/1/1
            name = retval.replace('.', '/')
            # dprint(f"Aruba Port {name} untagged vlan {val}")
            # however, the key to the interface is the ifIndex, not name!
            iface = self.get_interface_by_name(name)
            if iface:
                # dprint("   Port found !")
                untagged_vlan = int(val)
                if not iface.is_tagged and untagged_vlan in self.vlans.keys():
                    iface.untagged_vlan = untagged_vlan
                    iface.untagged_vlan_name = self.vlans[untagged_vlan].name
            else:
                # AOS-CX appears to report all interfaces for all possible stack members.
                # even when less then max-stack-members are actualy present!
                # so we are ignoring this warning for now...
                # self.add_warning(f"IEEE802.1QBridgePortVlanEntry found, but interface {name} NOT found!")
                dprint(f"IEEE802.1QBridgePortVlanEntry found, but interface {name} does not exist!")
            return True

        sub_oid = oid_in_branch(ieee8021QBridgeVlanCurrentEgressPorts, oid)
        if sub_oid:
            # vlans with port members
            dprint(f"Found ieee8021QBridgeVlanCurrentEgressPorts, sub_oid = '{sub_oid}'")
            # sub oid part is ieee8021QBridgeVlanCurrentEgressPorts.instance.timestamp.vlan_id = bitmap
            (ignore, time_val, v) = sub_oid.split('.')
            vlan_id = int(v)
            # check if vlan is globally defined on switch:
            if vlan_id not in self.vlans.keys():
                # not likely, we should know vlan by now, but just in case!
                self.add_vlan_by_id(vlan_id=vlan_id)
            # store the egress port list, as some switches need this when setting untagged vlans
            self.vlans[vlan_id].current_egress_portlist.from_unicode(val)
            # and go figure out what ports are part of this vlan:
            self._get_ports_from_vlan_bitmap(vlan_id=vlan_id, byte_string=val)
            return True

        sub_oid = oid_in_branch(ieee8021QBridgeVlanCurrentUntaggedPorts, oid)
        if sub_oid:
            dprint("Found ieee8021QBridgeVlanCurrentUntaggedPorts ")
            dprint("parsing ignored for now (not functional!)")
            # # sub oid part is ieee8021QBridgeVlanCurrentUntaggedPorts.somthing.instance.vlan_id = bitmap
            # (ignore, ignore2, v) = sub_oid.split('.')
            # vlan_id = int(v)
            # # check if vlan is globally defined on switch:
            # if vlan_id not in self.vlans.keys():
            #     # not likely, we should know vlan by now, but just in case!
            #     self.add_vlan_by_id(vlan_id=vlan_id)
            # # figure out untagged ports based on the bitmap
            # self._get_untagged_ports_from_vlan_bitmap(vlan_id=vlan_id, byte_string=val)
            return True

        return False

    #
    # Original "dot1d Bridge MIB" Known Ethernet MIB parsing
    #
    def _parse_mibs_dot1d_bridge_eth(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the Q-Bridge Ethernet MIBs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint("_parse_mibs_dot1d_bridge_eth()")

        # Q-Bridge Ethernet addresses known
        eth_decimals = oid_in_branch(dot1dTpFdbPort, oid)
        if eth_decimals:
            # the 6 decimals returned past OID are 6 numbers representing the MAC address!
            # they need to be converted to hex values with hyphens aa-bb-cc-11-22-33
            eth_string = decimal_to_hex_string_ethernet(eth_decimals)
            port_id = val
            # PortID=0 indicates known ethernet, but unknown port, i.e. ignore
            if int(port_id) > 0:
                # now port_id should map to the interface_id!
                if_index = self._get_if_index_from_port_id(port_id)
                if if_index in self.interfaces.keys():
                    e = EthernetAddress(eth_string)
                    # make sure we use consistent string representation of this ethernet address:
                    e.dialect = settings.MAC_DIALECT
                    if self.vlan_id_context > 0:
                        e.vlan_id = self.vlan_id_context
                        # we use string representation of the EthernetAddress() object
                        # to make sure we use a consistent key.
                        # See below were we find this entry in _parse_mibs_net_to_media()
                        # and _parse_mibs_q_bridge_eth()
                    if str(e) not in self.interfaces[if_index].eth:
                        self.interfaces[if_index].eth[str(e)] = e
                        self.eth_addr_count += 1
                        dprint(f"  Added MAC address: {e}")
                    else:
                        dprint(f"  Duplicate MAC: {e}")
                else:
                    dprint(f"  if_index = {if_index}: NOT FOUND!")
            return True
        return False

    #
    # Newer Q-Bridge Known Ethernet MIB parsing
    #
    def _parse_mibs_q_bridge_eth(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the Q-Bridge Ethernet MIBs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint("_parse_mibs_q_bridge_eth()")

        # Q-Bridge Ethernet addresses known
        fdb_eth_decimals = oid_in_branch(dot1qTpFdbPort, oid)
        if fdb_eth_decimals:
            # decimals returned are fdb index and then 6 numbers representing the MAC address!
            # e.g.    458752.120.72.89.101.150.155
            # fdb_index maps back to the vlan id!
            (fdb_index, eth_decimals) = fdb_eth_decimals.split('.', 1)
            # the last 6 decimals need to be converted to hex values with hyphens aa-bb-cc-11-22-33
            eth_string = decimal_to_hex_string_ethernet(eth_decimals)
            port_id = int(val)
            fdb_index = int(fdb_index)
            # PortID=0 indicates known ethernet, but unknown port, i.e. ignore
            if port_id:
                if_index = self._get_if_index_from_port_id(port_id)
                if if_index in self.interfaces.keys():
                    # make sure we use consistent string representation of this ethernet address:
                    e = EthernetAddress(eth_string)
                    e.dialect = settings.MAC_DIALECT
                    if self.vlan_id_context > 0:
                        # we are explicitly in a vlan context! (vendor specific implementation)
                        e.vlan_id = self.vlan_id_context
                    else:
                        # see if we can use Forward DB mapping:
                        # double lookup: from fdb index find vlan index, then from vlan index find vlan id!
                        """
                        vlan_index = self.dot1tp_fdb_to_vlan_index.get(fdb_index, 0)
                        vlan_id = self.vlan_id_by_index.get(vlan_index, 0)
                        dprint(f"Eth found in fdb_index {fdb_index} => vlan_index {vlan_index} => vlan_id {vlan_id}")
                        """
                        e.vlan_id = self.vlan_id_by_index.get(self.dot1tp_fdb_to_vlan_index.get(fdb_index, 0), 0)
                        # if vlan_id is still 0, if could be the fbd_index is the vlan id!
                        if e.vlan_id == 0:
                            # if fdb_index is a valid vlan id, assume so!
                            if fdb_index in self.vlans.keys():
                                e.vlan_id = fdb_index
                    dprint(f"  NEW MAC: {e}, vlan: {e.vlan_id}, interface {self.interfaces[if_index].name}")
                    if str(e) not in self.interfaces[if_index].eth:
                        self.interfaces[if_index].eth[str(e)] = e
                        self.eth_addr_count += 1
                        dprint("  Ethernet Added!")
                    else:
                        dprint(f"  Duplicate MAC: {e}")
                else:
                    dprint(f"  if_index = {if_index}: NOT FOUND!")
            return True
        return False

    def _parse_mibs_net_to_media(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the (various) Net-To-Media (ie ARP) mibs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint("_parse_mibs_net_to_media()")

        # First the old style ipNetToMedia tables
        # we take some shortcuts here by not using the mappings through ipNetToMediaIfIndex and ipNetToMediaNetAddress
        if_ip_string = oid_in_branch(ipNetToMediaPhysAddress, oid)
        if if_ip_string:
            parts = if_ip_string.split('.', 1)  # 1 means one split, two elements!
            if_index = str(parts[0])
            ip = str(parts[1])
            dprint(f"IfIndex={if_index}, IP={ip}")
            if if_index in self.interfaces.keys():
                mac_addr = bytes_ethernet_to_string(val)
                dprint(f"   MAC={mac_addr}")
                # see if we can add this to a known ethernet address
                # time consuming, but useful
                for iface in self.interfaces.values():
                    if mac_addr in iface.eth.keys():
                        # Found existing MAC addr, adding IP4
                        iface.eth[mac_addr].address_ip4 = ip

            return True

        """
        Next (eventually) the newer ipNetToPhysical tables
        Note: we have not found any device yet that returns this!
        """
        return False

    def _parse_mibs_net_to_physical(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the (various) Net-To-Physical (ie new ARP) mibs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint("_parse_mibs_net_to_physical()")

        # Here is the new style ipNetToPhysicalPhysAddress entry
        if_ip_string = oid_in_branch(ipNetToPhysicalPhysAddress, oid)
        if if_ip_string:
            # the returned OID format is:
            # ipNetToPhysicalPhysAddress.<if-index>.<address-type>.<length>."ip address in dotted format" = "mac address"
            # no if_ip_string = <if-index>.<address-type>.<length>."ip address in dotted format"
            # address-type = IANA_TYPE_IPV4 (1) or IANA_TYPE_IPV6 (2)
            parts = if_ip_string.split('.', 2)  # split in 3: if-index, address-type, and the rest

            if_index = str(parts[0])
            iface = self.get_interface_by_key(key=if_index)
            if not iface:
                # should not happen, not sure what to do here!
                dprint(f"  OID '{oid}' = '{val}', parsed if_index='{if_index}' to unknown interface!")
                return True  # we did parse this, with errors.

            addr_type = int(parts[1])
            dprint(f"  Interface '{iface.name}', IP address type={addr_type}")
            # the rest is IP, either v4 or v6
            ip = get_ip_from_oid_index(index=parts[2], addr_type=addr_type)
            # we currently only deal with IPv4:
            if addr_type == IANA_TYPE_IPV4:
                dprint(f"    IPV4={ip}")
                mac_addr = bytes_ethernet_to_string(val)
                dprint(f"    MAC={mac_addr}")
                if mac_addr in iface.eth.keys():
                    # Found existing MAC addr, adding IP4
                    iface.eth[mac_addr].address_ip4 = ip
                else:
                    iface.add_learned_ethernet_address(eth_address=mac_addr, ip4_address=ip)

            return True

        """
        Next (eventually) the newer ipNetToPhysical tables
        Note: we have not found any device yet that returns this!
        """
        return False

        #
        # LACP MIB parsing
        #

    def _parse_mibs_lacp(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the LACP MIBs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_lacp() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        """
        Parse a single OID with data returned from the LACP MIB
        Will return True if we have parsed this, and False if not.
        """

        # this gets the aggregator interface admin key or "index"
        # note that aggregator index is an integer according to MIB, but
        # we use it as a string value for the interfaces{} dictionary key!!!
        aggr_if_index = oid_in_branch(dot3adAggActorAdminKey, oid)
        if aggr_if_index:
            # this interface is a aggregator!
            if aggr_if_index in self.interfaces.keys():
                self.interfaces[aggr_if_index].lacp_type = LACP_IF_TYPE_AGGREGATOR
                self.interfaces[aggr_if_index].lacp_admin_key = int(val)
                # some vendors (certain Cisco switches) set the IF-MIB::ifType to Virtual (53) instead of LAGG (161)
                # hardcode to LAGG:
                self.interfaces[aggr_if_index].type = IF_TYPE_LAGG
                dprint(f"LACP MASTER FOUND: {self.interfaces[aggr_if_index].name}")
            return True

        # this get the member interfaces admin key ("index"), which maps back to the aggregator interface above!
        member_if_index = oid_in_branch(dot3adAggPortActorAdminKey, oid)
        # note that member_index is an integer according to MIB, but
        # we use it as a string value for the interfaces{} dictionary key!!!
        if member_if_index:
            # this interface is an lacp member!
            if member_if_index in self.interfaces.keys():
                # can we find an aggregate with this key value ?
                lacp_key = int(val)
                for lacp_index, iface in self.interfaces.items():
                    if iface.lacp_type == LACP_IF_TYPE_AGGREGATOR and iface.lacp_admin_key == lacp_key:
                        # the current interface is a member of this aggregate iface !
                        self.interfaces[member_if_index].lacp_type = LACP_IF_TYPE_MEMBER
                        # note that lacp_index is an integer according to MIB, but
                        # we use it as a string value for the interfaces{} dictionary key!!!
                        self.interfaces[member_if_index].lacp_master_index = int(lacp_index)
                        self.interfaces[member_if_index].lacp_master_name = iface.name
                        # add our name to the list of the aggregate interface
                        self.interfaces[lacp_index].lacp_members[member_if_index] = self.interfaces[
                            member_if_index
                        ].name
                        dprint(f"LACP MEMBER FOUND: {self.interfaces[member_if_index].name}")
            return True

        """
        # LACP port membership, may only valid once an interface is "up" and has joined the aggregate
        member_if_index = int(oid_in_branch(dot3adAggPortAttachedAggID, oid))
        if member_if_index:
            lacp_if_index = int(val)
            if lacp_if_index > 0:
                dprint(f"Member ifIndex {member_if_index} is part of LACP ifIndex {lacp_if_index})
                if member_if_index in self.interfaces.keys() and lacp_if_index in self.interfaces.keys():
                    # from this one read, we can get the aggregate ifIndex for the virtual interface
                    # (and name, for display convenience)
                    self.interfaces[member_if_index].lacp_master_index = lacp_if_index
                    self.interfaces[member_if_index].lacp_master_name = self.interfaces[lacp_if_index].name
                    # and also the member interface (i.e. the physical interface!)
                    self.interfaces[lacp_if_index].lacp_members[member_if_index] = self.interfaces[member_if_index].name
            return True
        """

        # we did not parse the OID.
        return False

    #
    # Interface IP Address MIB parsing
    #
    def _parse_mibs_ip_addr_table(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the "ipAddrTable" Interface IP address MIBs.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_ip_addr_table() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        """
        Handle the device IP addresses, e.g. interface ip, vlan ip, etc.
        """
        ip = oid_in_branch(ipAdEntIfIndex, oid)
        if ip:
            # snmp oid return value is the string "if_index"
            # Interfaces are indexed by string index, ie the 'val' returned:
            if val in self.interfaces.keys():
                # store IP and interface index (as str) for lookup of netmask below
                self.ip4_to_if_index[ip] = val
                # no need to store yet:
                # self.interfaces[val].add_ip4_network(ip)
            return True

        ip = oid_in_branch(ipAdEntNetMask, oid)
        if ip:
            # OID return value is netmask
            # we should have found the IP address already above!
            if ip in self.ip4_to_if_index.keys():
                if_key = self.ip4_to_if_index[ip]
                # make sure we have an interface for this key:
                if if_key in self.interfaces.keys():
                    # now add this IP / Netmask combo to this interface:
                    self.interfaces[if_key].add_ip4_network(f"{ip}/{val}")
            return True

        # we did not parse the OID.
        return False

    #
    # New IP-MIB - Interface IP Address MIB parsing
    #
    def _parse_mibs_ip_address_table(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the "ipAddressIfIndex" Interface IP address MIBs.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_ip_address_table() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        """
        Find a device IP addresses. Returned OID is ipAddressIfIndex.<address-type>.<length>.<ip-address> = <if-index>
        """
        oid_ip_string = oid_in_branch(ipAddressIfIndex, oid)
        if oid_ip_string:
            # sub_oid return value is the string "<ip-type>.<lenth>.<ip-address>"
            # "val" is ifIndex, validate that first. Note 'val' is already a "str" object:
            iface = self.get_interface_by_key(key=val)
            if iface:
                # go parse the IP address:
                parts = oid_ip_string.split('.', 1)  # split in 2, address-type, and the address
                addr_type = int(parts[0])
                dprint(f"  Interface '{iface.name}', IP type={addr_type}")
                # the rest is IP, either v4 or v6
                ip = get_ip_from_oid_index(index=parts[1], addr_type=addr_type)
                # we currently only deal with IPv4:
                if addr_type == IANA_TYPE_IPV4:
                    dprint(f"    IPV4={ip}")
                    # add to the interface:
                    iface.add_ip4_network(address=ip, prefix_len=32)
                elif addr_type == IANA_TYPE_IPV6:
                    dprint("   IPV6 NOT HANDLED YET! Ignored!")
                else:  # should not happen...
                    dprint(f"INVALID IP ADDRESS TYPE {addr_type}")
            else:
                # should not happen!
                dprint(f"ERROR: Interface NOT found for key '{val}'")
            return True

        # we did not parse the OID.
        return False

    #
    # SYSLOG-MSG MIB
    #
    def _parse_mibs_syslog_msg(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the "SYSLOG-MSG" MIB.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_syslog_msg() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        """
        SYSLOG-MSG-MIB - mostly meant to define notification, but we can read the log size
        """
        sub_oid = oid_in_branch(syslogMsgTableMaxSize, oid)
        if sub_oid:
            # this is the max number of syslog messages stored.
            self.syslog_max_msgs = int(val)
            return True
        """
        Note: the rest of the SYSLOG_MSG_MIB is meant to define OID's for sending
        SNMP traps with syslog messages, NOT to poll messages from snmp reads !!!
        """

    #
    # POE parsing - first Power Supplies
    #
    def _parse_mibs_poe_supply(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the Poe MIBs related to power supplies.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_poe_supply() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        """
        PoE related entries:
        the pethMainPseEntry table entries with device-level PoE info
        the OID is <base><device-id>.1 = <value>,
        where <device-id> is stack member number, vendor and device specific!
        """

        pse_id = int(oid_in_branch(pethMainPsePower, oid))
        if pse_id:
            self.poe_capable = True
            self.poe_max_power += int(val)  # in Watts
            # store data about individual PSE unit:
            if pse_id not in self.poe_pse_devices.keys():
                self.poe_pse_devices[pse_id] = PoePSE(pse_id)
            # update max power
            self.poe_pse_devices[pse_id].max_power = int(val)  # in Watts
            return True

        pse_id = int(oid_in_branch(pethMainPseOperStatus, oid))
        if pse_id:
            # not yet sure how to handle this, for now just read
            self.poe_capable = True
            self.poe_enabled = int(val)
            # store data about individual PSE unit:
            if pse_id not in self.poe_pse_devices.keys():
                self.poe_pse_devices[pse_id] = PoePSE(pse_id)
            # update status
            self.poe_pse_devices[pse_id].status = int(val)
            return True

        pse_id = int(oid_in_branch(pethMainPseConsumptionPower, oid))
        if pse_id:
            self.poe_capable = True
            self.poe_power_consumed += int(val)  # this is in Watts (not milliWatts !)
            # store data about individual PSE unit:
            if pse_id not in self.poe_pse_devices.keys():
                self.poe_pse_devices[pse_id] = PoePSE(pse_id)
            # update max power
            self.poe_pse_devices[pse_id].power_consumed = int(val)  # in Watts !
            return True

        pse_id = int(oid_in_branch(pethMainPseUsageThreshold, oid))
        if pse_id:
            self.poe_capable = True
            # store data about individual PSE unit:
            if pse_id not in self.poe_pse_devices.keys():
                self.poe_pse_devices[pse_id] = PoePSE(pse_id)
            # update max power
            self.poe_pse_devices[pse_id].threshold = int(val)
            return True

        # we did not parse the OID.
        return False

    #
    # PoE - the Power Per Port data.
    #

    def _parse_mibs_poe_port(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the Poe MIBs related to port power.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_poe_port() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        """
        the pethPsePortEntry tables with port-level PoE info
        OID is followed by PortEntry index (pe_index). This is typically
        or module_num.port_num for modules switch chassis, or
        device_id.port_num for stack members.
        This gets mapped to an interface later on in
        self._map_poe_port_entries_to_interface(), which is typically device specific
        (i.e. implemented in the device-specific classes in
        vendor/cisco/snmp.py, vendor/comware/snmp.py, etc.)
        """

        pe_index = oid_in_branch(pethPsePortAdminEnable, oid)
        if pe_index:
            self.poe_port_entries[pe_index] = PoePort(pe_index, int(val))
            return True

        pe_index = oid_in_branch(pethPsePortDetectionStatus, oid)
        if pe_index:
            if pe_index in self.poe_port_entries.keys():
                self.poe_port_entries[pe_index].detect_status = int(val)
            return True

        """
        These are currently not used:
        pe_index = oid_in_branch(pethPsePortPowerPriority, oid)
        if pe_index:
            if pe_index in self.poe_port_entries.keys():
                self.poe_port_entries[pe_index].priority = int(val)
            return True

        pe_index = oid_in_branch(pethPsePortType, oid)
        if pe_index:
            if pe_index in self.poe_port_entries.keys():
                self.poe_port_entries[pe_index].description = str(val)
            return True
        """

        # we did not parse the OID.
        return False

    #
    # LLDP MIB parsing
    #

    def _parse_mibs_lldp(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the LLDP MIBs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_lldp() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        # we are not looking at this at this time, already have it from IF MIB
        # lldp = oid_in_branch(lldpLocPortTable, oid)
        # if lldp:
        #    dprint(f"LLDP LOCAL PORT ENTRY {lldp} = {str(val)}")
        #    return True

        # this does not appear to be implemented in most gear:
        # lldp = oid_in_branch(lldpRemLocalPortNum, oid)
        # if lldp:
        #    dprint(f"LLDP REMOTE_LOCAL PORT ENTRY {lldp} = {str(val)}")
        #    return True

        # the following are indexed by  <remote-device-random-id>.<port-id>.1
        # if Q-BRIDGE is implemented, <port-id> is that port_id, mapped in self.qbridge_port_to_if_index[port_id]
        # if Q-BRIDGE is NOT implemented, <port-id> = <ifIndex>, ie without the mapping
        lldp_index = oid_in_branch(lldpRemPortId, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            # store the new lldp object, based on the string index.
            # need to find the ifIndex first.
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                # add new LLDP neighbor
                # self.interfaces[if_index].lldp[lldp_index] = NeighborDevice(lldp_index, if_index)
                neighbor = NeighborDevice(lldp_index)
                # val is likely the "name" of the remote port, depending on the value of "lldapRemPortIdSubType" !
                neighbor.port_name = val
                # and add to interface lldp info:
                self.interfaces[if_index].lldp[lldp_index] = neighbor
                self.neighbor_count += 1
            return True

        # lldpRemPortIdSubType is used to indicate what the value from "lldpRemPortId" means.
        lldp_index = oid_in_branch(lldpRemPortIdSubType, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            # store the new lldp object, based on the string index.
            # need to find the ifIndex first.
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                sub_type = int(val)
                # depending on type, we may need to blank neighbor.port_name!
                # we 'think' we can handle these: LLDP_PORT_SUBTYPE_INTERFACE_ALIAS, LLDP_PORT_SUBTYPE_MAC_ADDRESS
                # LLDP_PORT_SUBTYPE_NETWORK_ADDRESS, LLDP_PORT_SUBTYPE_INTERFACE_NAME
                # not sure how to interpret these:
                if sub_type in (
                    LLDP_PORT_SUBTYPE_CHASSIS_COMPONENT,
                    LLDP_PORT_SUBTYPE_PORT_COMPONENT,
                    LLDP_PORT_SUBTYPE_LOCAL,
                ):
                    dprint(f"  Clearning LLDP.port_name - interface subtype: {sub_type}")
                    self.interfaces[if_index].lldp[lldp_index].port_name = ""
            return True

        lldp_index = oid_in_branch(lldpRemPortDesc, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            # at this point, we should have already found the lldp neighbor and created an object
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                if lldp_index in self.interfaces[if_index].lldp.keys():
                    # now update with system port description
                    self.interfaces[if_index].lldp[lldp_index].port_descr = str(val)
            return True

        lldp_index = oid_in_branch(lldpRemSysName, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            # at this point, we should have already found the lldp neighbor and created an object
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                if lldp_index in self.interfaces[if_index].lldp.keys():
                    # now update with system name
                    self.interfaces[if_index].lldp[lldp_index].sys_name = str(val)
            return True

        lldp_index = oid_in_branch(lldpRemSysDesc, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            port_id = int(port_id)
            # at this point, we should have already found the lldp neighbor and created an object
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                if lldp_index in self.interfaces[if_index].lldp.keys():
                    # now update with system description
                    self.interfaces[if_index].lldp[lldp_index].sys_descr = str(val)
            return True

        # parse enabled capabilities
        lldp_index = oid_in_branch(lldpRemSysCapEnabled, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            # at this point, we should have already found the lldp neighbor and created an object
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                if lldp_index in self.interfaces[if_index].lldp.keys():
                    # now update with system capabilities
                    cap_bytes = bytes(val, 'utf-8')
                    # self.interfaces[if_index].lldp[lldp_index].capabilities = cap_bytes
                    self.interfaces[if_index].lldp[lldp_index].capabilities = int(cap_bytes[0])
            return True

        lldp_index = oid_in_branch(lldpRemChassisIdSubtype, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            # at this point, we should have already found the lldp neighbor and created an object
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                if lldp_index in self.interfaces[if_index].lldp.keys():
                    # now update with system chassis type
                    if self.interfaces[if_index].lldp[lldp_index].chassis_type > LLDP_CHASSIS_TYPE_NONE:
                        self.add_warning(
                            f"Chassis Type for {lldp_index} already "
                            "{self.interfaces[if_index].lldp[lldp_index].chassis_type},"
                            " now {val}!"
                        )
                    self.interfaces[if_index].lldp[lldp_index].chassis_type = int(val)
            return True

        lldp_index = oid_in_branch(lldpRemChassisId, oid)
        if lldp_index:
            (extra_one, port_id, extra_two) = lldp_index.split('.')
            # at this point, we should have already found the lldp neighbor and created an object
            # did we find Q-Bridge mappings?
            if_index = self._get_if_index_from_port_id(int(port_id))
            if if_index in self.interfaces.keys():
                if lldp_index in self.interfaces[if_index].lldp.keys():
                    # now update with system chassis info, but only chassis type is known
                    # (it should be at this time)
                    neighbor = self.interfaces[if_index].lldp[lldp_index]
                    if neighbor.chassis_type > LLDP_CHASSIS_TYPE_NONE:
                        if neighbor.chassis_type == LLDP_CHASSIC_TYPE_ETH_ADDR:
                            chassis_info = bytes_ethernet_to_string(val)
                        elif neighbor.chassis_type == LLDP_CHASSIC_TYPE_NET_ADDR:
                            # per MIB LldpChassisId, the first byte is the IANA Address Family Number:
                            net_addr_type = int(ord(val[0]))
                            if net_addr_type == IANA_TYPE_IPV4:
                                neighbor.chassis_string_type = IANA_TYPE_IPV4
                                addr_bytes = val[1:]
                                chassis_info = ".".join("%d" % ord(b) for b in addr_bytes)
                            elif net_addr_type == IANA_TYPE_IPV6:
                                neighbor.chassis_string_type = IANA_TYPE_IPV6
                                addr_bytes = val[1:]
                                chassis_info = ":".join("%d" % ord(b) for b in addr_bytes)
                                # we should simplify this here - TBD
                            else:
                                chassis_info = 'Unknown Address Type'
                        else:
                            # we don't parse this chassis_type, so just assume it is a string :-)
                            chassis_info = str(val)
                        neighbor.chassis_string = chassis_info

            return True
        return False

    def _parse_mibs_lldp_management(self, oid: str, val: str) -> bool:
        """Parse LLDP entries related to remote management info.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"_parse_mibs_lldp_management() {str(oid)}, len = {len(val)}, type = {str(type(val))}")

        # these 2 do not seems to be implemented!
        # # the management address type, ie ipv4 or ipv6:
        # lldp_index = oid_in_branch(lldpRemManAddrSubtype, oid)
        # if lldp_index:
        #     (extra_one, port_id, extra_two) = lldp_index.split('.')
        #     # at this point, we should have already found the lldp neighbor and created an object
        #     # did we find Q-Bridge mappings?
        #     if_index = self._get_if_index_from_port_id(int(port_id))
        #     if if_index in self.interfaces.keys():
        #         if lldp_index in self.interfaces[if_index].lldp.keys():
        #             # store management address type
        #             self.interfaces[if_index].lldp[lldp_index].management_address_type = int(val)
        #     return True

        # # the actual management address:
        # lldp_index = oid_in_branch(lldpRemManAddr, oid)
        # if lldp_index:
        #     (extra_one, port_id, extra_two) = lldp_index.split('.')
        #     # at this point, we should have already found the lldp neighbor and created an object
        #     # did we find Q-Bridge mappings?
        #     if_index = self._get_if_index_from_port_id(int(port_id))
        #     if if_index in self.interfaces.keys():
        #         if lldp_index in self.interfaces[if_index].lldp.keys():
        #             # set management address
        #             self.interfaces[if_index].lldp[lldp_index].management_address = val
        #     return True

        sub_oid = oid_in_branch(lldpRemManAddrIfSubtype, oid)
        if sub_oid:
            numbers = sub_oid.split('.')
            # dprint(f"  FOUND lldpRemManAddrIfSubtype, size {len(numbers)}, val = {int(val)}")
            # some bizarre "checking" for the right OID format. It appears to be:
            # 3 digits for LLDP index (index, port_id, extra), then "1.4", following by IP in dotted format, eg "10.1.1.1"
            if (
                len(numbers) == 9
                and int(val) in (LLDP_REM_MAN_ADDR_TYPE_IFINDEX, LLDP_REM_MAN_ADDR_TYPE_SYSTEMPORTNUMBER)
                and numbers[3] == '1'
                and numbers[4] == '4'
            ):
                # dprint("  LLDP FOUND MGMT IPv4 !")
                # this appears to be an IPv4 address embedded in sub-OID
                port_id = int(numbers[1])
                lldp_index = f"{numbers[0]}.{numbers[1]}.{numbers[2]}"
                # at this point, we should have already found the lldp neighbor and created an object
                # did we find Q-Bridge mappings?
                if_index = self._get_if_index_from_port_id(port_id)
                # dprint(f"  INFO: lldp_index='{lldp_index}', port_id='{port_id}', if_index='{if_index}'")
                if if_index in self.interfaces.keys():
                    if lldp_index in self.interfaces[if_index].lldp.keys():
                        # set management address
                        mgmt_ip = f"{numbers[5]}.{numbers[6]}.{numbers[7]}.{numbers[8]}"
                        dprint(f"  SETTING MGMT IPv4 = {mgmt_ip}")
                        self.interfaces[if_index].lldp[lldp_index].management_address = mgmt_ip
                        self.interfaces[if_index].lldp[lldp_index].management_address_type = IANA_TYPE_IPV4
            return True
        return False

    def _add_vlan_to_interface_by_port_id(self, port_id: int, vlan_id: int):
        """
        Add a given vlan to the interface identified by the dot1d bridge port id
        """
        dprint(f"_add_vlan_to_interface_by_port_id() port id {port_id} vlan {vlan_id}")

        # get the interface index first:
        if_index = self._get_if_index_from_port_id(port_id)
        if if_index in self.interfaces.keys():
            if self.interfaces[if_index].untagged_vlan == vlan_id:
                dprint("   PVID already set!")
                # interface already has this untagged vlan, not adding
                return True
            else:
                dprint("   Add as tagged?")
                # only add vlan once, and only if defined!
                if vlan_id in self.vlans.keys() and vlan_id not in self.interfaces[if_index].vlans:
                    dprint("      yes!")
                    self.interfaces[if_index].vlans.append(vlan_id)
                    self.interfaces[if_index].is_tagged = True
            return True
        return False

    def _add_untagged_vlan_to_interface_by_port_id(self, port_id: int, vlan_id: int):
        """
        Add a given vlan as untaggfed to the interface identified by the dot1d bridge port id
        """
        dprint(f"_add_untagged_vlan_to_interface_by_port_id() port id {port_id} vlan {vlan_id}")

        # get the interface index first:
        if_index = self._get_if_index_from_port_id(port_id)
        if if_index in self.interfaces.keys():
            if self.interfaces[if_index].untagged_vlan == 0:
                dprint("   PVID was 0, now set!")
                self.interfaces[if_index].untagged_vlan = vlan_id
                return True
            elif self.interfaces[if_index].untagged_vlan == vlan_id:
                dprint("   PVID already set!")
                # interface already has this untagged vlan, not adding
                return True
            else:
                dprint(f"   PVID was {self.interfaces[if_index].untagged_vlan}, now set!")  # should not happend
                self.interfaces[if_index].untagged_vlan = vlan_id
                return True
        dprint(f"if_index '{if_index}' not found!")
        return False

    def _parse_mibs_entity_physical(self, oid: str, val: str) -> bool:
        """
        Parse a single OID with data returned from the (various) Entity-Physical mib entries.
        ENTITY MIB, info about the device, eg stack or single unit, # of units, serials
        and other interesting pieces. We are looking at Chassis, Stack, or Module info only,
        not sensors, etc.

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint("")
        hw_to_check = [ENTITY_CLASS_STACK, ENTITY_CLASS_CHASSIS, ENTITY_CLASS_MODULE]
        dprint("_parse_mibs_entity_physical()")
        dev_id = int(oid_in_branch(entPhysicalClass, oid))
        if dev_id:
            dev_type = int(val)
            if dev_type in hw_to_check:
                # save this info!
                member = StackMember(dev_id, dev_type)
                self.stack_members[dev_id] = member
            return True

        dev_id = int(oid_in_branch(entPhysicalDescr, oid))
        if dev_id:
            if dev_id in self.stack_members.keys():
                self.stack_members[dev_id].description = str(val)
            return True

        dev_id = int(oid_in_branch(entPhysicalSerialNum, oid))
        if dev_id:
            if dev_id in self.stack_members.keys():
                self.stack_members[dev_id].serial = str(val)
            return True

        dev_id = int(oid_in_branch(entPhysicalSoftwareRev, oid))
        if dev_id:
            if dev_id in self.stack_members.keys():
                self.stack_members[dev_id].version = str(val)
            return True

        dev_id = int(oid_in_branch(entPhysicalModelName, oid))
        if dev_id:
            if dev_id in self.stack_members.keys():
                self.stack_members[dev_id].model = str(val)
            return True

        # not parsed here!
        return False

    def _get_if_index_from_port_id(self, port_id: int) -> str:
        """
        Return the ifIndex from the Q-Bridge port_id. This assumes we have walked
        the Q-Bridge mib that maps bridge port id to interfaceId.

        params:
            port_id (str): the string integer port-id associated with an interface,
                           as mapped via q-bridge port-to-if-index!

        returns:
            (str): the string representation of the interface index for this Q-Bridge port.
        """
        dprint(f"_get_if_index_from_port_id(port_id={port_id} ({type(port_id)})")
        port_id = int(port_id)  # make sure we have the proper type!
        # if len(self.qbridge_port_to_if_index) > 0 and port_id in self.qbridge_port_to_if_index.keys():
        if port_id in self.qbridge_port_to_if_index.keys():
            dprint(f"  Found in port_to_if_index = {self.qbridge_port_to_if_index[port_id]}")
            return self.qbridge_port_to_if_index[port_id]
        else:
            # we did not find the Q-BRIDGE mib. port_id = ifIndex !
            dprint("  port_id NOT FOUND, returning port_id as if_index")
            return str(port_id)  # if_index is the interface key as string!

    def _get_port_id_from_if_index(self, if_index: str) -> int:
        """
        Return the bridge PortId for the given interface index. This assumes we have walked
        the Q-Bridge mib that maps bridge port id to interfaceId.

        params:
            if_index (str): the index for an interface.

        returns:
            (str): the string representation of theQ-Bridge port id for this interface index.
        """
        if_index = str(if_index)
        if if_index in self.interfaces.keys() and len(self.qbridge_port_to_if_index) > 0:
            for port_id, index in self.qbridge_port_to_if_index.items():
                if if_index == index:
                    return port_id
        # we did not find the Q-BRIDGE mib. or could not find if_index,
        # return if_index as port_id !
        return int(if_index)  # port_id is integer!

    def _get_port_id_from_interface(self, interface: Interface) -> int:
        """
        Return the bridge PortId for the given interface object. This assumes we have walked
        the Q-Bridge mib that maps bridge port id to interfaceId.

        params:
            interface (Interface): a valid Interface for this device.

        returns:
            (int): the Q-Bridge port_id for this interface.
        """
        if interface.port_id != -1:
            return interface.port_id
        else:
            # we did not find the Q-BRIDGE mib. port_id = ifIndex !
            return int(interface.index)  # port_id is integer!

    def _parse_mibs_system(self, oid: str, value: str) -> bool:
        """
        parse the basic 6 system mib entries.
        ie.sys-descr, object-id, uptime, contact, name & location
        """
        dprint("_parse_mibs_system()")

        if oid == sysName:
            self.hostname = value
            self.add_more_info('System', 'Hostname', self.hostname)
            return True
        if oid == sysUpTime:
            self.sys_uptime = int(value)
            self.sys_uptime_timestamp = time.time()
            self.add_more_info('System', 'Uptime', str(datetime.timedelta(seconds=(self.sys_uptime / 100))))
            return True
        if oid == sysObjectID:
            self.object_id = value
            self.add_more_info('System', 'Object ID', value)
            return True
        if oid == sysDescr:
            self.add_more_info('System', 'Model', value)
            return True
        if oid == sysContact:
            self.add_more_info('System', 'Contact', value)
            return True
        if oid == sysLocation:
            self.add_more_info('System', 'Location', value)
            return True
        return False

    def _get_sys_uptime(self) -> None:
        """
        Get the current sysUpTime timetick for the device.
        """
        (error_status, snmpval) = self.get(sysUpTime, parser=self._parse_mibs_system)
        # sysUpTime is ticks in 1/100th of second since boot
        self.sys_uptime_timestamp = time.time()

    def _get_system_data(self) -> int:
        """
        get just the System-MIB parts, ie OID, Location, etc.
        Return a negative value if error occured, or 1 if success
        """
        retval = self.get_snmp_branch(branch_name='system', parser=self._parse_mibs_system)
        if retval < 0:
            self.add_warning("Error getting 'System-Mib' (system)")
            return retval  # error of some kind

        # add some more info about the configuration/settings
        self.add_more_info('System', 'IP/Hostname', self.switch.primary_ip4)
        if self.switch.snmp_profile:
            snmp_profile_name = self.switch.snmp_profile.name
        else:
            snmp_profile_name = "NOT SET!"
        self.add_more_info('System', 'Snmp Profile', snmp_profile_name)
        self.add_more_info('System', 'Vendor ID', get_switch_enterprise_info(self.object_id))
        # first time when data was read:
        self.add_more_info(
            'System', 'Read Time', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.sys_uptime_timestamp))
        )

        # see if the hostname changed
        if self.hostname:
            if self.switch.hostname != self.hostname:
                self.switch.hostname = self.hostname
                self.switch.save()
                self.add_log(
                    type=LOG_TYPE_WARNING, action=LOG_NEW_HOSTNAME_FOUND, description="New System Hostname found"
                )

        return 1

    def _get_hardware_data(self) -> int:
        """
        read the various Entity OIDs for the basic data we want
        This reads information about the modules, software revisions, etc.
        Return a negative value if error occured, or 1 if success
        """
        # do NOT just get the whole entity-Physical branch:
        # get physical device class info first, since we filter on some types of classes! this!
        retval = self.get_snmp_branch(branch_name='entPhysicalClass', parser=self._parse_mibs_entity_physical)
        if retval < 0:
            self.add_warning("Error getting 'Entity-Class' ('entPhysicalClass')")
            return retval

        retval = self.get_snmp_branch(branch_name='entPhysicalDescr', parser=self._parse_mibs_entity_physical)
        if retval < 0:
            self.add_warning("Error getting 'Entity-Description' ('entPhysicalDescr')")
            return retval

        retval = self.get_snmp_branch(branch_name='entPhysicalSerialNum', parser=self._parse_mibs_entity_physical)
        if retval < 0:
            self.add_warning("Error getting 'Entity-Serial' (entPhysicalSerialNum)")
            return retval

        retval = self.get_snmp_branch(branch_name='entPhysicalSoftwareRev', parser=self._parse_mibs_entity_physical)
        if retval < 0:
            self.add_warning("Error getting 'Entity-Software' (entPhysicalSoftwareRev)")
            return retval

        retval = self.get_snmp_branch(branch_name='entPhysicalModelName', parser=self._parse_mibs_entity_physical)
        if retval < 0:
            self.add_warning("Error getting 'Entity-Model' (entPhysicalModelName)")
            return retval

        return 1

    def _get_interface_data(self) -> int:
        """
        Get Interface MIB data from the switch. We are not reading the whole MIB-II branch at ifTable,
        but to speed it up, we run individual branches that we need ...
        Returns 1 on succes, -1 on failure
        """
        # it all starts with the interface indexes
        retval = self.get_snmp_branch(branch_name='ifIndex', parser=self._parse_mibs_if_table)
        if retval < 0:
            self.add_warning(f"Error getting 'Interfaces' ({ifIndex})")
            return retval
        # and the types
        retval = self.get_snmp_branch(branch_name='ifType', parser=self._parse_mibs_if_table)
        if retval < 0:
            self.add_warning(f"Error getting 'Interface-Type' ({ifType})")
            return retval

        # the status of the interface, admin up/down, link up/down
        retval = self.get_snmp_branch(branch_name='ifAdminStatus', parser=self._parse_mibs_if_table)
        if retval < 0:
            self.add_warning(f"Error getting 'Interface-AdminStatus' ({ifAdminStatus})")
            return retval
        retval = self.get_snmp_branch(branch_name='ifOperStatus', parser=self._parse_mibs_if_table)
        if retval < 0:
            self.add_warning(f"Error getting 'Interface-OperStatus' ({ifOperStatus})")
            return retval

        # find the interface name, start with the newer IF-MIB
        retval = self.get_snmp_branch(branch_name='ifName', parser=self._parse_mibs_if_x_table)
        if retval < 0:
            self.add_warning(f"Error getting 'Interface-Names' ({ifName})")
            return retval
        if retval == 0:  # newer IF-MIB entries no found, try the old
            retval = self.get_snmp_branch(branch_name='ifDescr', parser=self._parse_mibs_if_table)
            if retval < 0:
                self.add_warning(f"Error getting 'Interface-Descriptions' ({ifDescr})")
                return retval

        # this is the interface description
        retval = self.get_snmp_branch(branch_name='ifAlias', parser=self._parse_mibs_if_x_table)
        if retval < 0:
            self.add_warning(f"Error getting 'Interface-Alias' ({ifAlias})")
            return retval

        # speed is in new IF-MIB
        retval = self.get_snmp_branch(branch_name='ifHighSpeed', parser=self._parse_mibs_if_x_table)
        if retval < 0:
            self.add_warning(f"Error getting 'Interface-HiSpeed' ({ifHighSpeed})")
            return retval
        if retval == 0:  # new IF-MIB hcspeed entry not found, try old speed
            retval = self.get_snmp_branch(branch_name='ifSpeed', parser=self._parse_mibs_if_table)
            if retval < 0:
                self.add_warning(f"Error getting 'Interface-Speed' ({ifSpeed})")
                return retval

        # try to read duplex status
        retval = self.get_snmp_branch(branch_name='dot3StatsDuplexStatus', parser=self._parse_mibs_ether_like)
        if retval < 0:
            self.add_warning(f"Error getting 'Interface-Duplex' ({dot3StatsDuplexStatus})")
            return retval

        # check the connector, if not, cannot be managed, another safety feature
        # retval = self.get_snmp_branch(branch_name='ifConnectorPresent', parser=self._parse_mibs_if_x_table)
        # if retval < 0:
        #    self.add_warning(f"Error getting 'Interface-Connector' ({ifConnectorPresent})")
        #    return retval

        # if not self.get_snmp_branch(branch_name='ifStackEntry', parser=self._parse_mibs_if_stack):
        #    return False
        return 1

    def _get_vlans(self) -> int:
        """
        Read the list of defined vlans on the switch
        Returns error value (if < 0), or count of vlans found (0 or greater)
        """
        # first map dot1D-Bridge ports to ifIndexes, needed for Q-Bridge port-id to ifIndex
        retval = self.get_snmp_branch(branch_name='dot1dBasePortIfIndex', parser=self._parse_mibs_vlan_related)
        if retval < 0:
            self.add_warning(
                "Error getting 'Q-Bridge-PortId-Map' (dot1dBasePortIfIndex), NOT reading VLAN mibs dot1qVlanStaticRowStatus, dot1qVlanStaticName, dot1qVlanStatus, dot1qVlanStaticRowStatus"
            )
            return retval
        # read existing vlan id's from "dot1qVlanStaticTable"
        retval = self.get_snmp_branch(branch_name='dot1qVlanStaticRowStatus', parser=self._parse_mibs_vlan_related)
        if retval < 0:
            self.add_warning("Error getting 'Q-Bridge-Vlan-Rows' (dot1qVlanStaticRowStatus)")
            return retval
        vlan_count = retval
        # if there are vlans, read the name and type
        if retval > 0:
            retval = self.get_snmp_branch(branch_name='dot1qVlanStaticName', parser=self._parse_mibs_vlan_related)
            if retval < 0:
                # error occured (unlikely to happen)
                self.add_warning("Error getting 'Q-Bridge-Vlan-Names' (dot1qVlanStaticName)")
                # we have found VLANs, so we are going to ignore this!
            # read the vlan status, ie static, dynamic!
            retval = self.get_snmp_branch(branch_name='dot1qVlanStatus', parser=self._parse_mibs_vlan_related)
            if retval < 0:
                self.add_warning("Error getting 'Q-Bridge-Vlan-Status' (dot1qVlanStatus)")
                # we have found VLANs, so we are going to ignore this!
        else:
            # retval = 0, no vlans found!
            self.add_warning("No VLANs found at 'Q-Bridge-Vlan-Rows' (dot1qVlanStaticRowStatus)")

        # set vlan count
        self.vlan_count = len(self.vlans)
        return vlan_count

    def _get_port_vlan_membership(self) -> int:
        """
        Read the Q-Bridge MIB vlan and switchport data. Again, to optimize, we read what we need.
        Returns 1 on success, -1 on failure
        """

        # read the PVID of UNTAGGED interfaces.
        retval = self.get_snmp_branch(branch_name='dot1qPvid', parser=self._parse_mibs_vlan_related)
        if retval < 0:
            self.add_warning("Error getting 'Q-Bridge-Interface-PVID' (dot1qPvid)")
            return retval

        # THIS IS LIKELY NOT PROPERLY HANDLED !!!
        # read the current vlan untagged port mappings
        # retval = self.get_snmp_branch(dot1qVlanCurrentUntaggedPorts, parser=self._parse_mibs_vlan_related)
        # if retval < 0:
        #    self.add_warning(f"Error getting 'Q-Bridge-Vlan-Untagged-Interfaces' ({dot1qVlanCurrentUntaggedPorts})")
        #    return retval

        # read the current vlan egress port mappings, tagged and untagged
        retval = self.get_snmp_branch(branch_name='dot1qVlanCurrentEgressPorts', parser=self._parse_mibs_vlan_related)
        if retval < 0:
            self.add_warning("Error getting 'Q-Bridge-Vlan-Egress-Interfaces' (dot1qVlanCurrentEgressPorts)")
            return retval

        # read the 'static' vlan egress port mappings, tagged and untagged
        # this will be used when changing vlans on ports, could also ignore for now!
        # retval = self.get_snmp_branch(dot1qVlanStaticEgressPorts, parser=self._parse_mibs_vlan_related)
        # if retval < 0:
        #    self.add_warning("Error getting 'Q-Bridge-Vlan-Static-Egress-Interfaces' ({dot1qVlanStaticEgressPorts})")
        #    return retval

        return 1

    def _get_vlan_data(self) -> int:
        """
        Get all neccesary vlan info (names, id, ports on vlans, etc.) from the switch.
        Returns -1 on error, or a number to indicate vlans found.
        """
        dprint("#####\n_get_vlan_data()\n#####")
        # get the base 802.1q settings:
        retval = self.get_snmp_branch(branch_name='dot1qBase', parser=self._parse_mib_dot1q_base)
        if self.vlan_count > 0:
            # first get vlan id and names
            self._get_vlans()
            # next, read the interface vlan data
            retval = self._get_port_vlan_membership()
            if retval < 0:
                return retval
            # if GVRP enabled, then read this data
            if self.gvrp_enabled:
                retval = self.get_snmp_branch(branch_name='dot1qPortGvrpStatus', parser=self._parse_mibs_mvrp)

        # check MVRP status:
        retval = self.get_snmp_branch(branch_name='ieee8021QBridgeMvrpEnabledStatus', parser=self._parse_mibs_mvrp)

        dprint("#####\nEND _get_vlan_data()\n#####")

        return self.vlan_count

    def _get_my_ip4_addresses(self) -> int:
        """
        Read the ipAddrEntry tables for the switch IP4 addresses
        Returns 1 on success, -1 on failure
        """
        retval = self.get_snmp_branch(
            branch_name='ipAddrTable', parser=self._parse_mibs_ip_addr_table
        )  # small mib, read all entries below it
        if retval < 0:
            self.add_warning("Error getting 'IP-Address-Entries' (ipAddrTable)")
            return retval
        # also try the newer entry ipAddressIfIndex from IP-MIB ipAddressTable:
        retval = self.get_snmp_branch(branch_name='ipAddressIfIndex', parser=self._parse_mibs_ip_address_table)
        if retval < 0:
            self.add_warning("Error getting 'IP-Address-ifIndex' (ipAddressIfIndex)")

        return 1

    def _map_poe_port_entries_to_interface(self) -> None:
        """
        This function maps the "pethPsePortEntry" indices that are stored in self.poe_port_entries{}
        to interface ifIndex values, so we can store them with the interface and display as needed.
        In general, you can generate the interface ending "x/y" from the index by substituting "." for "/"
        E.g. "5.12" from the index becomes "5/12", and you then search for an interface with matching ending
        e.g. GigabitEthernet5/12
        """
        for pe_index, port_entry in self.poe_port_entries.items():
            end = port_entry.index.replace('.', '/')
            count = len(end)
            for if_index, iface in self.interfaces.items():
                if iface.name[-count:] == end:
                    iface.poe_entry = port_entry
                    break

    def _get_poe_data(self) -> int:
        """
        Read Power-over-Etnernet data, still needs works
        Returns 1 on success, -1 on failure
        """
        # first the PSE entries, ie the power supplies
        retval = self.get_snmp_branch(branch_name='pethMainPseEntry', parser=self._parse_mibs_poe_supply)
        if retval < 0:
            self.add_warning("Error getting 'PoE-PSE-Data' (pethMainPseEntry)")
            return retval
        if retval > 0:
            # found power supplies, look at port power data
            # this is under pethPsePortEntry, but we only need a few entries:
            retval = self.get_snmp_branch(branch_name='pethPsePortAdminEnable', parser=self._parse_mibs_poe_port)
            if retval < 0:
                self.add_warning("Error getting 'PoE-Port-Admin-Status' (pethPsePortAdminEnable)")
            if retval > 0:  # ports with PoE capabilities found!
                retval = self.get_snmp_branch(
                    branch_name='pethPsePortDetectionStatus', parser=self._parse_mibs_poe_port
                )
                if retval < 0:
                    self.add_warning("Error getting 'PoE-Port-Detect-Status' (pethPsePortDetectionStatus)")
                """ Currently not used:
                retval = self.get_snmp_branch(branch_name='pethPsePortPowerPriority', parser=self._parse_mibs_poe_port)
                if retval < 0:
                    self.add_warning("Error getting 'PoE-Port-Detect-Status' (pethPsePortPowerPriority)")
                retval = self.get_snmp_branch(branch_name='pethPsePortType', parser=self._parse_mibs_poe_port)
                if retval < 0:
                    self.add_warning("Error getting 'PoE-Port-Description' (pethPsePortType)")
                """
        return 1

    def _get_known_ethernet_addresses(self) -> bool:
        """
        Read the Bridge-MIB for known ethernet address on the switch.
        Returns True on success (0 or more addresses found), False on error
        """

        # next, read the known ethernet addresses, and add to the Interfaces.
        # Do NOT cache and use a custom parser for speed

        # First, the newer dot1q bridge mib
        retval = self.get_snmp_branch(branch_name='dot1qTpFdbPort', parser=self._parse_mibs_q_bridge_eth)
        if retval < 0:
            # error!
            self.add_warning("Error getting 'Q-Bridge-EthernetAddresses' (dot1qTpFdbPort)")
            return False
        # If nothing found,check the older dot1d bridge mib
        if retval == 0:
            retval = self.get_snmp_branch(branch_name='dot1dTpFdbPort', parser=self._parse_mibs_dot1d_bridge_eth)
            if retval < 0:
                self.add_warning("Error getting 'Bridge-EthernetAddresses' (dot1dTpFdbPort)")
                return False
        return True

    def _get_arp_data(self) -> bool:
        """
        Read the arp tables from both old style ipNetToMedia,
        and eventually, new style ipNetToPhysical
        Returns True on success, False on failure
        """
        retval = self.get_snmp_branch(branch_name='ipNetToMediaPhysAddress', parser=self._parse_mibs_net_to_media)
        if retval < 0:
            self.add_warning("Error getting 'ARP-Table' (ipNetToMediaPhysAddress)")
            return False
        # check the newer ipNetToPhysical tables as well:
        retval = self.get_snmp_branch(branch_name='ipNetToPhysicalPhysAddress', parser=self._parse_mibs_net_to_physical)
        if retval < 0:
            self.add_warning("Error getting 'new ARP-Table' (ipNetToPhysicalPhysAddress)")
            return False
        return True

    def _get_lldp_data(self) -> bool:
        """
        Read parts of the LLDP mib for neighbors on interfaces
        Note that this needs to be called after _get_known_ethernet_addresses()
        as we need the Bridge-to-IfIndex mapping that is loaded there!
        Returns True on success, False on failure
        """
        # Probably don't need this part, already got most from MIB-2
        # retval = not self.get_snmp_branch(lldpLocPortTable, parser=self._parse_mibs_lldp):
        #    return False

        # this does not appear to be implemented in most gear:
        # retval = not self.get_snmp_branch(lldpRemLocalPortNum, parser=self._parse_mibs_lldp):
        #    return False

        # this should catch all the remote device info:
        # retval = not self.get_snmp_branch(lldpRemEntry, parser=self._parse_mibs_lldp):
        #    return False
        # return True

        # go read and parse LLDP data, we do NOT (False) want to cache this data!
        # we have a custom parser, so we do not have to run this through the long and slow default parser!
        # start with "lldpRemPortId", this gives us the local port a neighbor is heard on
        # so we can start with a NeighborDevice() object attached to the proper device Interface().lldp{}
        # the value of "lldpRemPortId" also gives us the name of the remote device interface we are
        # connected to (see _parse_mibs_lldp() for more)
        retval = self.get_snmp_branch(branch_name='lldpRemPortId', parser=self._parse_mibs_lldp)
        if retval < 0:
            self.add_warning("Error getting 'LLDP-Remote-Ports' (lldpRemPortId)")
            return False
        if retval > 0:  # there are neighbors entries! Go get the details.
            retval = self.get_snmp_branch(branch_name='lldpRemPortIdSubType', parser=self._parse_mibs_lldp)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-Port-ID-Subtype' (lldpRemPortIdSubType)")
                return False
            retval = self.get_snmp_branch(branch_name='lldpRemPortDesc', parser=self._parse_mibs_lldp)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-Port-Description' (lldpRemPortDesc)")
                return False
            retval = self.get_snmp_branch(branch_name='lldpRemSysName', parser=self._parse_mibs_lldp)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-System-Name' (lldpRemSysName)")
                return False
            retval = self.get_snmp_branch(branch_name='lldpRemSysDesc', parser=self._parse_mibs_lldp)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-System-Decription' (lldpRemSysDesc)")
                return False
            # get the enabled remote device capabilities
            retval = self.get_snmp_branch(branch_name='lldpRemSysCapEnabled', parser=self._parse_mibs_lldp)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-System-Capabilities' (lldpRemSysCapEnabled)")
                return False
            # and info about the remote chassis:
            retval = self.get_snmp_branch(branch_name='lldpRemChassisIdSubtype', parser=self._parse_mibs_lldp)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-Chassis-Type' (lldpRemChassisIdSubtype)")
                return False
            retval = self.get_snmp_branch(branch_name='lldpRemChassisId', parser=self._parse_mibs_lldp)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-Chassis-Id' (lldpRemChassisId)")
                return False
            # remote management info:
            retval = self.get_snmp_branch(branch_name='lldpRemManAddrEntry', parser=self._parse_mibs_lldp_management)
            if retval < 0:
                self.add_warning("Error getting 'LLDP-Remote-Management-Info' (lldpRemManAddrEntry)")
                return False
        return True

    def _get_lacp_data(self) -> bool:
        """
        Read the IEEE LACP mib, single mib counter gives us enough to identify
        the physical interfaces that are an LACP member.
        Returns True on success, False on failure
        """

        # Get the admin key or "index" for aggregate interfaces
        retval = self.get_snmp_branch(branch_name='dot3adAggActorAdminKey', parser=self._parse_mibs_lacp)
        if retval < 0:
            self.add_warning("Error getting 'LACP-Aggregate-Admin-Key' (dot3adAggActorAdminKey)")
            return False

        # If there are aggregate interfaces, then get the admin key or "index" for physical member interfaces
        # this maps back to the logical or actor aggregates above in dot3adAggActorAdminKey
        if retval > 0:
            retval = self.get_snmp_branch(branch_name='dot3adAggPortActorAdminKey', parser=self._parse_mibs_lacp)
            if retval < 0:
                self.add_warning("Error getting 'LACP-Port-Admin-Key' (dot3adAggPortActorAdminKey)")
                return False

        """
        # this is a shortcut to find aggregates and members all in one, but does not work for every device.
        retval = self.get_snmp_branch(branch_name='dot3adAggPortAttachedAggID', parser=self._parse_mibs_lacp)
        if retval < 0:
            self.add_warning("Error getting 'LACP-Port-AttachedAggID' (dot3adAggPortAttachedAggID)")
            return False
        """

        return True

    def _get_syslog_msgs(self):
        """
        Read the SYSLOG-MSG-MIB: note this is meant for notifications, but we can read log size!
        Returns True on success, False on failure
        """
        retval = self.get_snmp_branch(branch_name='syslogMsgTableMaxSize', parser=self._parse_mibs_syslog_msg)
        if retval < 0:
            self.add_warning("Error getting Log Size Info (syslogMsgTableMaxSize)")

    def get_my_vrfs(self):
        """Read the VRFs defined on this device.
            This reads 'mplsL3VpnVrfEntry' items from the 'mplsL3VpnVrfTable'
            defined in the standard MPLS-L3VPN-STD-MIB

        Args:
            none

        Returns:
            (bool): True on success, False on failure
        """
        dprint("SnmpConnector.get_my_vrfs()")
        retval = self.get_snmp_branch(branch_name='mplsL3VpnVrfEntry', parser=self._parse_mib_mpls_l3vpn)
        if retval < 0:
            self.add_warning("Error getting VRF info from the MPLS-L2VPN tables (mplsL3VpnVrfEntry)")

        # if we have found VRF's, let's see if we can find Interface membership:
        if self.vrfs:
            retval = self.get_snmp_branch(
                branch_name='mplsL3VpnIfVpnClassification', parser=self._parse_mib_mpls_vrf_members
            )
            if retval < 0:
                # try another entry in case the device does not implement mplsL3VpnIfVpnClassification:
                retval = self.get_snmp_branch(
                    branch_name='mplsL3VpnIfVpnRouteDistProtocol', parser=self._parse_mib_mpls_vrf_members
                )

        return True

    def _parse_mib_mpls_l3vpn(self, oid: str, val: str) -> bool:
        """
        Parse standard VRF mib entries from MPLS-L3VPN-STD-MIB. This gets added to self.vrfs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"SnmpConnector._parse_vrf_entries() {str(oid)}")

        # VRF name
        sub_oid = oid_in_branch(mplsL3VpnVrfName, oid)
        if sub_oid:
            vrf_name = self._get_string_from_oid_index(oid_index=sub_oid)
            dprint(f"  VRF NAME = '{vrf_name}'")
            vrf = self.get_vrf_by_name(name=vrf_name)
            return True

        # VRF description
        sub_oid = oid_in_branch(mplsL3VpnVrfDescription, oid)
        if sub_oid:
            vrf_name = self._get_string_from_oid_index(oid_index=sub_oid)
            dprint(f"  VRF DESCR for '{vrf_name}'")
            vrf = self.get_vrf_by_name(name=vrf_name)
            vrf.description = val
            return True

        # the VRF RD:
        sub_oid = oid_in_branch(mplsL3VpnVrfRD, oid)
        if sub_oid:
            vrf_name = self._get_string_from_oid_index(oid_index=sub_oid)
            dprint(f"  VRF RD for '{vrf_name}'")
            vrf = self.get_vrf_by_name(name=vrf_name)
            vrf.rd = val
            return True

        # state is enabled or disabled
        sub_oid = oid_in_branch(mplsL3VpnVrfOperStatus, oid)
        if sub_oid:
            vrf_name = self._get_string_from_oid_index(oid_index=sub_oid)
            dprint(f"  VRF State for'{vrf_name}'")
            vrf = self.get_vrf_by_name(name=vrf_name)
            # set the state, active=True
            if int(val) == MPLS_VRF_STATE_ENABLED:
                vrf.state = True
            else:
                vrf.state = False
            return True

        # number of active interfaces in this VRF
        sub_oid = oid_in_branch(mplsL3VpnVrfActiveInterfaces, oid)
        if sub_oid:
            vrf_name = self._get_string_from_oid_index(oid_index=sub_oid)
            dprint(f"  VRF Active count for'{vrf_name}'")
            vrf = self.get_vrf_by_name(name=vrf_name)
            vrf.active_interfaces = int(val)
            return True

        # we did not parse:
        return False

    def _parse_mib_mpls_vrf_members(self, oid: str, val: str) -> bool:
        """
        Parse standard VRF interface membership entries from MPLS-L3VPN-STD-MIB.
        This gets added to Interface().vrfs

        Params:
            oid (str): the SNMP OID to parse
            val (str): the value of the SNMP OID we are parsing

        Returns:
            (boolean): True if we parse the OID, False if not.
        """
        dprint(f"SnmpConnector._parse_mib_mpls_vrf_members() {str(oid)}")

        # find ifIndex entries that are part of a VRF.
        sub_oid = oid_in_branch(mplsL3VpnIfVpnClassification, oid)
        if sub_oid:
            # sub-oid is <vrf-name-as-oid-encoded>.<if_index>
            # for now we dont care about "val"
            # we cheat, we know last number is ifIndex:
            ifIndex = sub_oid.split('.')[-1]
            vrf_name = self._get_string_from_oid_index(oid_index=sub_oid)
            dprint(f"  mplsL3VpnIfVpnClassification: vrf '{vrf_name}' interface index {ifIndex} = {val}")
            iface = self.get_interface_by_key(key=str(ifIndex))
            if iface:
                dprint(f"    interface '{iface.name}'")
                # add to the list of interfaces for this vrf
                if iface.name not in self.vrfs[vrf_name].interfaces:
                    self.vrfs[vrf_name].interfaces.append(iface.name)
                # assing this vrf name to the interface:
                iface.vrf_name = vrf_name
                # see if this is a routed "vlan-interface" to assign VRF to vlan
                vlan_id = get_vlan_id_from_l3_interface(iface)
                if vlan_id > 0:
                    dprint("    Vlan ID {vlan_id} is part of vrf '{vrf_name}'")
                    vlan = self.get_vlan_by_id(vlan_id=vlan_id)
                    vlan.vrf = vrf_name
            return True

        sub_oid = oid_in_branch(mplsL3VpnIfVpnRouteDistProtocol, oid)
        if sub_oid:
            # sub-oid is <vrf-name-as-oid-encoded>.<if_index>
            # for now we dont care about "val"
            # we cheat, we know last number is ifIndex:
            ifIndex = sub_oid.split('.')[-1]
            vrf_name = self._get_string_from_oid_index(oid_index=sub_oid)
            dprint(f"  mplsL3VpnIfVpnRouteDistProtocol: vrf '{vrf_name}' interface index {ifIndex} = {val}")
            iface = self.get_interface_by_key(key=str(ifIndex))
            if iface:
                dprint(f"    interface '{iface.name}'")
                # add to the list of interfaces for this vrf
                if iface.name not in self.vrfs[vrf_name].interfaces:
                    self.vrfs[vrf_name].interfaces[iface.name] = True
                # assing this vrf name to the interface:
                iface.vrf_name = vrf_name
                # see if this is a routed "vlan-interface" to assign VRF to vlan
                vlan_id = get_vlan_id_from_l3_interface(iface)
                if vlan_id > 0:
                    dprint("    Vlan ID {vlan_id} is part of vrf '{vrf_name}'")
                    vlan = self.get_vlan_by_id(vlan_id=vlan_id)
                    vlan.vrf = vrf_name
            return True

        # we did not parse:
        return False

    def _get_string_from_oid_index(self, oid_index: str) -> str:
        """Get the "string name as index" from a MIB table element.
        This is used as 'index' for a number of MIB table entries.
        First digit is length, the rest the ascii representation of the name.
        eg. "4.78.97.109.101", is the 4-character string "Name" (N=78, a=97, m=109, e=101)

        Note: there are instances where this 'oid string' is followed by more oid numbers
        (e.g. in Vrf Interface membership) so we check the length,
        and break out when that number of chracters is found!

        Args:
            oid_index (str): represents the "oid index" to decode.

        Returns:
            (str): value of the decoded string, or ""
        """
        dprint(f"_get_string_from_oid_index('{oid_index}')")
        value = ""
        try:
            chars = oid_index.split(".")
            length = int(chars.pop(0))  # remove length entry
            dprint(f"  String size: {length}")
            for char in chars:
                value += chr(int(char))  # add the character represented by the ascii number.
                if len(value) == length:
                    dprint(f"  Max size found, string = '{value}'")
                    break
        except Exception as err:
            self.add_log(
                description=f"Error decoding string for oid index '{oid_index}': {err}",
                action=LOG_SNMP_ERROR,
                type=LOG_TYPE_ERROR,
            )
            value = ""  # reset to default, just in case
        return value

    #
    # "Public" interface methods
    #

    """
    Class specific functions
    """

    # Duplicates of connect.connector.Connector() base function:
    # def get_switch_vlans(self) -> dict:
    #     """
    #     Return the vlans defined on this switch
    #     """
    #     return self.vlans
    #
    # def get_vlan_by_id(self, vlan_id: int) -> Vlan:
    #     """
    #     Return the Vlan() object for the given id
    #     """
    #     vlan_id = int(vlan_id)
    #     if vlan_id in self.vlans.keys():
    #         return self.vlans[vlan_id]
    #     return False

    def set_interface_admin_status(self, interface: Interface, new_state: bool) -> bool:
        """
        Set the interface to the requested state (up or down)

        Args:
            interface = Interface() object for the requested port
            new_state = True / False  (enabled/disabled)

        Returns:
            return True on success, False on error and set self.error variables

        """
        if not interface:
            self.error = Error(status=True, description="set_interface_admin_status(): Invalid interface (not set)!")
            return False

        # make sure we cast the proper type here! Ie this needs an Integer()
        status_int = IF_OPER_STATUS_UP if new_state else IF_OPER_STATUS_DOWN
        if self.set(
            oid=f"{ifAdminStatus}.{interface.index}", value=status_int, snmp_type='i', parser=self._parse_mibs_if_table
        ):
            super().set_interface_admin_status(interface=interface, new_state=new_state)
            return True
        return False

    def set_interface_poe_status(self, interface: Interface, new_state: int) -> bool:
        """
        Set the interface Power-over-Ethernet state as given

        Args:
            interface = Interface() object for the requested port
            new_state = POE_PORT_ADMIN_ENABLED or POE_PORT_ADMIN_DISABLED

        Returns:
            return True on success, False on error and set self.error variables
        """
        if not interface:
            self.error = Error(status=True, description="set_interface_poe_status(): Invalid interface (not set)!")
            return False
        # the PoE index is kept in the iface.poe_entry
        if not interface.poe_entry:
            self.error = Error(status=True, description="set_interface_poe_status(): interface has no poe_entry!")
            return False
        # proper status value?
        if new_state != POE_PORT_ADMIN_ENABLED and new_state != POE_PORT_ADMIN_DISABLED:
            self.error = Error(status=True, description=f"set_interface_poe_status(): Invalid status: {new_state}")
            return False

        # make sure we cast the proper type here! Ie this needs an Integer()
        if self.set(
            oid=f"{pethPsePortAdminEnable}.{interface.poe_entry.index}",
            value=new_state,
            snmp_type='i',
            parser=self._parse_mibs_poe_port,
        ):
            super().set_interface_poe_status(interface=interface, new_state=new_state)
            return True
        return False

    def set_interface_description(self, interface: Interface, description: str) -> bool:
        """
        Set a description on an interface.
        return True on success, False on error and set self.error variables
        """
        if not interface:
            self.error = Error(status=True, description="set_interface_description(): Invalid interface (not set)!")
            return False

        # make sure we cast the proper type here! I.e. this needs an string
        if self.set(
            oid=f"{ifAlias}.{interface.index}",
            value=description,
            snmp_type='OCTETSTRING',
            parser=self._parse_mibs_if_x_table,
        ):
            super().set_interface_description(interface=interface, description=description)
            return True
        return False

    def set_interface_untagged_vlan(self, interface: Interface, new_vlan_id: int) -> bool:
        """
        Change the VLAN via the Q-BRIDGE MIB (ie generic)
        return True on success, False on error and set self.error variables
        """
        dprint(f"SnmpConnector.set_interface_untagged_vlan(interface={interface.name}, vlan={new_vlan_id})")
        if not interface:
            dprint("  Invalid interface!, returning False")
            return False
        # now check the Q-Bridge PortID
        if interface.port_id < 0:
            dprint(f"  Invalid interface.port_id ({interface.port_id}), returning False")
            return False
        dprint("   valid interface and port_id")
        old_vlan_id = interface.untagged_vlan
        # set this switch port on the new vlan:
        # Q-BIRDGE mib: VlanIndex = Unsigned32
        dprint("Setting NEW VLAN on port")
        if not self.set(
            oid=f"{dot1qPvid}.{interface.port_id}",
            value=int(new_vlan_id),
            snmp_type='u',
            parser=self._parse_mibs_vlan_related,
        ):
            return False

        # some switches need a little "settling time" here (value is in seconds)
        time.sleep(0.5)

        # should this be using "dot1qVlanCurrentEgressPorts" ?
        #        old_vlan_portlist = PortList()
        #        old_vlan_portlist.from_unicode(snmpval.value)
        #        dprint(f"OLD VLAN Static Egress Ports = {old_vlan_portlist.to_hex_string()}")
        #
        #        # dot1qVlanCurrentEgressPorts Read-Only field! .0. is timestamp.
        #        (error_status, snmpval) = self.get(f"{dot1qVlanCurrentEgressPorts}.0.{old_vlan_id}")

        # Remove port from list of ports on old vlan,
        # i.e. read current Egress PortList bitmap first:
        dprint(f"Reading egress ports:")
        (error_status, snmpval) = self.get(
            f"{dot1qVlanStaticEgressPorts}.{old_vlan_id}", parser=self._parse_mibs_vlan_related
        )
        if error_status:
            # Hmm, not sure what to do
            dprint("  ERROR: reading egress ports!")
            return False

        # now calculate new bitmap by removing this switch port
        old_vlan_portlist = PortList()
        old_vlan_portlist.from_unicode(snmpval.value)
        dprint(f"OLD VLAN Current Egress Ports = {old_vlan_portlist.to_hex_string()}")

        # unset bit for port, i.e. remove from active portlist on vlan:
        old_vlan_portlist[interface.port_id] = 0

        dprint(
            f"Updating OLD VLAN Current Egress Ports with removed port {interface.port_id}, now  = {old_vlan_portlist.to_hex_string()}"
        )

        # now send update to switch:
        # use PySNMP to do this work:
        octet_string = OctetString(hexValue=old_vlan_portlist.to_hex_string())
        try:
            pysnmp = pysnmpHelper(self.switch)
        except Exception as err:
            self.error.status = True
            self.error.description = "Error getting snmp connection object (pysnmpHelper())"
            self.error.details = f"Caught Error: {repr(err)} ({str(type(err))})\n{traceback.format_exc()}"
            dprint("SnmpConnector.set_interface_untagged_vlan() -> False from pysnmpHelper()")
            return False
        if not pysnmp.set(f"{dot1qVlanStaticEgressPorts}.{old_vlan_id}", octet_string):
            self.error.status = True
            self.error.description += "\nError in setting port (dot1qVlanStaticEgressPorts)"
            # copy over the error details from the call:
            self.error.details = pysnmp.error.details
            dprint("SnmpConnector.set_interface_untagged_vlan() -> False from pysnmp.set(dot1qVlanStaticEgressPorts)")
            return False

        # and re-read the dot1qVlanCurrentEgressPorts, all ports
        # tagged/untagged on the old and new vlan
        # note the 0 to hopefully deactivate time filter!
        dprint("Get OLD VLAN Current Egress Ports")
        (error_status, snmpval) = self.get(
            f"{dot1qVlanCurrentEgressPorts}.0.{old_vlan_id}", parser=self._parse_mibs_vlan_related
        )
        dprint("Get NEW VLAN Current Egress Ports")
        (error_status, snmpval) = self.get(
            f"{dot1qVlanCurrentEgressPorts}.0.{new_vlan_id}", parser=self._parse_mibs_vlan_related
        )
        interface.untagged_vlan = new_vlan_id
        dprint("SnmpConnector.set_interface_untagged_vlan() -> True")
        return True

    def vlan_create(self, vlan_id: int, vlan_name: str) -> bool:
        '''
        Create a new vlan on this device. Upon success, this then needs to call the base class for book keeping!

        Note: this uses SNMP dot1qVlanStaticRowStatus set to createAndGo(4). This should work on most devices
        that implement the Q-Bridge MIB. However, some devices may need to set createAndWait(5). If your device
        needs a different sequency, please override this function in your device driver!

        Args:
            vlan_id (int): the vlan id
            vlan_name (str): the name of the vlan

        Returns:
            True on success, False on error and set self.error variables.
        '''

        # this is atomic multi-set action. Full tuples with (OID, value, type) calling ezsnmp:
        oid1 = (f"{dot1qVlanStaticRowStatus}.{vlan_id}", vlan_createAndGo, 'i')
        oid2 = (f"{dot1qVlanStaticName}.{vlan_id}", vlan_name, 's')
        if not self.set_multiple(oid_values=[oid1, oid2]):
            # we leave self.error.details as is!
            return False
        # all OK, now do the book keeping
        Connector.vlan_create(self=self, vlan_id=vlan_id, vlan_name=vlan_name)
        return True

    def vlan_edit(self, vlan_id: int, vlan_name: str) -> bool:
        '''
        Edit the vlan name. Upon success, this then needs to call the base class for book keeping!

        Args:
            vlan_id (int): the vlan id to edit
            vlan_name (str): the new name of the vlan

        Returns:
            True on success, False on error and set self.error variables.
        '''

        # this is atomic multi-set action. Full tuples with (OID, value, type) calling ezsnmp:
        oid1 = (f"{dot1qVlanStaticName}.{vlan_id}", vlan_name, 's')
        if not self.set_multiple(oid_values=[oid1]):
            # we leave self.error.details as is!
            return False
        # all OK, now do the book keeping
        Connector.vlan_edit(self=self, vlan_id=vlan_id, vlan_name=vlan_name)
        return True

    def vlan_delete(self, vlan_id: int) -> bool:
        '''
        Deletel the vlan. Upon success, this then needs to call the base class for book keeping!

        Args:
            vlan_id (int): the vlan id to edit

        Returns:
            True on success, False on error and set self.error variables.
        '''

        # this is atomic multi-set action. Full tuples with (OID, value, type) calling ezsnmp:
        oid1 = (f"{dot1qVlanStaticRowStatus}.{vlan_id}", vlan_destroy, 'i')
        if not self.set_multiple(oid_values=[oid1]):
            # we leave self.error.details as is!
            return False
        # all OK, now do the book keeping
        Connector.vlan_delete(self=self, vlan_id=vlan_id)
        return True


# --- End of SnmpConnector() ---


class SnmpProbeConnector(SnmpConnector):
    """
    This class implements a SNMP Probing connector.
    Here we can implement whatever specifics we need to probe devices to find out what vendor/type they are.
    """

    def get_system_oid(self) -> str:
        """Read the SNMP System OID object. Return as string.

        Return:
            (str): string representing the SNMP system OID

        Exceptions:
            If we cannot read the OID, throw generic exception.
        """
        dprint("get_system_oid()")
        (error_status, retval) = self.get(oid=sysObjectID, parser=self._parse_mibs_system)
        if error_status:
            self.add_log(description=self.error.details, type=LOG_TYPE_ERROR, action=LOG_SNMP_ERROR)
            raise Exception(f"Error getting System OID: {self.error.details}")
        dprint(f"  System OID={retval.value}")
        return retval.value


# --- End of SnmpProbeConnector() --


def oid_in_branch(mib_branch: str, oid: str) -> bool | str:
    """
    Check if a given OID is in the branch, if so, return the 'ending' portion after the mib_branch
    E.g. in many cases, the oid end is the 'ifIndex' or vlan_id, or such.
    mib_branch should contain starting DOT (ezsnmp returns the OID with starting dot), but NOT trailing dot !!!
    """
    # dprint(f"oid_in_branch() checking branch {mib_branch}, oid = {oid}")
    if not isinstance(oid, str):
        dprint("Error: oid not string value")
        return False
    mib_branch += "."  # make sure the OID branch terminates with a . for the next series of data
    oid_len = len(oid)
    branch_len = len(mib_branch)
    if oid_len > branch_len and oid[:branch_len] == mib_branch:  # need to check for trailing .
        return oid[branch_len:]  # get data past the "root" oid + the period (+1)
    return False


def get_switch_enterprise_info(system_oid: str) -> str:
    """
    Return the Enterprise name from the Object ID given
    """
    sub_oid = oid_in_branch(enterprises, system_oid)
    if sub_oid:
        parts = sub_oid.split('.', 1)  # 1 means one split, two elements!
        enterprise_id = int(parts[0])
        # here we go:
        if enterprise_id in enterprise_id_info.keys():
            return enterprise_id_info[enterprise_id]
        else:
            return f"Unknown ({enterprise_id})"
    else:
        # sub oid, ie enterprise data, not found!
        return 'Not found'
