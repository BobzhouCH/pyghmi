#!/usr/bin/env python

import os


class IPMI(object):
    def __init__(self, host, username="admin", passwd='admin'):
        self._host = host
        self._username = username
        self._passwd = passwd

    def run_command(self, command, grep=''):
        cmd = "ipmitool -I lan -H %s -U %s -P %s %s " % (
            self._host, self._username, self._passwd, command )
        if not grep == '':
            cmd += '| grep "%s"' % (grep)
        output = os.popen(cmd).readlines()
        return output


def main():
    ipmi = IPMI("10.100.17.178", 'Administrator','Admin@9000')
    out = ipmi.run_command('fru list')
    print('fru list is %s'%(out))
    out = ipmi.run_command('fru list', 'Product Manufacturer')
    print('fru list with grep is %s'%(out))

if __name__ == "__main__":
    main()