# Some glogal constants
VERSION = '1.0'
DATA_CACHE_FILE = '.tides.metservice.json'
LOCAL_TAB_FILE = '.tides.metservice.intnet.mu'

# Global variables
logger = None
moduleDirPath = ''
dataCachePath = ''
prevModTime = 0

# Config parameters
mandatoryFields = []
optionalFields  = [('d','DEBUG', 0),
                   ('b','VERBOSE', 'False'),
                   ('s','LOGFILE')]
