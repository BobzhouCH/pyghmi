
from pyghmi.common.ipmi import IPMI_lanplus as IPMI



class FRU(object):

    def __init__(self, host, user, password, fru_id=0):
        self.info = {}
        self.ipmi_session = IPMI(host,user,password)
        self.fru_id = fru_id
        self.get_info()

    def get_info(self):
        ###### Chassiss info######
        inf = self.info
        fru_output = self.ipmi_session.run_command('fru list' + str(self.fru_id))
        inf['Chassis type'] = ''
        inf['Chassis part number'] = ''
        inf['Chassis serial number'] = ''

        ###### Board info######
        inf['Board manufacture date'] = fru_output[0].split(':')[1].strip()
        inf['Board manufacturer'] = fru_output[1].split(':')[1].strip()
        inf['Board product name'] = fru_output[2].split(':')[1].strip()
        inf['Board serial number'] = fru_output[3].split(':')[1].strip()
        inf['Board model'] = ''

        ###### Manufacturer info######
        inf['Manufacturer'] = fru_output[5].split(':')[1].strip()
        inf['Product name'] = fru_output[6].split(':')[1].strip()
        inf['Model'] = fru_output[6].split(':')[1].strip()
        inf['Hardware Version'] = fru_output[7].split(':')[1].strip()
        inf['Serial Number'] = fru_output[8].split(':')[1].strip()
        inf['Asset Number'] = fru_output[9].split(':')[1].strip()
