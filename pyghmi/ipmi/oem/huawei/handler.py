# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2015-2016 Lenovo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import binascii
import traceback
import urllib

import pyghmi.constants as pygconst
import pyghmi.exceptions as pygexc
import pyghmi.ipmi.oem.generic as generic
import pyghmi.ipmi.private.constants as ipmiconst
import pyghmi.ipmi.private.util as util

from pyghmi.ipmi.oem.huawei import cpu
from pyghmi.ipmi.oem.huawei import dimm
from pyghmi.ipmi.oem.huawei import drive

from pyghmi.ipmi.oem.huawei import firmware
from pyghmi.ipmi.oem.huawei import imm
from pyghmi.ipmi.oem.huawei import inventory
from pyghmi.ipmi.oem.huawei import nextscale
from pyghmi.ipmi.oem.huawei import pci
from pyghmi.ipmi.oem.huawei import psu
from pyghmi.ipmi.oem.huawei import raid_controller
from pyghmi.ipmi.oem.huawei import raid_drive
from pyghmi.ipmi.oem.huawei import energy
from pyghmi.ipmi.oem.huawei.snmp import oid

import pyghmi.util.webclient as wc

import math
import socket
import struct
import weakref
try:
    range = xrange
except NameError:
    pass
try:
    buffer
except NameError:
    buffer = memoryview

inventory.register_inventory_category(cpu)
inventory.register_inventory_category(dimm)
inventory.register_inventory_category(pci)
inventory.register_inventory_category(drive)
inventory.register_inventory_category(psu)
inventory.register_inventory_category(raid_drive)
inventory.register_inventory_category(raid_controller)


firmware_types = {
    1: 'Management Controller',
    2: 'UEFI/BIOS',
    3: 'CPLD',
    4: 'Power Supply',
    5: 'Storage Adapter',
    6: 'Add-in Adapter',
}

firmware_event = {
    0: ('Update failed', pygconst.Health.Failed),
    1: ('Update succeeded', pygconst.Health.Ok),
    2: ('Update aborted', pygconst.Health.Ok),
    3: ('Unknown', pygconst.Health.Warning),
}

me_status = {
    0: ('Recovery GPIO forced', pygconst.Health.Warning),
    1: ('ME Image corrupt', pygconst.Health.Critical),
    2: ('Flash erase error', pygconst.Health.Critical),
    3: ('Unspecified flash state', pygconst.Health.Warning),
    4: ('ME watchdog timeout', pygconst.Health.Critical),
    5: ('ME platform reboot', pygconst.Health.Critical),
    6: ('ME update', pygconst.Health.Ok),
    7: ('Manufacturing error', pygconst.Health.Critical),
    8: ('ME Flash storage integrity error', pygconst.Health.Critical),
    9: ('ME firmware exception', pygconst.Health.Critical),  # event data 3..
    0xa: ('ME firmware worn', pygconst.Health.Warning),
    0xc: ('Invalid SCMP state', pygconst.Health.Warning),
    0xd: ('PECI over DMI failure', pygconst.Health.Warning),
    0xe: ('MCTP interface failure', pygconst.Health.Warning),
    0xf: ('Auto configuration completed', pygconst.Health.Ok),
}

me_flash_status = {
    0: ('ME flash corrupted', pygconst.Health.Critical),
    1: ('ME flash erase limit reached', pygconst.Health.Critical),
    2: ('ME flash write limit reached', pygconst.Health.Critical),
    3: ('ME flash write enabled', pygconst.Health.Ok),
}

leds = {
    "BMC_UID": 0x00,
    "BMC_HEARTBEAT": 0x01,
    "SYSTEM_FAULT": 0x02,
    "PSU1_FAULT": 0x03,
    "PSU2_FAULT": 0x04,
    "LED_FAN_FAULT_1": 0x10,
    "LED_FAN_FAULT_2": 0x11,
    "LED_FAN_FAULT_3": 0x12,
    "LED_FAN_FAULT_4": 0x13,
    "LED_FAN_FAULT_5": 0x14,
    "LED_FAN_FAULT_6": 0x15,
    "LED_FAN_FAULT_7": 0x16,
    "LED_FAN_FAULT_8": 0x17
}

ami_leds = {
    "BMC_HEARTBEAT": 0x00,
    "BMC_UID": 0x01,
    "SYSTEM_FAULT": 0x02,
    "HDD_FAULT": 0x03
}


asrock_leds = {
    "SYSTEM_EVENT": 0x00,
    "BMC_UID": 0x01,
    "LED_FAN_FAULT_1": 0x02,
    "LED_FAN_FAULT_2": 0x03,
    "LED_FAN_FAULT_3": 0x04
}

ts460_leds = {
    "SYSTEM_EVENT": 0x00,
    "BMC_UID": 0x01,
    "LED_FAN_FAULT_1": 0x02,
    "LED_FAN_FAULT_2": 0x03,
    "LED_FAN_CPU": 0x04,
    "LED_FAN_REAR": 0x05
}

led_status = {
    0x00: "Off",
    0xFF: "On"
}

ami_led_status = {
    0x00: "Off",
    0x01: "On"
}

asrock_led_status = {
    0x00: "Off",
    0x01: "On"
}

led_status_default = "Blink"
mac_format = '{0:02x}:{1:02x}:{2:02x}:{3:02x}:{4:02x}:{5:02x}'

ris_media_types = {
    1: 'Cd-media',
    2: 'Fd-media',
    4: 'Hd-media',
    8: 'Ris',
}

power_supply_modes = {
    '1' : 'loadBalance',
    '2' : 'activeBackup',
    '3' : 'unknown'
}

def _megarac_abbrev_image(name):
    # MegaRAC platform in some places needs an abbreviated filename
    # Their scheme in such a scenario is a max of 20.  Truncation is
    # acheived by taking the first sixteen, then skipping ahead to the last
    # 4 (presumably to try to keep '.iso' or '.img' in the name).
    if len(name) <= 20:
        return name
    return name[:16] + name[-4:]

ris_configuration_parameter_selectors = {
    0: 'image_name',
    1: 'source_path',
    2: 'ip_address',
    3: 'user_name',
    4: 'password',
    5: 'share_type',
    6: 'domain_name',
    7: 'start_mount',
    8: 'mount_status',
    9: 'error_code',
    10: 'ris_state'
}

categorie_items = ["cpu", "dimm", "firmware", "bios_version"]

