import netsnmp

class Trap(object):
    def __init__(self,ops=None,trap_index=1):
        if ops is None:
            ops = self._get_default_ops()
        self.ops=ops
        self.trap_index=trap_index
        #
        self.tag = "1.3.6.1.4.1"
        self.trap_receiver_address="2011.2.235.1.1.4.50.1.3.%s"
        self.trap_receiver_enable= "2011.2.235.1.1.4.50.1.2.%s"
        #
    def _get_default_ops(self):
        version_ops={}
        version_ops['retries'] = 3
        version_ops['community'] = "public"
        version_ops['seclevel'] = "authPriv"
        version_ops['authproto'] = "SHA"
        version_ops['authpass'] = "Admin@9000"
        version_ops['privproto'] = "AES"
        version_ops['privpass'] = "Admin@9000"
        version_ops['secname'] = "Administrator"
        return version_ops

    def _format(self,f):
        return f % self.trap_index

    def _set_oid(self,snmp_agent,oid):
        try:
            return netsnmp.snmpset(oid,DestHost=snmp_agent,
                Version=3,
                Retries=int(self.ops['retries']),
                SecLevel=self.ops['seclevel'],
                AuthProto=self.ops['authproto'],
                AuthPass=self.ops['authpass'],
                PrivProto=self.ops['privproto'],
                PrivPass=self.ops['privpass'],
                SecName=self.ops['secname'])
        except Exception as e :
            print e
            raise e

    def _get_oid(self, snmp_agent, oid):
        try:
            return netsnmp.snmpget(oid, DestHost=snmp_agent,
                                   Version=3,
                                   Retries=int(self.ops['retries']),
                                   SecLevel=self.ops['seclevel'],
                                   AuthProto=self.ops['authproto'],
                                   AuthPass=self.ops['authpass'],
                                   PrivProto=self.ops['privproto'],
                                   PrivPass=self.ops['privpass'],
                                   SecName=self.ops['secname'])
        except Exception as e:
            print e
            raise e

    def set_trap_target(self, snmp_agent, target="1.1.1.1"):
        enable_oid = netsnmp.Varbind(self.tag, self._format(self.trap_receiver_enable), '2', 'INTEGER')
        rev_addr = netsnmp.Varbind(self.tag, self._format(self.trap_receiver_address), target, 'OCTETSTR')
        self._set_oid(snmp_agent, enable_oid)
        self._set_oid(snmp_agent, rev_addr)
##
    def get_trap_traget(self, snmp_agent):
        rev_addr = netsnmp.Varbind(self.tag, self._format(self.trap_receiver_address), None, 'OCTETSTR')
        addr = self._get_oid(snmp_agent, rev_addr)
        return addr[0]

    @staticmethod
    def do_unit_test():
        Trap().set_trap_target('10.100.17.135')
        obj = Trap().get_trap_traget('10.100.17.135')
        print obj

class EventHandler(object):
    pass

if __name__ == "__main__":
    Trap.do_unit_test()
