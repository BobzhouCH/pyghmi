#!/usr/bin/env python
# Copyright 2018 Lenovo
# author: Coco Gao
# This file is used to describe dell hardware snmp oid.

cpu_fields = {}
cpu_fields['number'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.1'
cpu_fields['Manufacturer'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.2.'
cpu_fields['Family'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.3.'
cpu_fields['Type'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.4.'
cpu_fields['Maximum Frequency'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.5.'
cpu_fields['Cores'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.12.'
cpu_fields['Threads'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.13.'
cpu_fields['Model'] = '.1.3.6.1.4.1.2011.2.235.1.1.15.50.1.4.'


mem_fields = {}
mem_fields['number'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.1'
mem_fields['manufacturer'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.3.'
mem_fields['module_type'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.11.'
mem_fields['capacity_mb'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.4.'
mem_fields['speed'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.5.'

mem_fields['ddr_voltage'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.13.'
mem_fields['manufacture_location'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.8.'
mem_fields['serial'] = '.1.3.6.1.4.1.2011.2.235.1.1.16.50.1.12.'


net_fields = {}
net_fields['number'] = '.1.3.6.1.4.1.2011.2.235.1.1.25.50.1.1'
net_fields['Manufacturer'] = '.1.3.6.1.4.1.2011.2.235.1.1.25.50.1.9.'
net_fields['model'] = '.1.3.6.1.4.1.2011.2.235.1.1.25.50.1.8.'
net_fields['interface'] = '.1.3.6.1.4.1.2011.2.235.1.1.25.50.1.5.'

raid_fields= {}
raid_fields['number'] = '.1.3.6.1.4.1.2011.2.235.1.1.36.50.1.1'
raid_fields['ComponentName'] = '.1.3.6.1.4.1.2011.2.235.1.1.36.50.1.4.'
raid_fields['HealthStatus'] = '.1.3.6.1.4.1.2011.2.235.1.1.36.50.1.7.'
raid_fields['FwVersion'] = '.1.3.6.1.4.1.2011.2.235.1.1.36.50.1.8.'
raid_fields['NVDataVersion'] = '.1.3.6.1.4.1.2011.2.235.1.1.36.50.1.9.'
raid_fields['BBUPresence'] = '.1.3.6.1.4.1.2011.2.235.1.1.36.50.1.16.'
raid_fields['model'] = '.1.3.6.1.4.1.2011.2.235.1.1.36.50.1.3.'

disk_fields = {}
disk_fields['number'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.1'
disk_fields['presence'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.2.'
disk_fields['DeviceState'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.3.'
disk_fields['CapacityInMB'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.30.'
disk_fields['CapacityInGB'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.12.'
disk_fields['SpeedInMbps'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.18.'
disk_fields['PowerState'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.15.'
disk_fields['MediaType'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.13.'
disk_fields['Manufacturer'] = '.1.3.6.1.4.1.2011.2.235.1.1.18.50.1.9.'
disk_fields['ModelNumber'] = ".1.3.6.1.4.1.2011.2.235.1.1.18.50.1.8."
disk_fields['SerialNumber'] = ".1.3.6.1.4.1.2011.2.235.1.1.18.50.1.7."
disk_fields['Devicename'] = ".1.3.6.1.4.1.2011.2.235.1.1.18.50.1.6."
disk_fields['Location'] = ".1.3.6.1.4.1.2011.2.235.1.1.18.50.1.4."
disk_fields['InterfaceType'] = ".1.3.6.1.4.1.2011.2.235.1.1.18.50.1.14."
disk_fields['Temperature'] = ".1..3.6.1.4.1.2011.2.235.1.1.18.50.1.20."

power_supply = {}
power_supply['number'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.1'
power_supply['power_supply_mode'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.3.0'
power_supply['manufacturer'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.2.'
power_supply['model'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.4.'
power_supply['revision'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.5.'
power_supply['capacity'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.6.'
power_supply['presence'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.9.'
power_supply['serial_number'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.15.'
power_supply['location'] = '.1.3.6.1.4.1.2011.2.235.1.1.6.50.1.11.'

