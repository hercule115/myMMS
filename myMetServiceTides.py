#!/usr/bin/env python

# Tool to get tides information from metservice.intnet.mu

# Import or build our configuration. Must be FIRST
try:
    import config	# Shared global config variables (DEBUG,...)
except:
    #print('config.py does not exist. Generating...')
    import initConfig	# Check / Update / Create config.py module
    initConfig.initConfiguration()
    
# Import generated module
try:
    import config
except:
    print('config.py initialization has failed. Exiting')
    sys.exit(1)
    
import argparse
import builtins as __builtin__
import datetime
import inspect
import json
import logging
import os
import sys
import time

import myGlobals as mg
from common.utils import myprint, module_path, get_linenumber, color
import tides as mst

# Arguments parser
def parse_argv():
    desc = 'Get tides information from metservice.intnet.mu server'

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-s", "--server",
                        action="store_true",                        
                        dest="server",
                        default=False,
                        help="run in server mode (as a Web Service)")
    parser.add_argument("-d", "--debug",
                        action="count",
                        dest="debug",
                        default=0,
                        help="print debug messages (to stdout)")
    parser.add_argument("-v", "--verbose",
                        action="store_true", dest="verbose", default=False,
                        help="provides more information")
    parser.add_argument('-f', '--file',
                        dest='logFile',
                        const='',
                        default=None,
                        action='store',
                        nargs='?',
                        metavar='LOGFILE',
                        help="write debug messages to FILE")
    parser.add_argument("-C", "--cache",
                        action="store_true",
                        dest="useCache",
                        default=True,
                        help="Use local cache if available (default=True)")
    parser.add_argument('-D', '--delay',
                        dest='updateDelay',
                        default=86400,
                        type=int,
                        action='store',
                        nargs='?',
                        metavar='DELAY',
                        help="update interval in seconds (Server mode only)")
    parser.add_argument("-I", "--info",
                        action="store_true", dest="version", default=False,
                        help="print version and exit")

    parser.add_argument('tidesDate',
                        action='store',
                        nargs='?',
                        metavar='DATE',
                        help='Tides Date to show (ddmmyy)')

    args = parser.parse_args()
    return args


####
def import_module_by_path(path):
    name = os.path.splitext(os.path.basename(path))[0]
    if sys.version_info[0] == 2:
        import imp
        return imp.load_source(name, path)
    elif sys.version_info[:2] <= (3, 4):
        from importlib.machinery import SourceFileLoader
        return SourceFileLoader(name, path).load_module()
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


#
# Import module. Must be called *after* parsing arguments
#
def importModule(moduleDirPath, moduleName, name):
    modulePath = os.path.join(moduleDirPath, moduleName)
    mod = import_module_by_path(modulePath)
    globals()[name] = mod


####
def main():

    args = parse_argv()

    if args.version:
        print('%s: version %s' % (sys.argv[0], mg.VERSION))
        sys.exit(0)

    config.SERVER    = args.server
    config.VERBOSE   = args.verbose
    config.USE_CACHE = args.useCache
    config.DEBUG     = args.debug
    
    if config.DEBUG:
        myprint(1, 'Running in DEBUG mode (level=%d)' % config.DEBUG)
        myprint(1,
                'config.SERVER =', config.SERVER,
                'config.VERBOSE =', config.VERBOSE,
                'config.USE_CACHE =', config.USE_CACHE)
        
    if args.logFile == None:
        #print('Using stdout')
        pass
    else:
        if args.logFile == '':
            config.LOGFILE = "mymetservicetides-debug.txt"
        else:
            config.LOGFILE = args.logFile
        mg.configFilePath = os.path.join(mg.moduleDirPath, config.LOGFILE)
        print('Using log file: %s' % mg.configFilePath)
        try:
            sys.stdout = open(mg.configFilePath, "w")
            sys.stderr = sys.stdout            
        except:
            print('Cannot create log file')

    if args.server:
        if args.updateDelay:
            config.UPDATEDELAY = args.updateDelay
        else:
            config.UPDATEDELAY = 86400 # seconds

    if config.SERVER:
        import server as msas
        if config.DEBUG:
            mg.logger.info('server imported (line #%d)' % get_linenumber())

        myprint(0, 'Running in Server mode. Update interval: %d seconds (%s)' % (config.UPDATEDELAY, str(datetime.timedelta(seconds=config.UPDATEDELAY))))
        res = msas.apiServerMain()	# Never returns
        myprint(1, 'API Server exited with code %d' % res)
        sys.exit(res)

    #
    # Standalone mode
    #
    if not args.tidesDate:
        tidesDate = datetime.datetime.now().strftime('%d%m%y')	# Today's tides
    else:
        if 'init' in args.tidesDate:
            initConfiguration()
            print('Config initialized. Re-run the command.')
            sys.exit(0)

        tidesDate = args.tidesDate
        # Check for a valid date
        try:
            dt = datetime.datetime.strptime(tidesDate, '%d%m%y')
        except:
            myprint(0, 'Invalid tides date argument %s' % tidesDate)
            sys.exit(1)
        else:
            tidesDate = dt.strftime('%d%m%y')

    if config.USE_CACHE:
        # Load data from local cache
        info = mst.loadDataFromCacheFile()
        if not info:
            myprint(1, 'Failed to load tides data from local cache file. Retrieving data from server')
            # Read data from server
            res = mst.getTidesInfoFromMetServiceServer()
            if res:
                myprint(0, 'Failed to create/update local data cache')
                sys.exit(res)

        # Display information
        res = mst.showTidesInfo(tidesDate)
        if res:
            myprint(0, 'Unable to retrieve tides information')
            sys.exit(1)

        if args.logFile and args.logFile != '':
            sys.stdout.close()
            sys.stderr.close()

        sys.exit(0)

    # Read data from server
    res = mst.getTidesInfoFromMetServiceServer()    
    if res:
        myprint(0, 'Failed to retrieve tides information from server')
        sys.exit(res)

    t = os.path.getmtime(mg.dataCachePath)
    dt = datetime.datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S')
    myprint(1, 'Cache file updated. Last modification time: %s (%d)' % (dt,t))

    # Display information
    res = mst.showTidesInfo(tidesDate)
    if res:
        myprint(0, 'Unable to retrieve tides information')
        sys.exit(1)

    if args.logFile and args.logFile != '':
        sys.stdout.close()
        sys.stderr.close()
        
# Entry point    
if __name__ == "__main__":

    dt_now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    logging.basicConfig(filename='myMetServiceTides-ws.log', level=logging.INFO)
    mg.logger = logging.getLogger(__name__)
    mg.logger.info('Running at %s. Args: %s' % (dt_now, ' '.join(sys.argv)))
    
    # Absolute pathname of directory containing this module
    mg.moduleDirPath = os.path.dirname(module_path(main))

    # Absolute pathname of data cache file
    mg.dataCachePath = os.path.join(mg.moduleDirPath, '%s' % (mg.DATA_CACHE_FILE))
    
    # Let's go
    main()
