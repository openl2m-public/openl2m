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

# HPE/ComWare
ENTERPRISE_ID_H3C = 25506
enterprise_id_info[ENTERPRISE_ID_H3C] = 'HPE/Comware'

# HH3C Configuration Mib
hh3cConfig = '.1.3.6.1.4.1.25506.2.4'

hh3cCfgLog = '.1.3.6.1.4.1.25506.2.4.1.1'
snmp_mib_variables['hh3cCfgLog'] = hh3cCfgLog

hh3cCfgRunModifiedLast = '.1.3.6.1.4.1.25506.2.4.1.1.1'
hh3cCfgRunSavedLast = '.1.3.6.1.4.1.25506.2.4.1.1.2'
hh3cCfgStartModifiedLast = '.1.3.6.1.4.1.25506.2.4.1.1.3'

hh3cCfgOperateType = '.1.3.6.1.4.1.25506.2.4.1.2.4.1.2'
snmp_mib_variables['hh3cCfgOperateType'] = hh3cCfgOperateType
HH3C_running2Startup = 1

hh3cCfgOperateRowStatus = '.1.3.6.1.4.1.25506.2.4.1.2.4.1.9'
snmp_mib_variables['hh3cCfgOperateRowStatus'] = hh3cCfgOperateRowStatus
HH3C_createAndGo = 4

# HH3C PoE
# see http://www.circitor.fr/Mibs/Html/H/HH3C-POWER-ETH-EXT-MIB.php

hh3cPowerEthernetExt = '.1.3.6.1.4.1.25506.2.14'

# The object specifies the power currently being consumed by the port.
# It is a read only integer value with units of milliWatts.
hh3cPsePortCurrentPower = '.1.3.6.1.4.1.25506.2.14.1.1.5'
snmp_mib_variables['hh3cPsePortCurrentPower'] = hh3cPsePortCurrentPower

# HH3C LswINF MIB - interface related
# See http://www.circitor.fr/Mibs/Html/H/HH3C-LswINF-MIB.php

# hh3cifAggregatePort
hh3cifAggregatePort = '.1.3.6.1.4.1.25506.8.35.1.1.1.3'  # + ifIndex = True if aggregate port
snmp_mib_variables['hh3cifAggregatePort'] = hh3cifAggregatePort  # + ifIndex = True if aggregate port

# HH3C LswVLAN MIB - VLAN related
# See http://www.circitor.fr/Mibs/Html/H/HH3C-LswVLAN-MIB.php
# and the raw text at http://www.circitor.fr/Mibs/Mib/H/HH3C-LswVLAN-MIB.mib
# This is the H3C VLan mib, similar to Q-Bridge mib.

hh3cdot1qVlanName = '.1.3.6.1.4.1.25506.8.35.2.1.1.1.2'
snmp_mib_variables['hh3cdot1qVlanName'] = hh3cdot1qVlanName
#
# This is the OID to write to for UNTAGGED, "mode access" ports!
hh3cdot1qVlanPorts = '.1.3.6.1.4.1.25506.8.35.2.1.1.1.3'  # + .vlanId = PortList (bitmap)
snmp_mib_variables['hh3cdot1qVlanPorts'] = hh3cdot1qVlanPorts  # + .vlanId = PortList (bitmap)

# READ-ONLY "Tagged port list of the VLAN."
hh3cdot1qVlanTaggedPorts = '.1.3.6.1.4.1.25506.8.35.2.1.1.1.17'  # PortList, read-only!
snmp_mib_variables['hh3cdot1qVlanTaggedPorts'] = hh3cdot1qVlanTaggedPorts   # PortList, read-only!

# READ-ONLY "Untagged port list of the VLAN."
hh3cdot1qVlanUntaggedPorts = '.1.3.6.1.4.1.25506.8.35.2.1.1.1.18'   # PortList, read-only!
snmp_mib_variables['hh3cdot1qVlanUntaggedPorts'] = hh3cdot1qVlanUntaggedPorts   # PortList, read-only!

# This is the WRITE variable for VLAN tagged ports:
BYTES_FOR_2048_VLANS = 256  # 2048 vlans / 8 bits-per-byte
# hh3cifVLANTrunkAllowListLow and High, NOTE: BITMAP of VLANS!!!
# on a port in "trunk mode"  (i.e. not bitmap of ports as in Q-Bridge!)
hh3cifVLANTrunkAllowListLow = '.1.3.6.1.4.1.25506.8.35.5.1.3.1.6'  # + portId = VlanBitMap for vlan 1 - 2048
snmp_mib_variables['hh3cifVLANTrunkAllowListLow'] = hh3cifVLANTrunkAllowListLow  # + portId = VlanBitMap for vlan 1 - 2048

hh3cifVLANTrunkAllowListHigh = '.1.3.6.1.4.1.25506.8.35.5.1.3.1.7'  # + portId = VlanBitMap for vlan 2049 - 4096
snmp_mib_variables['hh3cifVLANTrunkAllowListHigh'] = hh3cifVLANTrunkAllowListHigh   # + portId = VlanBitMap for vlan 2049 - 4096
