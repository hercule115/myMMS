# Some glogal constants
VERSION = '1.0'
DATA_CACHE_FILE = '.tides.metservice.json'

# Global variables
logger = None
moduleDirPath = ''
dataCachePath = ''

# Config parameters
mandatoryFields = []
optionalFields  = [('d','DEBUG', 0),
                   ('b','VERBOSE', 'False'),
                   ('s','LOGFILE')]
