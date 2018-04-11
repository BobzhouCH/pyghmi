#!/usr/bin/env python
# Copyright 2018 Lenovo
# author: Coco Gao
# This file is used to describe dell hardware snmp oid.

cpu_fields = {}
cpu_fields['number'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.1.1'
cpu_fields['Manufacturer'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.8.1.'
cpu_fields['Family'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.8.1.'
cpu_fields['Type'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.23.1.'
cpu_fields['Maximum Frequency'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.11.1.'
cpu_fields['Cores'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.17.1.'
cpu_fields['Threads'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.19.1.'
cpu_fields['Model'] = '.1.3.6.1.4.1.674.10892.5.4.1100.30.1.23.1.'


mem_fields = {}
mem_fields['number'] = '.1.3.6.1.4.1.674.10892.5.4.1100.50.1.1'
mem_fields['manufacturer'] = '.1.3.6.1.4.1.674.10892.5.4.1100.50.1.21.1.'
mem_fields['module_type'] = '.1.3.6.1.4.1.674.10892.5.4.1100.50.1.7.1.'
mem_fields['capacity_mb'] = '.1.3.6.1.4.1.674.10892.5.4.1100.50.1.14.1.'
mem_fields['speed'] = '.1.3.6.1.4.1.674.10892.5.4.1100.50.1.15.1.'

mem_fields['ddr_voltage'] = ''
mem_fields['manufacture_location'] = '.1.3.6.1.4.1.674.10892.5.4.1100.50.1.8.1.'
mem_fields['serial'] = '.1.3.6.1.4.1.674.10892.5.4.1100.50.1.23.1.'


net_fields = {}
net_fields['number'] = '.1.3.6.1.4.1.674.10892.5.4.1100.90.1.1.1.1'
net_fields['Manufacturer'] = '.1.3.6.1.4.1.674.10892.5.4.1100.90.1.7.1.'
net_fields['model'] = '.1.3.6.1.4.1.674.10892.5.4.1100.90.1.6.1.'
net_fields['interface'] = '.1.3.6.1.4.1.674.10892.5.4.1100.90.1.6.1.'##

raid_fields= {}
raid_fields['number'] = '.1.3.6.1.4.1.'
raid_fields['ComponentName'] = '.1.3.6.1.4.1.'
raid_fields['HealthStatus'] = '.1.3.6.1.4.1.'
raid_fields['FwVersion'] = '.1.3.6.1.4.1.'
raid_fields['NVDataVersion'] = '.1.3.6.1.4.1.'
raid_fields['BBUPresence'] = '.1.3.6.1.4.1.'
raid_fields['model'] = '.1.3.6.1.4.1.'

disk_fields = {}
disk_fields['number'] = '.1.3.6.1.4.1.'
disk_fields['presence'] = '.1.3.6.1.4.1.'
disk_fields['DeviceState'] = '.1.3.6.1.4.1.'
disk_fields['CapacityInMB'] = '.1.3.6.1.4.1.'
disk_fields['CapacityInGB'] = '.1.3.6.1.4.1.'
disk_fields['SpeedInMbps'] = '.1.3.6.1.4.1.'
disk_fields['PowerState'] = '.1.3.6.1.4.1.'
disk_fields['MediaType'] = '.1.3.6.1.4.1.'
disk_fields['Manufacturer'] = '.1.3.6.1.4.1.'
disk_fields['ModelNumber'] = ".1.3.6.1.4.1."
disk_fields['SerialNumber'] = ".1.3.6.1.4.1."
disk_fields['Devicename'] = ".1.3.6.1.4.1."
disk_fields['Location'] = ".1.3.6.1.4.1."
disk_fields['InterfaceType'] = ".1.3.6.1.4.1."
disk_fields['Temperature'] = ".1.3.6.1.4.1."

power_supply = {}
power_supply['number'] = '.1.3.6.1.4.1.'
power_supply['power_supply_mode'] = '.1.3.6.1.4.1.'
power_supply['manufacturer'] = '.1.3.6.1.4.1.'
power_supply['model'] = '.1.3.6.1.4.1.'
power_supply['revision'] = '.1.3.6.1.4.1.'
power_supply['capacity'] = '.1.3.6.1.4.1.'
power_supply['presence'] = '.1.3.6.1.4.1.'
power_supply['serial_number'] = '.1.3.6.1.4.1.'
power_supply['location'] = '.1.3.6.1.4.1.'