class OEMHandler(generic.OEMHandler):
    # noinspection PyUnusedLocal
    def __init__(self, oemid, ipmicmd, snmpcmd):
        # will need to retain data to differentiate
        # variations.  For example System X versus Thinkserver
        self.vendor = 'huawei'
        self.oemid = oemid
        self._fpc_variant = None
        self.ipmicmd = weakref.proxy(ipmicmd)
        self._has_megarac = None
        self.oem_inventory_info = None
        self._mrethidx = None
        self._hasimm = None
        self._hasxcc = None
        if self.has_xcc:
            self.immhandler = imm.XCCClient(ipmicmd)
        elif self.has_imm:
            self.immhandler = imm.IMMClient(ipmicmd)
        self.snmpcmd = snmpcmd
        # get inventory info at initialization
        self._get_inventory_info()

    @property
    def _megarac_eth_index(self):
        if self._mrethidx is None:
            chan = self.ipmicmd.get_network_channel()
            rsp = self.ipmicmd.xraw_command(0x32, command=0x62, data=(chan,))
            self._mrethidx = rsp['data'][0]
        return self._mrethidx

    def get_video_launchdata(self):
        if self.has_tsm:
            return self.get_tsm_launchdata()

    def get_tsm_launchdata(self):
        pass

    def process_event(self, event, ipmicmd, seldata):
        if 'oemdata' in event:
            oemtype = seldata[2]
            oemdata = event['oemdata']
            if oemtype == 0xd0:  # firmware update
                event['component'] = firmware_types.get(oemdata[0], None)
                event['component_type'] = ipmiconst.sensor_type_codes[0x2b]
                slotnumber = (oemdata[1] & 0b11111000) >> 3
                if slotnumber:
                    event['component'] += ' {0}'.format(slotnumber)
                event['event'], event['severity'] = \
                    firmware_event[oemdata[1] & 0b111]
                event['event_data'] = '{0}.{1}'.format(oemdata[2], oemdata[3])
            elif oemtype == 0xd1:  # BIOS recovery
                event['severity'] = pygconst.Health.Warning
                event['component'] = 'BIOS/UEFI'
                event['component_type'] = ipmiconst.sensor_type_codes[0xf]
                status = oemdata[0]
                method = (status & 0b11110000) >> 4
                status = (status & 0b1111)
                if method == 1:
                    event['event'] = 'Automatic recovery'
                elif method == 2:
                    event['event'] = 'Manual recovery'
                if status == 0:
                    event['event'] += '- Failed'
                    event['severity'] = pygconst.Health.Failed
                if oemdata[1] == 0x1:
                    event['event'] += '- BIOS recovery image not found'
                event['event_data'] = '{0}.{1}'.format(oemdata[2], oemdata[3])
            elif oemtype == 0xd2:  # eMMC status
                if oemdata[0] == 1:
                    event['component'] = 'eMMC'
                    event['component_type'] = ipmiconst.sensor_type_codes[0xc]
                    if oemdata[0] == 1:
                        event['event'] = 'eMMC Format error'
                        event['severity'] = pygconst.Health.Failed
            elif oemtype == 0xd3:
                if oemdata[0] == 1:
                    event['event'] = 'User privilege modification'
                    event['severity'] = pygconst.Health.Ok
                    event['component'] = 'User Privilege'
                    event['component_type'] = ipmiconst.sensor_type_codes[6]
                    event['event_data'] = \
                        'User {0} on channel {1} had privilege changed ' \
                        'from {2} to {3}'.format(
                            oemdata[2], oemdata[1], oemdata[3] & 0b1111,
                            (oemdata[3] & 0b11110000) >> 4
                        )
            else:
                event['event'] = 'OEM event: {0}'.format(
                    ' '.join(format(x, '02x') for x in event['oemdata']))
            del event['oemdata']
            return
        evdata = event['event_data_bytes']
        if event['event_type_byte'] == 0x75:  # ME event
            event['component'] = 'ME Firmware'
            event['component_type'] = ipmiconst.sensor_type_codes[0xf]
            event['event'], event['severity'] = me_status.get(
                evdata[1], ('Unknown', pygconst.Health.Warning))
            if evdata[1] == 3:
                event['event'], event['severity'] = me_flash_status.get(
                    evdata[2], ('Unknown state', pygconst.Health.Warning))
            elif evdata[1] == 9:
                event['event'] += ' (0x{0:2x})'.format(evdata[2])
            elif evdata[1] == 0xf and evdata[2] & 0b10000000:
                event['event'] = 'Auto configuration failed'
                event['severity'] = pygconst.Health.Critical
        # For HDD bay events, the event data 2 is the bay, modify
        # the description to be more specific
        if (event['event_type_byte'] == 0x6f and
                (evdata[0] & 0b11000000) == 0b10000000 and
                event['component_type_id'] == 13):
            event['component'] += ' {0}'.format(evdata[1] & 0b11111)

    def get_ntp_enabled(self):
        if self.has_tsm or self.has_ami or self.has_asrock:
            ntpres = self.ipmicmd.xraw_command(netfn=0x32, command=0xa7)
            return ntpres['data'][0] == '\x01'
        return None

    def get_ntp_servers(self):
        if self.has_tsm or self.has_ami or self.has_asrock:
            srvs = []
            ntpres = self.ipmicmd.xraw_command(netfn=0x32, command=0xa7)
            srvs.append(ntpres['data'][1:129].rstrip('\x00'))
            srvs.append(ntpres['data'][129:257].rstrip('\x00'))
            return srvs
        return None

    def set_ntp_enabled(self, enabled):
        if self.has_tsm or self.has_ami or self.has_asrock:
            if enabled:
                self.ipmicmd.xraw_command(
                    netfn=0x32, command=0xa8, data=(3, 1), timeout=15)
            else:
                self.ipmicmd.xraw_command(
                    netfn=0x32, command=0xa8, data=(3, 0), timeout=15)
            return True
        return None

    def set_ntp_server(self, server, index=0):
        if self.has_tsm or self.has_ami or self.has_asrock:
            if not (0 <= index <= 1):
                raise pygexc.InvalidParameterValue("Index must be 0 or 1")
            cmddata = bytearray((1 + index, ))
            cmddata += server.ljust(128, '\x00')
            self.ipmicmd.xraw_command(netfn=0x32, command=0xa8, data=cmddata)
            return True
        return None

    @property
    def is_fpc(self):
        """True if the target is a Lenovo nextscale fan power controller
        """
        fpc_id = (19046, 32, 1063)
        smm_id = (19046, 32, 1180)
        currid = (self.oemid['manufacturer_id'], self.oemid['device_id'],
                  self.oemid['product_id'])
        if currid == fpc_id:
            self._fpc_variant = 6
        elif currid == smm_id:
            self._fpc_variant = 2
        return self._fpc_variant

    @property
    def is_sd350(self):
        return (19046, 32, 13616) == (self.oemid['manufacturer_id'],
                                      self.oemid['device_id'],
                                      self.oemid['product_id'])

    @property
    def has_tsm(self):
        """True if this particular server have a TSM based service processor
        """
        if (self.oemid['manufacturer_id'] == 19046 and
                self.oemid['device_id'] == 32):
            try:
                self.ipmicmd.xraw_command(netfn=0x3a, command=0xf)
            except pygexc.IpmiException as ie:
                if ie.ipmicode == 193:
                    return False
                raise
            return True
        return False
    
    @property
    def has_ami(self):
        """True if this particular server is AMI based lenovo server
        """
        if(self.oemid['manufacturer_id'] == 19046 and 
                self.oemid['product_id'] == 13616):
            try:
                rsp = self.ipmicmd.xraw_command(netfn=0x3a, command=0x80)
            except pygexc.IpmiException as ie:
                if ie.ipmicode == 193:
                    return False
                raise
            if ord(rsp['data'][0]) in range(5):
                return True
            else:
                return False
        return False
                
    @property
    def has_asrock(self):
        """True if this particular server have a ASROCKRACK based service processor (RS160 or TS460)
        """
        # RS160 (Riddler) product id is 1182 (049Eh)
        # TS460 (WildThing) product id is 1184 (04A0h)
        if (self.oemid['manufacturer_id'] == 19046 and
            (self.oemid['product_id'] == 1182 or self.oemid['product_id'] == 1184)):
            try:
                self.ipmicmd.xraw_command(netfn=0x3a, command=0x50, data=(0x00, 0x00, 0x00))
            except pygexc.IpmiException as ie:
                if ie.ipmicode == 193:
                    return False
                raise
            return True
        return False
    
    @property
    def isTS460(self):
        if (self.oemid['product_id'] == 1184):
            return True;
        return False;
    
    def get_oem_inventory_descriptions(self):
        #if self.has_tsm or self.has_ami or self.has_asrock:
        #    # Thinkserver with TSM
        #    if not self.oem_inventory_info:
        #        self._collect_tsm_inventory()
        #    return iter(self.oem_inventory_info)
        #elif self.has_imm:
        #    return self.immhandler.get_hw_descriptions()
        #return ()
        return iter(self.oem_inventory_info)

    def _get_net_info(self, index):
        oilManufacturer = oid.net_fields['Manufacturer'] + index
        oilModel = oid.net_fields['model'] + index
        oilSpeed = oid.net_fields['interface'] + index

        oidList = {'Manufacturer': oilManufacturer, 'Model': oilModel, 'Interface': oilSpeed}
        return self.snmpcmd.dictGet(oidList)

    def _get_raid_info(self, index):
        raid_info  = {
                'AdapterType': 'RAIDController',
                'FlashComponent2Name': 'NVDT',
                'FlashComponent2Version': '',
                'FlashComponent3Name': '',
                'FlashComponent3Version': '',
                'FlashComponent4Name': '',
                'FlashComponent4Version': '',
                'FlashComponent5Name': '',
                'FlashComponent5Version': '',
                'FlashComponent6Name': '',
                'FlashComponent6Version': '',
                'FlashComponent7Name': '',
                'FlashComponent7Version': '',
                'FlashComponent8Name': '',
                'FlashComponent8Version': '',
                'SupercapPresence': 'Absent'
        }

        oidList = {
                    'FlashComponent1Name': oid.raid_fields['ComponentName'] + index,
                    'FlashComponent1Version': oid.raid_fields['FwVersion'] + index,
                    'FlashComponent2Version': oid.raid_fields['NVDataVersion'] + index,
        }
        #'SupercapPresence': oid.raid_fields['BBUPresence'] + index
        raid_info.update(self.snmpcmd.dictGet(oidList))
        return raid_info

    def _disk_info_format(self, disk_info):

        if(disk_info['LinkSpeed'] == ""):
            disk_info['LinkSpeed'] = ''
        elif(disk_info['LinkSpeed'] == '-1' ):
            disk_info['LinkSpeed'] = ''
        else:
            disk_info['LinkSpeed'] += ' Mb/s'


        if(disk_info['Size'] == '-1'):
            disk_info['Size'] = ''
        elif (disk_info['Size'] == ''):
            disk_info['Size'] = ''
        else:
            disk_info['Size'] += ' MB'


        if(disk_info['MediaType'] == '1'):
            disk_info['MediaType'] = 'HDD'
        else:
            disk_info['MediaType'] = ''


        if(disk_info['InterfaceType'] == '3'):
            disk_info['InterfaceType'] = 'SAS'
        else:
            disk_info['InterfaceType'] = ''


        if(disk_info['DeviceState'] == '1'):
            disk_info['DeviceState'] = 'active'
        else:
            disk_info['DeviceState'] = 'inactive'
        
        return


    def _get_disk_info(self, index):
        disk_info = {
                'ControllerIndex': index,
                'DeviceState': '',
                'FormFactor': '',
                'InterfaceType':'',
                'LinkSpeed':'',
                'MediaType': '',
                'Size': '',
                'SlotNumber': index,
                'VendorID': ''                
                }
        oidList = {
                'DeviceState': oid.disk_fields['DeviceState'] + index,
                'FormFactor': oid.disk_fields['Manufacturer'] + index,
                'InterfaceType': oid.disk_fields['InterfaceType'] + index,
                'LinkSpeed': oid.disk_fields['SpeedInMbps'] + index,
                'MediaType': oid.disk_fields['MediaType'] + index,
                'Size': oid.disk_fields['CapacityInMB'] + index,
                'Model': oid.disk_fields['ModelNumber'] + index,
                'VendorID': oid.disk_fields['Manufacturer'] + index,
                }

        disk_info.update(self.snmpcmd.dictGet(oidList))
        self._disk_info_format(disk_info)

        if( disk_info['Size'] == ''):
            disk_info = None

        return disk_info

    def _get_cpu_info(self, index):
        return self.snmpcmd.dictGet({
            'Cores': oid.cpu_fields['Cores'] + index,
            'Family': oid.cpu_fields['Family'] + index,
            'Manufacturer': oid.cpu_fields['Manufacturer'] + index,
            'Maximum Frequency': oid.cpu_fields['Maximum Frequency'] + index,
            'Threads': oid.cpu_fields['Threads'] + index,
            'Type': oid.cpu_fields['Type'] + index,
            'Model': oid.cpu_fields['Model'] + index
        })

    def _get_mem_info(self, index):
        # XCLA supported but not needed in Test.
        mem_info = {
            'Model': '',
            'Stepping': '',
            'channel_number': '',
            'speed': self.snmpcmd.get(oid.mem_fields['speed'] + index).strip(),
            'capacity_mb': self.snmpcmd.get(oid.mem_fields['capacity_mb'] + index).strip().split(' ')[0]
        }
        # Test needed.
        dic_get = {
            'manufacturer': oid.mem_fields['manufacturer'] + index,
            'module_type': oid.mem_fields['module_type'] + index,
            'ddr_voltage': oid.mem_fields['ddr_voltage'] + index,
            'manufacture_location': oid.mem_fields['manufacture_location'] + index,
            'serial': oid.mem_fields['serial'] + index
        }
        mem_info.update(self.snmpcmd.dictGet(dic_get))
        return mem_info

    def _get_power_supply(self, index):
        power_supply = {
            'DMTF Power Supply Type': power_supply_modes[self.snmpcmd.get(oid.power_supply['power_supply_mode'])],
            'DMTF Input Voltage Range': '',
            'Unplugged': False,
            'Board product name': '',
            'Board manufacture date': '',
            'Presence State': int(self.snmpcmd.get(oid.power_supply['presence'] + index)),
            'Hot Replaceable': True
        }
        dic_get = {
            'Board model': oid.power_supply['model'] + index,
            'Board manufacturer revision': oid.power_supply['revision'] + index,
            'Capacity W': oid.power_supply['capacity'] + index,
            'Board manufacturer': oid.power_supply['manufacturer'] + index,
            'Board serial number': oid.power_supply['serial_number'] + index,
            'Location': oid.power_supply['location'] + index
        }
        power_supply.update(self.snmpcmd.dictGet(dic_get))
        return power_supply

    def _get_inventory_info(self):
        # return json format info
        self.oem_inventory_info = {}
        # first get cpu number using snmp walk.
        for i in range(1, len(self.snmpcmd.walk(oid.cpu_fields['number'])) + 1):
            self.oem_inventory_info['CPU ' + str(i)] = self._get_cpu_info(str(i))

        # first get memory nubmer using snmp walk.
        for i in range(1, len(self.snmpcmd.walk(oid.mem_fields['number'])) + 1):
            self.oem_inventory_info['DIMM ' + str(i)] = self._get_mem_info(str(i))

        # net
        for i in range(1, len(self.snmpcmd.walk(oid.net_fields['number'])) + 1):
            self.oem_inventory_info['NET ' + str(i)] = self._get_net_info(str(i))

        # raid
        for i in range(1, len(self.snmpcmd.walk(oid.raid_fields['number'])) + 1):
            self.oem_inventory_info['RAID Controller ' + str(i)] = self._get_raid_info(str(i))

        # disk
        for i in range(1, len(self.snmpcmd.walk(oid.disk_fields['number'])) + 1):
            diskInfo = self._get_disk_info(str(i))

            if(diskInfo):
                self.oem_inventory_info['RAID Drive ' + str(i)] = diskInfo
                self.oem_inventory_info['Drive ' + str(i)] = diskInfo


        # power
        for i in range(1, len(self.snmpcmd.walk(oid.power_supply['number'])) + 1):
            self.oem_inventory_info['Power Supply ' + str(i)] = self._get_power_supply(str(i))

    def get_oem_inventory(self):
        #if self.has_tsm or self.has_ami or self.has_asrock:
            #self._collect_tsm_inventory()
            #for compname in self.oem_inventory_info:
                #yield (compname, self.oem_inventory_info[compname])
        #elif self.has_imm:
            #for inv in self.immhandler.get_hw_inventory():
                #yield inv
        for component in self.oem_inventory_info:
            print component, self.oem_inventory_info[component]
            yield (component, self.oem_inventory_info[component])

    def get_sensor_data(self):
        if self.is_fpc:
            for name in nextscale.get_sensor_names(self._fpc_variant):
                yield nextscale.get_sensor_reading(name, self.ipmicmd,
                                                   self._fpc_variant)

    def get_sensor_descriptions(self):
        if self.is_fpc:
            return nextscale.get_sensor_descriptions(self._fpc_variant)
        return ()

    def get_sensor_reading(self, sensorname):
        if self.is_fpc:
            return nextscale.get_sensor_reading(sensorname, self.ipmicmd,
                                                self._fpc_variant)
        return ()

    def get_inventory_of_component(self, component):
        #if self.has_tsm or self.has_ami or self.has_asrock:
        #    self._collect_tsm_inventory()
        #    return self.oem_inventory_info.get(component, None)
        #if self.has_imm:
        #    return self.immhandler.get_component_inventory(component)
        return self.oem_inventory_info.get(component, None)

    def get_cmd_type (self, categorie_item, catspec): 
        if self.has_asrock:
            cmd_type = catspec["command"]["asrock"]
        elif categorie_item in categorie_items:
            cmd_type = catspec["command"]["lenovo"]
        else:
            cmd_type = catspec["command"]
        
        return cmd_type
    
    def _collect_tsm_inventory(self):
        self.oem_inventory_info = {}
        
        asrock = False
        if self.has_asrock: 
            asrock = True
        for catid, catspec in inventory.categories.items():
            #skip the inventory fields if the system is RS160  
            if asrock and catid not in categorie_items:
                continue
                
            if (catspec.get("workaround_bmc_bug", False) and catspec["workaround_bmc_bug"]("ami" if self.has_ami else "lenovo")):
                rsp = None
                
                cmd = self.get_cmd_type (catid, catspec)
                                                         
                tmp_command = dict(cmd)
                
                tmp_command["data"] = list(tmp_command["data"])
                count = 0
                for i in range(0x01, 0xff):
                    tmp_command["data"][-1] = i
                    try:
                        partrsp = self.ipmicmd.xraw_command(**tmp_command)
                        
                        count += 1
                        
                        if asrock and partrsp["data"][1] == "\xff":
                            continue                       

                        if rsp is None:
                            rsp = partrsp
                            rsp["data"] = list(rsp["data"])
                        else:
                            rsp["data"].extend(partrsp["data"][1:])
                    except Exception:
                        break
                # If we didn't get any response, assume we don't have
                # this category and go on to the next one
                if rsp is None:
                    continue
                rsp["data"].insert(1, count)
                rsp["data"] = buffer(bytearray(rsp["data"]))
            else:
                try:
                    cmd = self.get_cmd_type (catid, catspec)
                    rsp = self.ipmicmd.xraw_command(**cmd)
                except pygexc.IpmiException:
                    continue
            # Parse the response we got
            try:
                items = inventory.parse_inventory_category(
                    catid, rsp, asrock, 
                    countable=catspec.get("countable", True)
                )
            except Exception:
                # If we can't parse an inventory category, ignore it
                print(traceback.print_exc())
                continue

            for item in items:
                try:
                    # Originally on ThinkServer and SD350 (Kent), the DIMM is distinguished by slot, 
                    # the key is the value of slot number (item["index"])
                    # While on RS160/TS460 the DIMMs is distinguished by slot number and channel number,
                    # the key is the value of the sum of slot number and channel number
                    if asrock and catid == "dimm":
                        if item["channel_number"] == 1:
                            key = catspec["idstr"].format(item["index"])
                        else:
                            key = catspec["idstr"].format(item["index"]+item["channel_number"])
                    else:
                        key = catspec["idstr"].format(item["index"])
                    del item["index"]
                    self.oem_inventory_info[key] = item
                except Exception:
                    # If we can't parse an inventory item, ignore it
                    print(traceback.print_exc())
                    continue

    def get_leds(self):
                
        cmd = 0x02
        led_set = leds
        led_set_status = led_status
        
        if self.has_ami:
            cmd = 0x05
            led_set = ami_leds
            led_set_status = ami_led_status
        elif self.has_asrock:
            cmd = 0x50
            #because rs160 has different led info with ts460 
            if self.isTS460:
                    led_set = ts460_leds
            else:
                led_set = asrock_leds
                
            led_set_status = asrock_led_status
        
        if self.has_ami or self.has_asrock or self.has_tsm:
            for (name, id_) in led_set.items():
                try:
                    if self.has_asrock:
                        rsp = self.ipmicmd.xraw_command(netfn=0x3A, command=cmd,
                                                        data=(0x03, id_, 0x00))
                        status = ord(rsp['data'][1])
                    else:
                        rsp = self.ipmicmd.xraw_command(netfn=0x3A, command=cmd,
                                                        data=(id_,))
                        status = ord(rsp['data'][0])
                except pygexc.IpmiException:
                    continue  # Ignore LEDs we can't retrieve
                status = led_set_status.get(status, led_status_default)
                yield (name, {'status': status})

    def set_identify(self, on, duration):
        if on and not duration and self.is_sd350:
            self.ipmicmd.xraw_command(netfn=0x3a, command=6, data=(1, 1))
        else:
            raise pygexc.UnsupportedFunctionality()

    def process_fru(self, fru):
        if fru is None:
            return fru
        if self.has_tsm:
            fru['oem_parser'] = 'lenovo'
            # Thinkserver lays out specific interpretation of the
            # board extra fields
            try:
                _, _, wwn1, wwn2, mac1, mac2 = fru['board_extra']
                if wwn1 not in ('0000000000000000', ''):
                    fru['WWN 1'] = wwn1.encode('utf-8')
                if wwn2 not in ('0000000000000000', ''):
                    fru['WWN 2'] = wwn2.encode('utf-8')
                if mac1 not in ('00:00:00:00:00:00', ''):
                    fru['MAC Address 1'] = mac1.encode('utf-8')
                if mac2 not in ('00:00:00:00:00:00', ''):
                    fru['MAC Address 2'] = mac2.encode('utf-8')
            except (AttributeError, KeyError):
                pass
            try:
                # The product_extra field is UUID as the system would present
                # in DMI.  This is different than the two UUIDs that
                # it returns for get device and get system uuid...
                byteguid = fru['product_extra'][0]
                # It can present itself as claiming to be ASCII when it
                # is actually raw hex.  As a result it triggers the mechanism
                # to strip \x00 from the end of text strings.  Work around this
                # by padding with \x00 to the right if less than 16 long
                byteguid.extend('\x00' * (16 - len(byteguid)))
                if byteguid not in ('\x20' * 16, '\x00' * 16, '\xff' * 16):
                    fru['UUID'] = util.decode_wireformat_uuid(byteguid)
            except (AttributeError, KeyError, IndexError):
                pass
            return fru
        elif self.has_asrock:
            fru['oem_parser'] = 'lenovo'
            # ASRock RS160 TS460 lays out specific interpretation of the
            # board extra fields
            try:
                mac1 = fru['board_extra']
                if mac1 not in ('00:00:00:00:00:00', ''):
                    fru['MAC Address 1'] = mac1.encode('utf-8')
            except (AttributeError, KeyError):
                pass
            return fru
        elif self.has_imm:
            fru['oem_parser'] = 'lenovo'
            try:
                bextra = fru['board_extra']
                fru['FRU Number'] = bextra[0]
                fru['Revision'] = bextra[4]
                macs = bextra[6]
                macprefix = None
                idx = 0
                endidx = len(macs) - 5
                macprefix = None
                while idx < endidx:
                    currmac = macs[idx:idx+6]
                    if not isinstance(currmac, bytearray):
                        # invalid vpd format, abort attempts to extract
                        # mac in this way
                        break
                    if currmac == b'\x00\x00\x00\x00\x00\x00':
                        break
                    # VPD may veer off, detect and break off
                    if macprefix is None:
                        macprefix = currmac[:3]
                    elif currmac[:3] != macprefix:
                        break
                    ms = mac_format.format(*currmac)
                    ifidx = idx / 6 + 1
                    fru['MAC Address {0}'.format(ifidx)] = ms
                    idx = idx + 6
            except (AttributeError, KeyError, IndexError):
                pass
            return fru
        else:
            fru['oem_parser'] = None
            return fru

    @property
    def has_xcc(self):
        if self._hasxcc is not None:
            return self._hasxcc
        try:
            bdata = self.ipmicmd.xraw_command(netfn=0x3a, command=0xc1)
        except pygexc.IpmiException:
            self._hasxcc = False
            self._hasimm = False
            return False
        if len(bdata['data'][:]) != 3:
            self._hasimm = False
            self._hasxcc = False
            return False
        rdata = bytearray(bdata['data'][:])
        self._hasxcc = rdata[1] & 16 == 16
        if self._hasxcc:
            # For now, have imm calls go to xcc, since they are providing same
            # interface.  Longer term the hope is that all the Lenovo
            # stuff will branch at init, and not have conditionals
            # in all the functions
            self._hasimm = self._hasxcc
        return self._hasxcc

    @property
    def has_imm(self):
        if self._hasimm is not None:
            return self._hasimm
        try:
            bdata = self.ipmicmd.xraw_command(netfn=0x3a, command=0xc1)
        except pygexc.IpmiException:
            self._hasimm = False
            return False
        if len(bdata['data'][:]) != 3:
            self._hasimm = False
            return False
        rdata = bytearray(bdata['data'][:])
        self._hasimm = (rdata[1] & 1 == 1) or (rdata[1] & 16 == 16)
        return self._hasimm

    def get_oem_firmware(self, bmcver):
        if self.has_tsm or self.has_ami or self.has_asrock:
            command = firmware.get_categories()["firmware"]
            
            fw_cmd = self.get_cmd_type ("firmware", command)      
            
            rsp = self.ipmicmd.xraw_command(**fw_cmd)
            # the newest Lenovo ThinkServer versions are returning Bios version
            # numbers through another command
            bios_versions = None
            if self.has_tsm or self.has_asrock:
                bios_command = firmware.get_categories()["bios_version"]
                
                bios_cmd = self.get_cmd_type ("bios_version", bios_command)                    
                bios_rsp = self.ipmicmd.xraw_command(**bios_cmd)
                if self.has_asrock:
                    bios_versions = bios_rsp['data']
                else:
                    bios_versions = bios_command["parser"](bios_rsp['data'])
            # pass bios versions to firmware parser
            # TODO: find a better way to implement this
            return command["parser"](rsp["data"], bios_versions, self.has_asrock)
        elif self.has_imm:
            return self.immhandler.get_firmware_inventory(bmcver)
        elif self.is_fpc:
            return nextscale.get_fpc_firmware(bmcver, self.ipmicmd,
                                              self._fpc_variant)
        return super(OEMHandler, self).get_oem_firmware(bmcver)

    def get_oem_capping_enabled(self):
        if self.has_tsm:
            rsp = self.ipmicmd.xraw_command(netfn=0x3a, command=0x1b,
                                            data=(3,))
            # disabled
            if rsp['data'][0] == '\x00':
                return False
            # enabled
            else:
                return True

    def set_oem_capping_enabled(self, enable):
        """Set PSU based power capping

        :param enable: True for enable and False for disable
        """
        # 1 - Enable power capping(default)
        if enable:
            statecode = 1
        # 0 - Disable power capping
        else:
            statecode = 0
        if self.has_tsm:
            self.ipmicmd.xraw_command(netfn=0x3a, command=0x1a,
                                      data=(3, statecode))
            return True

    def get_oem_remote_kvm_available(self):
        if self.has_tsm:
            rsp = self.ipmicmd.raw_command(netfn=0x3a, command=0x13)
            return rsp['data'][0] == 0
        return False

    def _restart_dns(self):
        if self.has_tsm:
            self.ipmicmd.xraw_command(netfn=0x32, command=0x6c, data=(7, 0))

    def get_oem_domain_name(self):
        pass

    def set_oem_domain_name(self, name):
        pass

    """ Gets a remote console launcher for a Lenovo ThinkServer.

    Returns a tuple: (content type, launcher) or None if the launcher could
    not be retrieved."""
    def _get_ts_remote_console(self, bmc, username, password):
        # We don't establish non-secure connections without checking
        # certificates
        if not self.ipmicmd.certverify:
            return
        conn = wc.SecureHTTPConnection(bmc, 443,
                                       verifycallback=self.ipmicmd.certverify)
        conn.connect()
        params = urllib.urlencode({
            'WEBVAR_USERNAME': username,
            'WEBVAR_PASSWORD': password
        })
        headers = {
            'Connection': 'keep-alive'
        }
        conn.request('POST', '/rpc/WEBSES/create.asp', params, headers)
        rsp = conn.getresponse()
        if rsp.status == 200:
            conn.cookies = {}
            body = rsp.read().split('\n')
            session_line = None
            for line in body:
                if 'SESSION_COOKIE' in line:
                    session_line = line
            if session_line is None:
                return

            session_id = session_line.split('\'')[3]
            # Usually happens when maximum number of sessions is reached
            if session_id == 'Failure_Session_Creation':
                return

            headers = {
                'Connection': 'keep-alive',
                'Cookie': 'SessionCookie=' + session_id,
            }
            conn.request(
                'GET',
                '/Java/jviewer.jnlp?EXTRNIP=' + bmc + '&JNLPSTR=JViewer',
                None, headers)
            rsp = conn.getresponse()
            if rsp.status == 200:
                return rsp.getheader('Content-Type'), base64.b64encode(
                    rsp.read())
        conn.close()

    def get_graphical_console(self):
        return self._get_ts_remote_console(self.ipmicmd.bmc,
                                           self.ipmicmd.ipmi_session.userid,
                                           self.ipmicmd.ipmi_session.password)

    def add_extra_net_configuration(self, netdata):
        if self.has_tsm:
            ipv6_addr = self.ipmicmd.xraw_command(
                netfn=0x0c, command=0x02,
                data=(0x01, 0xc5, 0x00, 0x00))["data"][1:]
            if not ipv6_addr:
                return
            ipv6_prefix = ord(self.ipmicmd.xraw_command(
                netfn=0xc, command=0x02,
                data=(0x1, 0xc6, 0, 0))['data'][1])
            if hasattr(socket, 'inet_ntop'):
                ipv6str = socket.inet_ntop(socket.AF_INET6, ipv6_addr)
            else:
                # fall back to a dumber, but more universal formatter
                ipv6str = binascii.b2a_hex(ipv6_addr)
                ipv6str = ':'.join([ipv6str[x:x+4] for x in range(0, 32, 4)])
            netdata['ipv6_addresses'] = [
                '{0}/{1}'.format(ipv6str, ipv6_prefix)]

    def get_extra_net_configuration(self):
        ipv6_addr = self.ipmicmd.xraw_command(netfn=0x0c, command=0x02,
            data=(0x01, 0xc5, 0x00, 0x00))["data"][1:]
        if not ipv6_addr:
            return '::'
        # TODO: create or use a IPv6 address formatting function
        bytes = [format(ord(a), '02x') for a in ipv6_addr]
        bytes = zip(bytes[0::2], bytes[1::2])
        ipv6_addr = ':'.join([b[0] + b[1] for b in bytes])
        return {"ipv6_addr": ipv6_addr}
    
    def get_sensor_reading(self, sensorname):
        """Get an OEM sensor
    
        If software wants to model some OEM behavior as a 'sensor' without
        doing SDR, this hook provides that ability.  It should mimic
        the behavior of 'get_sensor_reading' in command.py.
        """
        for sensor in self.get_sensor_data():
            if sensor.name == sensorname:
                return sensor
    
    def get_sensor_descriptions(self):
        """Get list of OEM sensor names and types

        Iterate over dicts describing a label and type for OEM 'sensors'.  This
        should mimic the behavior of the get_sensor_descriptions function
        in command.py.
        """
        if self.has_ami:
            energy_sensor = energy.Energy(self.ipmicmd)
            for sensor in energy_sensor.get_energy_sensor():
                yield {'name': sensor.name,
                       'type': sensor.type}

    def get_sensor_data(self):
        """Get OEM sensor data

        Iterate through all OEM 'sensors' and return data as if they were
        normal sensors.  This should mimic the behavior of the get_sensor_data
        function in command.py.
        """
        if self.has_ami:
            energy_sensor = energy.Energy(self.ipmicmd)
            for sensor in energy_sensor.get_energy_sensor():
                yield sensor


    def set_oem_extended_privilleges(self, uid):
        """ Set user extended privillege as 'KVM & VMedia Allowed" as you can see bellow.

            |KVM & VMedia Not Allowed	0x00 0x00 0x00 0x00
            |KVM Only Allowed	0x01 0x00 0x00 0x00
            |VMedia Only Allowed	0x02  0x00 0x00 0x00
            |KVM & VMedia Allowed	0x03 0x00 0x00 0x00


        :param uid: User ID.
        """
        if self.has_tsm:
            self.ipmicmd.xraw_command(netfn=0x32 , command=0xa3, data=(uid, 0x03, 0x00, 0x00, 0x00))
            return True
        return False

    def get_ris_configuration_parameters(self, service_type_id):
        return_dict = {}
        for (param_id, param_name) in ris_configuration_parameter_selectors.items():
            # Skipping invalid combinations of param_id and service_type_id
            # Parameter RIS State (10) is only applicable for service type RIS (8)
            if param_id == 10 and service_type_id != 8:
                continue
            elif service_type_id == 8 and param_id != 10:
                continue

            try:
                rsp = self.ipmicmd.raw_command(netfn=0x32, command=0x9e,
                                                data=(service_type_id, param_id))
            except pygexc.IpmiException as ie:
                continue  # Ignore parameters we can't retrieve

            # Decoding hex values according to parameter selectors
            # These parameters are for strings (image name, source path, share type, ip address, domain name, password and user name)
            if param_id in [0, 1, 2, 3, 4, 5, 6]:
                if 'data' in rsp:
                    value = ''.join(chr(rsp['data'][i]) for i in range(2, len(rsp['data'])))
                    value = value.rstrip("\x00")
                else:
                    value = ''
            # These parameters are for values that should be decoded as enable/disable (Start Mount and RIS State)
            elif param_id in [7, 10]:
                value = 'enable' if rsp['data'][2] == 1 else 'disable'
            # Decoding mount status value
            elif param_id == 8:
                value = 'not mount' if rsp['data'][2] == 0 else 'mount success'
            else:
                value = rsp['data'][2]
            return_dict[param_name] = value
        return return_dict

    def set_ris_configuration_parameter(self, media_type_id, param_id, value):
        multiply = lambda value, times=None: [value] * times if times else []
        hexify = lambda x, y=None: ([ord(elem) for elem in x])

        reset_progress_bit = False

        data = [media_type_id, param_id]

        # Ris Restart
        if param_id == 0x0b and media_type_id == 0x08:
            rsp = self.ipmicmd.raw_command(netfn=0x32, command=0x9f, data=data)
        # Ris State
        elif param_id == 0x0a and media_type_id == 0x08:
            data.extend([0x00, 0x00 if value == 'disable' else 0x01])
            rsp = self.ipmicmd.raw_command(netfn=0x32, command=0x9f, data=data)
        # Password
        elif param_id in [0x04] and media_type_id != 0x08:
            data.append(0x00)
            data.extend(hexify(value, 32))
            rsp = self.ipmicmd.raw_command(netfn=0x32, command=0x9f, data=data)
        elif param_id in [0x02, 0x05] and media_type_id != 0x08:
            data.append(0x00)
            data.extend(hexify(value, 64))
            rsp = self.ipmicmd.raw_command(netfn=0x32, command=0x9f, data=data)
        # Ris Souce Path, image name, domain name or user name
        elif param_id in [0x01, 0x00, 0x06, 0x03] and media_type_id != 0x08:
            if len(value) > 256:
                raise StandardError('Value should be less than 256 caracteres')
            # Progress Bit
            self.ipmicmd.xraw_command(netfn=0x32, command=0x9f, data=(0x01, param_id, 0x00, 0x01))

            for i in range(1, int(math.ceil(len(value) / 64.0)) + 1):
                data = [0x01, param_id, i]
                substr_start = (i - 1) * 64
                substr_end   =      i  * 64
                data.extend(hexify(value[substr_start:substr_end], 64))
                self.ipmicmd.raw_command(netfn=0x32, command=0x9f, data=data)

            # Reset Progress Bit
            rsp = self.ipmicmd.raw_command(netfn=0x32, command=0x9f, data=(0x01, param_id, 0x00, 0x00))
        else:
            raise StandardError('Unknown parameter or not implemented')

        error_messages = {
            # Documented message
            0x95: 'Image format is not supported',
        }

        if 'code' in rsp and rsp['code'] != 0:
            if rsp['code'] in error_messages:
                raise pygexc.IpmiException(error_messages[rsp['code']], rsp['code'])
            else:
                raise pygexc.IpmiException(rsp['error'], rsp['code'])

    def set_ris_redirection_state(self, image_type, value):
        self.ipmicmd.raw_command(netfn=0x32, command=0xa0,
                                 data=[image_type, 0x01 if value == 'start' else 0x00])

    def set_media_redirection_state(self, image_type, image_name, value):
        data = [image_type, 0x01 if value == 'start' else 0x00]
        data.extend([ord(elem) for elem in image_name])
        data.append(0x00)
        rsp = self.ipmicmd.raw_command(netfn=0x3a, command=0x16, data=data)
        error_messages = {
            0x90: 'Media support is not enabled',
            0x91: 'Error in get vmedia configuration',
            0x92: 'Media is not running',
            0x95: 'Slot is not available for the particular Image type',
            0x96: 'Error in retrieving available image information',
            0x97: 'Valid Image is not available',
            0x98: 'Image format is not supported',
            0x99: 'Image file not found',
            0x9a: 'invalid start/stop command'
        }
        if 'code' in rsp and rsp['code'] != 0:
            if rsp['code'] in error_messages:
                raise pygexc.IpmiException(error_messages[rsp['code']], rsp['code'])
            else:
                raise pygexc.IpmiException(rsp['error'], rsp['code'])

    def get_media_redirected_image_info(self, image_type_id):
        image_types = {
            0x01: 'Cd image',
            0x02: 'Fd image',
            0x04: 'Hd image',
            0x08: 'All images'
        }
        data = [6, 0x01, image_type_id]
        rsp = self.ipmicmd.raw_command(netfn=0x32, command=0xd8, data=data)
        return_dict = {}
        if 'data' in rsp:
            rsp_data = rsp['data']
            if rsp_data:
                image_name_array = rsp_data[1:(rsp_data.index(0, 1))]
                return_dict['image_name']    = ''.join([chr(x) for x in image_name_array])
                return_dict['image_type']    = image_types[rsp_data[257]]
                return_dict['is_redirected'] = 'yes' if 1 == rsp_data[258] else 'no'
                return_dict['image_index']   = rsp_data[259]
                return_dict['session_index'] = rsp_data[260]
        return return_dict

    @property
    def has_megarac(self):
        # if there is functionality that is the same for tsm or generic
        # megarac, then this is appropriate.  If there's a TSM specific
        # preferred, use has_tsm first
        if self._has_megarac is not None:
            return self._has_megarac
        self._has_megarac = False
        try:
            rsp = self.ipmicmd.xraw_command(netfn=0x32, command=0x7e)
            # We don't have a handy classify-only, so use get sel policy
            # rsp should have a length of one, and be either '\x00' or '\x01'
            if len(rsp['data'][:]) == 1 and rsp['data'][0] in ('\x00', '\x01'):
                self._has_megarac = True
        except pygexc.IpmiException as ie:
            if ie.ipmicode == 0:
                # if it's a generic IpmiException rather than an error code
                # from the BMC, then this is a deeper problem than just an
                # invalid command or command length or similar
                raise
        return self._has_megarac

    def set_alert_ipv6_destination(self, ip, destination, channel):
        if self.has_megarac:
            ethidx = self._megarac_eth_index
            reqdata = bytearray([channel, 193, destination, ethidx, 0])
            parsedip = socket.inet_pton(socket.AF_INET6, ip)
            reqdata.extend(parsedip)
            reqdata.extend('\x00\x00\x00\x00\x00\x00')
            self.ipmicmd.xraw_command(netfn=0xc, command=1, data=reqdata)
            return True
        return False

    def _set_short_ris_string(self, selector, value):
        data = (1, selector, 0) + struct.unpack('{0}B'.format(len(value)),
                                                value)
        self.ipmicmd.xraw_command(netfn=0x32, command=0x9f, data=data)

    def _set_ris_string(self, selector, value):
        if len(value) > 256:
            raise pygexc.UnsupportedFunctionality(
                'Value exceeds 256 characters: {0}'.format(value))
        padded = value + (256 - len(value)) * '\x00'
        padded = list(struct.unpack('256B', padded))
        # 8 = RIS, 4 = hd, 2 = fd, 1 = cd
        try:  # try and clear in-progress if left incomplete
            self.ipmicmd.xraw_command(netfn=0x32, command=0x9f,
                                      data=(1, selector, 0, 0))
        except pygexc.IpmiException:
            pass
        # set in-progress
        self.ipmicmd.xraw_command(netfn=0x32, command=0x9f,
                                  data=(1, selector, 0, 1))
        # now do the set
        for x in range(0, 256, 64):
            currdata = padded[x:x+64]
            currchunk = x // 64 + 1
            cmddata = [1, selector, currchunk] + currdata
            self.ipmicmd.xraw_command(netfn=0x32, command=0x9f, data=cmddata)
        # unset in-progress
        self.ipmicmd.xraw_command(netfn=0x32, command=0x9f,
                                  data=(1, selector, 0, 0))

    def _megarac_fetch_image_shortnames(self):
        rsp = self.ipmicmd.xraw_command(netfn=0x32, command=0xd8,
                                        data=(7, 1, 0))
        imgnames = rsp['data'][1:]
        shortnames = []
        for idx in range(0, len(imgnames), 22):
            shortnames.append(imgnames[idx+2:idx+22].rstrip('\0'))
        return shortnames

    def _megarac_media_waitforready(self, imagename):
        # first, we have, sadly, a 10 second grace period for some invisible
        # async activity to get far enough long to monitor
        self.ipmicmd.ipmi_session.pause(10)
        risenabled = '\x00'
        mountok = '\xff'
        while risenabled != '\x01':
            risenabled = self.ipmicmd.xraw_command(
                netfn=0x32, command=0x9e, data=(8, 10))['data'][2]
        while mountok == '\xff':
            mountok = self.ipmicmd.xraw_command(
                netfn=0x32, command=0x9e, data=(1, 8))['data'][2]
        targshortname = _megarac_abbrev_image(imagename)
        shortnames = self._megarac_fetch_image_shortnames()
        while targshortname not in shortnames:
            self.ipmicmd.wait_for_rsp(1)
            shortnames = self._megarac_fetch_image_shortnames()
        self.ipmicmd.ipmi_session.pause(10)
        try:
            self.ipmicmd.xraw_command(netfn=0x32, command=0xa0, data=(1, 0))
            self.ipmicmd.ipmi_session.pause(5)
        except pygexc.IpmiException:
            pass

    def _megarac_attach_media(self, proto, username, password, imagename,
                              domain, path, host):
        # First we must ensure that the RIS is actually enabled
        self.ipmicmd.xraw_command(netfn=0x32, command=0x9f, data=(8, 10, 0, 1))
        if username is not None:
            self._set_ris_string(3, username)
        if password is not None:
            self._set_short_ris_string(4, password)
        if domain is not None:
            self._set_ris_string(6, domain)
        self._set_ris_string(1, path)
        ip = util.get_ipv4(host)[0]
        self._set_short_ris_string(2, ip)
        self._set_short_ris_string(5, proto)
        # now to restart RIS to have changes take effect...
        self.ipmicmd.xraw_command(netfn=0x32, command=0x9f, data=(8, 11))
        # now to kick off the requested mount
        self._megarac_media_waitforready(imagename)
        self._set_ris_string(0, imagename)
        self.ipmicmd.xraw_command(netfn=0x32, command=0xa0,
                                  data=(1, 1))

    def attach_remote_media(self, url, username, password):
        if self.has_imm:
            self.immhandler.attach_remote_media(url, username, password)
        elif self.has_megarac:
            proto, host, path = util.urlsplit(url)
            if proto == 'smb':
                proto = 'cifs'
            domain = None
            path, imagename = path.rsplit('/', 1)
            if username is not None and '@' in username:
                username, domain = username.split('@', 1)
            elif username is not None and '\\' in username:
                domain, username = username.split('\\', 1)
            try:
                self._megarac_attach_media(proto, username, password,
                                           imagename, domain, path, host)
            except pygexc.IpmiException as ie:
                if ie.ipmicode in (0x92, 0x99):
                    # if starting from scratch, this can happen...
                    self._megarac_attach_media(proto, username, password,
                                               imagename, domain, path, host)
                else:
                    raise

    def detach_remote_media(self):
        if self.has_imm:
            self.immhandler.detach_remote_media()
        elif self.has_megarac:
            self.ipmicmd.xraw_command(
                netfn=0x32, command=0x9f, data=(8, 10, 0, 0))
            self.ipmicmd.xraw_command(netfn=0x32, command=0x9f, data=(8, 11))

    def invoke_oem_method(self,method,*arg,**karg):
        methods=[
            "get_alert_destination",
            "set_alert_destination"]
        if method in methods:
            fun = getattr(self, method)
            return fun(*arg,**karg)
        return False

    def set_alert_destination(self, ip=None, acknowledge_required=None,
                              acknowledge_timeout=None, retries=None,
                              destination=0, channel=None):
        pass

    def get_alert_destination(self, destination=0, channel=None):
        pass
