from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
from pysnmp.carrier.asynsock.dgram import udp, udp6
from pyasn1.codec.ber import decoder
from pysnmp.proto import api

class TrapServer(object):
    def __init__(self,bind_ipv4=None,port=162,bind_ipv6=None,notify_cb=None,udata=None):
        if bind_ipv4 is None and bind_ipv6 is None:
            raise Exception('Need ipv4 or ipv6 address')
        self.ipv4_addr=bind_ipv4
        self.ipv6_addr=bind_ipv6
        self.port=port
        self.nofity=notify_cb
        self.udata=udata
        
        self.mapping={
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.1':{
            'name':'seq',
            'field':'number',
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.2':{
            'name':'event',
            'field':'string'
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.3':{
            'name':'description',
            'field':'string'
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.4':{
             'name':'level',
             'field':'number',
             'fun':self._parse_level
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.5':{
             'name':'eventcode',
             'field':'string'
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.6':{
              'name':'eventdata1',
              'field':['number','string']
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.7':{
                'name':'eventdata2',
                'field':['string','number']
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.8':{
                'name':'server_id',
                'field':'string'
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.9':{
                'name':'trap_location',
                'field':'string'
            },
            '1.3.6.1.4.1.2011.2.235.1.1.500.1.10':{
                'name':'trap_time',
                'field':'string'
            }
        }
        
        self.level_str=["ok",'minor','major','critical']
    
    
    def _parse_level(self,level):
        level=int(level)
        if level < 0 or level >= len(self.level_str):
            level=3
        return self.level_str[level]
    
    def _split_dict(self,lines):
        p={}
        for l in lines.split('\n'):
            key_value=l.split('=')
            if len(key_value) >=2:
                p[key_value[0].strip()]="=".join(key_value[1:]).strip()
        return p
    
    @staticmethod
    def _get_oid_value(var_format,var_property):
        key=var_format['field']
        if isinstance(var_format['field'],list):
            for field in var_format['field']:
                if field in var_property:
                    key = field
                    break
        if 'fun' in var_format:
            return var_format['fun'](var_property[key])
        else:
            return var_property[key]
            
    def _parse_event(self,src_addr,oid,var_binds):
        """
        {
        'origin': ('10.100.17.135', 53824), 
        'server_id': 'sever identity test', 
        'eventdata1': '0', 
        'description': 'test event', 
        'seq': '33', 
        'level': 'minor', 
        'event_oid': '1.3.6.1.4.1.2011.2.235.1.1.500.10.256', 
        'eventcode': '0x00000001', 
        'trap_location': 'server room', 
        'eventdata2': '0', 
        'event': 'test subject--info1.info2', 
        'trap_time': '1970-01-01 00:00:00'
        }
        """
        result={'origin':src_addr,'event_oid':oid}
        
        from pyasn1.type import base
        NoValue = base.NoValue
        noValue = NoValue()
        
        for var in var_binds:
            var_property={}
            for idx, componentValue in enumerate(var._componentValues):
                if componentValue is not noValue:
                    if var.componentType:
                        name=var.componentType.getNameByPosition(idx)
                    else:
                        name=var._dynamicNames.getNameByPosition(idx)
                    if name =='name':
                        value=componentValue.prettyPrint(0)
                        var_property[name]=value.strip()
                    else:
                        var_property.update(self._split_dict(componentValue.prettyPrint(0)))
            if var_property['name'] not in self.mapping:
                print "parse error"
                continue
            var_format = self.mapping[var_property['name']]
            oid_var=var_format['name']
            oid_value= TrapServer._get_oid_value(var_format,var_property)
            result[oid_var]=oid_value
        #notify xlca
        print(result)
        return result
        
    def _event_handle(self,transportDispatcher, transportDomain, transportAddress, wholeMsg):
        while wholeMsg:
            msgVer = int(api.decodeMessageVersion(wholeMsg))
            if msgVer in api.protoModules:
                pMod = api.protoModules[msgVer]
            else:
                print('Unsupported SNMP version %s' % msgVer)
                return
            reqMsg, wholeMsg = decoder.decode(
                wholeMsg, asn1Spec=pMod.Message(),
            )
            reqPDU = pMod.apiMessage.getPDU(reqMsg)
            if reqPDU.isSameTypeWith(pMod.TrapPDU()):
                if msgVer == api.protoVersion1:
                    oid=pMod.apiTrapPDU.getEnterprise(reqPDU).prettyPrint()
                    varBinds = pMod.apiTrapPDU.getVarBindList(reqPDU)
                else:
                    oid='unkown'
                    varBinds = pMod.apiPDU.getVarBindList(reqPDU)
            self._parse_event(transportAddress,oid, varBinds)
        return wholeMsg
    
    def start(self):
        transportDispatcher = AsynsockDispatcher()
        transportDispatcher.registerRecvCbFun(self._event_handle)

        if self.ipv4_addr:
            transportDispatcher.registerTransport(
                udp.domainName, udp.UdpSocketTransport().openServerMode((str(self.ipv4_addr), self.port))
                )
        if self.ipv6_addr:
            transportDispatcher.registerTransport(
                udp6.domainName, udp6.Udp6SocketTransport().openServerMode((str(self.ipv6_addr), self.port))
                )

        transportDispatcher.jobStarted(1)
        try:
            # Dispatcher will never finish as job#1 never reaches zero
            transportDispatcher.runDispatcher()
        except:
            transportDispatcher.closeDispatcher()
            raise
    def stop(self):
        pass
    
    @staticmethod
    def do_unit_test(ip='10.100.206.223'):
        TrapServer(ip).start()


if __name__ == "__main__":
    TrapServer.do_unit_test()

