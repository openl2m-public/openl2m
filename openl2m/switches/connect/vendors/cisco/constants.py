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

from switches.connect.constants import snmp_mib_variables
from switches.connect.vendors.constants import enterprise_id_info

# Cisco specific constants
ENTERPRISE_ID_CISCO = 9
enterprise_id_info[ENTERPRISE_ID_CISCO] = 'Cisco'

# most Cisco switches support this:
# http://www.circitor.fr/Mibs/Html/C/CISCO-CONFIG-MAN-MIB.php
ciscoConfigManMIBObjects = '.1.3.6.1.4.1.9.9.43.1'
snmp_mib_variables['ciscoConfigManMIBObjects'] = ciscoConfigManMIBObjects

ccmHistory = '.1.3.6.1.4.1.9.9.43.1.1'
snmp_mib_variables['ccmHistory'] = ccmHistory

# these values are the value of sysUpTime for the event, i.e. ticks in 1/100th of a second:
ccmHistoryRunningLastChanged = '.1.3.6.1.4.1.9.9.43.1.1.1'
snmp_mib_variables['ccmHistoryRunningLastChanged'] = ccmHistoryRunningLastChanged

ccmHistoryRunningLastSaved = '.1.3.6.1.4.1.9.9.43.1.1.2'
snmp_mib_variables['ccmHistoryRunningLastSaved'] = ccmHistoryRunningLastSaved

ccmHistoryStartupLastChanged = '.1.3.6.1.4.1.9.9.43.1.1.3'
snmp_mib_variables['ccmHistoryStartupLastChanged'] = ccmHistoryStartupLastChanged


# VTP MIB:
vtpVlanState = '.1.3.6.1.4.1.9.9.46.1.3.1.1.2.1'
snmp_mib_variables['vtpVlanState'] = vtpVlanState

vtpVlanType = '.1.3.6.1.4.1.9.9.46.1.3.1.1.3.1'
snmp_mib_variables['vtpVlanType'] = vtpVlanType

VLAN_TYPE_NORMAL = 1     # regular(1)
VLAN_TYPE_FDDI = 2       # fddi(2)
VLAN_TYPE_TOKENRING = 3  # tokenRing(3)
VLAN_TYPE_FDDINET = 4    # fddiNet(4)
VLAN_TYPE_TRNET = 5      # trNet(5)

vtpVlanName = '.1.3.6.1.4.1.9.9.46.1.3.1.1.4.1'
snmp_mib_variables['vtpVlanName'] = vtpVlanName
# VTP trunk ports start at .1.3.6.1.4.1.9.9.46.1.6
# details about ports start at .1.3.6.1.4.1.9.9.46.1.6.1.1

vlanTrunkPortNativeVlan = '.1.3.6.1.4.1.9.9.46.1.6.1.1.5'
snmp_mib_variables['vlanTrunkPortNativeVlan'] = vlanTrunkPortNativeVlan

vlanTrunkPortDynamicState = '.1.3.6.1.4.1.9.9.46.1.6.1.1.13'
snmp_mib_variables['vlanTrunkPortDynamicState'] = vlanTrunkPortDynamicState
VTP_TRUNK_STATE_ON = 1
VTP_TRUNK_STATE_OFF = 2
VTP_TRUNK_STATE_DESIRED = 3
VTP_TRUNK_STATE_AUTO = 4
VTP_TRUNK_STATE_NO_NEGOTIATE = 5

# actual trunk status, result of the vlanTrunkPortDynamicState and the ifOperStatus of the trunk port itself
# ie when port is down, this shows DISABLED!!!
vlanTrunkPortDynamicStatus = '.1.3.6.1.4.1.9.9.46.1.6.1.1.14'
snmp_mib_variables['vlanTrunkPortDynamicStatus'] = vlanTrunkPortDynamicStatus
VTP_PORT_TRUNK_ENABLED = 1
VTP_PORT_TRUNK_DISABLED = 2

# this is the untagged or native vlan for a Cisco switch port
# this will NOT show ports in trunk mode!!!
vmVlan = '.1.3.6.1.4.1.9.9.68.1.2.2.1.2'
snmp_mib_variables['vmVlan'] = vmVlan

# this is the Cisco "Voice" Vlan
vmVoiceVlanId = '.1.3.6.1.4.1.9.9.68.1.5.1.1.1'
snmp_mib_variables['vmVoiceVlanId'] = vmVoiceVlanId


# Cisco L2L3 Interface Config Mib
# http://www.circitor.fr/Mibs/Html/C/CISCO-L2L3-INTERFACE-CONFIG-MIB.php

cL2L3IfModeOper = '.1.3.6.1.4.1.9.9.151.1.1.1.1.2'
snmp_mib_variables['cL2L3IfModeOper'] = cL2L3IfModeOper
# routed(1), switchport(2)
CISCO_ROUTE_MODE = 1
CISCO_BRIDGE_MODE = 2

#
# Cisco new Extended POE mib
#
ciscoPowerEthernetExtMIB = '.1.3.6.1.4.1.9.9.402'
snmp_mib_variables['ciscoPowerEthernetExtMIB'] = ciscoPowerEthernetExtMIB

cpeExtPsePortPwrAllocated = '.1.3.6.1.4.1.9.9.402.1.2.1.7'
snmp_mib_variables['cpeExtPsePortPwrAllocated'] = cpeExtPsePortPwrAllocated

cpeExtPsePortPwrAvailable = '.1.3.6.1.4.1.9.9.402.1.2.1.8'
snmp_mib_variables['cpeExtPsePortPwrAvailable'] = cpeExtPsePortPwrAvailable

cpeExtPsePortPwrConsumption = '.1.3.6.1.4.1.9.9.402.1.2.1.9'
snmp_mib_variables['cpeExtPsePortPwrConsumption'] = cpeExtPsePortPwrConsumption

cpeExtPsePortMaxPwrDrawn = '.1.3.6.1.4.1.9.9.402.1.2.1.10'
snmp_mib_variables['cpeExtPsePortMaxPwrDrawn'] = cpeExtPsePortMaxPwrDrawn

# CISCO-STACK-MIB contains various mappings
ciscoStackMIB = '.1.3.6.1.4.1.9.5.1'
snmp_mib_variables['ciscoStackMIB'] = ciscoStackMIB
# this maps a Cisco port # to a standard if_index:
portIfIndex = '.1.3.6.1.4.1.9.5.1.4.1.1.11'
snmp_mib_variables['portIfIndex'] = portIfIndex


# OID to "write mem" via Snmp
ciscoWriteMem = '.1.3.6.1.4.1.9.2.1.54.0'
snmp_mib_variables['ciscoWriteMem'] = ciscoWriteMem
