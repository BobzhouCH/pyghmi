from pyghmi.common import snmp

class TestSNMP(object):
    '''
    Test snmp get(oid), getlist(oidList)
    '''
    def __init__(self, hostIP, snmp_version=2, snmp_ops={}):
        self.snmp_version = snmp_version
        self.snmp_opts = snmp_ops
        self.session = snmp.Connection(hostIP, self.snmp_version, **self.snmp_opts)

    def test(self):
        oidList={"cpu_cooperation":".1.3.6.1.4.1.2011.2.235.1.1.15.50.1.2.1", "cpu.2":".1.3.6.1.4.1.2011.2.235.1.1.15.50.1.2.2", "cpu.3":".1.3.6.1.4.1.2011.2.235.1.1.16.50.1.4.1"}
        print self.session.get(".1.3.6.1.4.1.2011.2.235.1.1.15.50.1.2.1")
	print self.session.dictGet(oidList)
	print self.session.walk(".1.3.6.1.4.1.2011.2.235.1.1.15.50.1")
	print self.session.walkGet(".1.3.6.1.4.1.2011.2.235.1.1.15.50.1")

version_ops={}
version_ops['retries'] = 3
version_ops['community'] = "public"
version_ops['seclevel'] = "authPriv"
version_ops['authproto'] = "SHA"
version_ops['authpass'] = "Admin@9000"
version_ops['privproto'] = "AES"
version_ops['privpass'] = "Admin@9000"
version_ops['secname'] = "Administrator"

print version_ops

a = TestSNMP(hostIP="10.100.17.135", snmp_version=3,snmp_ops=version_ops)
a.test()
