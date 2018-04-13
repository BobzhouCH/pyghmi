#!/usr/bin/env python
# Copyright 2018 Lenovo
# author: Coco Gao
# FreeBSD requirements:
# Compile net-snmp with python bindings

import netsnmp
from socket import gethostbyname, gaierror
import time
import ConfigParser




class ResolveError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Connection:
    __doc__ = "SNMP connection to a single host, containing common data like authentication"

    # Configuring SNMP session towards a single host.
    def __init__(self, host, version=2, vendor=None, **version_ops):

        self.host = host
        self.version = version
        self.options = version_ops
        self.vendor = vendor
        try:
            gethostbyname(host)
        except gaierror:
            raise ResolveError("Couldn't resolve hostname %s" % host)

        if version == 2:
            # Make sure host is resolvable
            self.session = self.get_v2_session(host, version_ops)
        # SNMP V3
        elif version == 3:
            self.session = self.get_v3_session_from_config(host)
        # SNMP V2 or V3
        elif version == 0:
            # try version 2
            self.session = self.get_v2_session(host, version_ops)
            if not self.session:
                # try version 3
                self.session = self.get_v3_session_from_config(host)
            return

        else:
            self.session = None

    def get_v2_session(self, host, version_ops):
        version_ops.setdefault('community', 'public')
        version_ops.setdefault('retries', 3)
        session = netsnmp.Session(DestHost=host,
                                  Version=2,
                                  Community=version_ops['community'],
                                  Retries=int(version_ops['retries']))
        return session

    def get_v3_session(self, host, version_ops):
        version_ops.setdefault('retries', 3)
        version_ops.setdefault('seclevel', 'authPriv')
        version_ops.setdefault('authproto', 'SHA')
        version_ops.setdefault('privproto', 'AES')
        session = netsnmp.Session(DestHost=host,
                                  Version=3,
                                  Retries=int(version_ops['retries']),
                                  SecLevel=version_ops['seclevel'],
                                  AuthProto=version_ops['authproto'],
                                  AuthPass=version_ops['authpass'],
                                  PrivProto=version_ops['privproto'],
                                  PrivPass=version_ops['privpass'],
                                  SecName=version_ops['secname'])
        return session

    def get_v3_session_from_config(self, host):
        cf = ConfigParser.ConfigParser()
        cf.read("/usr/lib/python2.7/site-packages/pyghmi/common/snmp-config.conf")
        v3_ops = {}
        v3_ops['retries'] = cf.get('v3-'+self.vendor, 'retries')
        v3_ops['community'] = cf.get('v3-'+self.vendor, 'community')
        v3_ops['seclevel'] = cf.get('v3-'+self.vendor, 'seclevel')
        v3_ops['authproto'] = cf.get('v3-'+self.vendor, 'authproto')
        v3_ops['authpass'] = cf.get('v3-'+self.vendor, 'authpass')
        v3_ops['privproto'] = cf.get('v3-'+self.vendor, 'privproto')
        v3_ops['privpass'] = cf.get('v3-'+self.vendor, 'privpass')
        v3_ops['secname'] = cf.get('v3-'+self.vendor, 'secname')

        session = netsnmp.Session(DestHost=host,
                                  Version=3,
                                  Retries=int(v3_ops['retries']),
                                  SecLevel=v3_ops['seclevel'],
                                  AuthProto=v3_ops['authproto'],
                                  AuthPass=v3_ops['authpass'],
                                  PrivProto=v3_ops['privproto'],
                                  PrivPass=v3_ops['privpass'],
                                  SecName=v3_ops['secname'])
        return session


    # SNMP get on a single OID. Returns value or None.
    def get(self, var, retry = 3):
        try:
            varlist = netsnmp.VarList(var)
        except TypeError:
            return None

        self.session.get(varlist)
        if varlist[0].val:
            return varlist[0].val
        else:
            while retry > 0:
                time.sleep(2/retry)
                self.session.get(varlist)
                retry -= 1
                if varlist[0].val:
                    return varlist[0].val
        return None

    # SNMP walk on an OID. Returns dict of {OID: value} pairs or None.
    def walk(self, var, retry = 3):
        try:
            varlist = netsnmp.VarList(var)
        except TypeError:
            return None

        result = self.session.walk(varlist)
        if result:
            return {x.tag: x.val for x in varlist if x.val}
        else:
            while retry > 0:
                time.sleep(2/retry)
                result = self.session.walk(varlist)
                retry -= 1
                if result:
                    return {x.tag: x.val for x in varlist if x.val}

        return None

    # Assemble a VarList of desired OIDs, run a single session,
    # then reassemble values into dict to return.
    def dictGet(self, indict):
        outdict = {}
        varlist = netsnmp.VarList()
        for key in indict:
            oid = indict[key]
            try:
                varbind = netsnmp.Varbind(oid)
            except TypeError:
                break
            # Using a key here that netsnmp library is unlikely to implement in the future.
            varbind.snmp_dict_key = key
            varlist.varbinds.append(varbind)

        self.session.get(varlist)

        for varbind in varlist:
            if varbind.val:
                outdict[varbind.snmp_dict_key] = varbind.val
        return outdict

    # Try walking the OID, then getting it.
    # Why walk first? Walk will succeed on more variations of misspelled OIDs,
    # Either with missing bits of hierarchy or a forgotten trailing dot.
    def walkGet(self, var, retry = 3):
        result = self.walk(var, retry)
        if not result:
            result = self.get(var, retry)

        return result

    # Takes dict of OIDs as input, returns dict with values.
    def populateDict(self, indata, keepValuesOnFailure=False):
        outdata = {}
        for key in indata:
            oid = indata[key]
            value = self.walkGet(oid)
            if value:
                outdata[key] = value
            elif keepValuesOnFailure:
                outdata[key] = oid
        return outdata

    # Takes list of OIDs as input, returns list of values.
    # When is this even useful?
    def populateList(self, indata, keepValuesOnFailure=False):
        outdata = []
        for oid in indata:
            value = self.walkGet(oid)
            if value:
                outdata.append(value)
            elif keepValuesOnFailure:
                outdata.append(oid)
        return outdata
