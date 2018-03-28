
from pyghmi.common.ipmi import IPMI




class FRU(object):

    def __init__(self, host, user, password):
        self.info = {}
        self.ipmi_session = IPMI(host,user,password)
        self.get_info()

    def get_info(self):
        ###### Chassiss info######
        inf = self.info
        fru_output = self.ipmi_session.run_command('fru list')
        inf['Chassis type'] = fru_output[1].split(':')[1].strip()
        inf['Chassis part number'] = ''
        inf['Chassis serial number'] = ''

        ###### Board info######
        inf['Board manufacture date'] = ''
        inf['Board manufacturer'] = fru_output[3].split(':')[1].strip()
        inf['Board product name'] = fru_output[4].split(':')[1].strip()
        inf['Board serial number'] = fru_output[5].split(':')[1].strip()
        inf['Board model'] = ''

        ###### Manufacturer info######
        inf['Manufacturer'] = fru_output[15].split(':')[1].strip()
        inf['Product name'] = fru_output[16].split(':')[1].strip()
        inf['Model']  = ''
        inf['Hardware Version'] = ''
        inf['Serial Number'] = fru_output[18].split(':')[1].strip()
        inf['Asset Number'] = ''