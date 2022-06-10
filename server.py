import myGlobals as mg
from common.utils import get_linenumber
#from datetime import datetime
import datetime
from dateutil.relativedelta import relativedelta
from flask import Flask
from flask_restful import Api, Resource
import inspect
import json
from multiprocessing import Process, Value
import os
import sys
import time

import config
from common.utils import myprint, isFileOlderThanXMinutes
import myMetServiceTides as mst

from resources.tides import TidesAPI, TodayTidesAPI

DATACACHE_AGING_IN_MINUTES = 60*24

apiResources = {
    "tides" : [
        (TidesAPI, '/mymetservicetides/api/v1.0/tides/<string:id>', 'tides'),
        (TodayTidesAPI, '/mymetservicetides/api/v1.0/tides', 'todaytides')
    ],
}

def foreverLoop(loop_on, dataCachePath, debug, updateDelay):
    config.DEBUG = debug

    class color:
        BOLD      = '\033[1m'
        UNDERLINE = '\033[4m'
        END       = '\033[0m'

    # Re-define myprint() as child process don't share globals :(
    def myprint(level, *args, **kwargs):
        import builtins as __builtin__
        
        if level <= config.DEBUG:
            __builtin__.print('%s%s()%s:' % (color.BOLD, inspect.stack()[1][3], color.END), *args, **kwargs)

    #myprint(1,'Started. Updating cache file every %d seconds (%s).' % (updateDelay, time.strftime('%H:%M:%S', time.gmtime(updateDelay))))
    myprint(1,'Started. Updating cache file every %d seconds (%s).' % (updateDelay, str(datetime.timedelta(seconds=updateDelay))))
    
    myprint(1,'Cache file: %s' % dataCachePath)
    
    while True:
        if loop_on.value == True:
            time.sleep(updateDelay)
            dt_now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            myprint(0, 'Reloading cache file from server at %s...' % (dt_now))
            res = mst.getTidesInfoFromMetServiceServer()
            if res:
                myprint(0, 'Failed to create/update local data cache')
            else:
                myprint(0, 'Data collected from server at %s' % (dt_now))            


def apiServerMain():

    dt_now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    mg.logger.info('Launching server at %s' % dt_now)
    myprint(1, 'Launching server...')
    
    app = Flask(__name__, static_url_path="")
    api = Api(app)

    for resourceName, resourceParamList in apiResources.items():
        for resource in resourceParamList:
            resApi = resource[0]
            resUrl = resource[1]
            resEndpoint = resource[2]
            myprint(1, 'Adding Resource:', resourceName, resApi, resUrl, resEndpoint)
            api.add_resource(resApi, resUrl, endpoint=resEndpoint)
            
    # Check if local cache file exists.
    # In this case, check its modification time and reload it from MetService server if too old.
    if os.path.isfile(mg.dataCachePath):
        if isFileOlderThanXMinutes(mg.dataCachePath, minutes=DATACACHE_AGING_IN_MINUTES):
            t = os.path.getmtime(mg.dataCachePath)
            dt = datetime.datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S')
            myprint(0, 'Cache file outdated (%s). Deleting and reloading from MetService server' % dt)
            # Remove data cache file and reload from server
            os.remove(mg.dataCachePath)
            res = mst.getTidesInfoFromMetServiceServer()
            if res:
                myprint(0, 'Failed to create local data cache. Aborting server')
                return(res)
    else:
        res = mst.getTidesInfoFromMetServiceServer()
        if res:
            myprint(0, 'Failed to create local data cache. Aborting server')
            return(res)
        
    recording_on = Value('b', True)
    p = Process(target=foreverLoop, args=(recording_on,
                                          mg.dataCachePath,
                                          config.DEBUG,
                                          config.UPDATEDELAY))
    p.start()  
    app.run(debug=True, use_reloader=False, port=5002) ##, host="0.0.0.0", port=6420)
    p.join()

    return(0)
