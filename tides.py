from bs4 import BeautifulSoup
from datetime import datetime, date
import json
import os
import pytz
import requests
import time
import shutil
import sys
import unicodedata

import myGlobals as mg
import httpHeaders as hh
import config

from common.utils import myprint, color, dumpToFile, dumpJsonToFile, dumpListToFile, dumpListOfListToFile, bubbleSort, isFileOlderThanXMinutes

class color:
    PURPLE    = '\033[95m'
    CYAN      = '\033[96m'
    DARKCYAN  = '\033[36m'
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    GREYED    = '\033[2m'
    ITALIC    = '\033[3m'
    UNDERLINE = '\033[4m'
    STRIKETHRu = '\033[9m'
    END       = '\033[0m'


# Dictionary containing the HTTP requests to send to the server
METSERVICE_HTTP_REQUESTS = {
    "initialPage" : {
        "info" : "Conect to metservice.intnet.mu and get index page to retrieve tides table",
        "rqst" : {
            "type" : 'GET',
            "url"  : 'http://metservice.intnet.mu/sun-moon-and-tides-tides-mauritius.php',
            "headers" : {
            },
        },
        "resp" : {
            "code" : 200,
            "dumpResponse" : 'metservice.intnet.mu.html',
            "updateCookies" : False,                
        },
        "returnText" : True,
    },
}

cacheUpdated = False
            
class MetServiceTides:
    def __init__(self, session):
        self._session  = session
        # Dict to save cookies from server
        self._cookies = dict()
        
    def getTidesInformation(self):
        # Execute request to get the tides raw information
        respText = self._executeRequest('initialPage')
        if 'ErRoR' in respText:
            myprint(1, 'Error retrieving information from server')
            return -1

        # Parse returned information. Create/Update local cache file
        info = self._parseTidesPage(respText)
        myprint(2, json.dumps(info, indent=4))
        return 0
    
    # Build a string containing all cookies passed as parameter in a list 
    def _buildCookieString(self, cookieList):
        cookieAsString = ''
        for c in cookieList:
            # Check if cookie exists in our dict
            if c in self._cookies:
                cookieAsString += '%s=%s; ' % (c, self._cookies[c])
            else:
                myprint(1,'Warning: Cookie %s not found.' % (c))
        return(cookieAsString)

    # Update our cookie dict
    def _updateCookies(self, cookies):
        for cookie in self._session.cookies:
            if cookie.value == 'undefined' or cookie.value == '':
                myprint(2,'Skipping cookie with undefined value %s' % (cookie.name))
                continue
            if cookie.name in self._cookies and self._cookies[cookie.name] != cookie.value:
                myprint(1,'Updating cookie:', cookie.name)
                self._cookies[cookie.name] = cookie.value
            elif not cookie.name in self._cookies:
                myprint(1,'Adding cookie:', cookie.name)
                self._cookies[cookie.name] = cookie.value
            else:
                myprint(2,'Cookie not modified:', cookie.name)                

    def _executeRequest(self, name):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        rqst = METSERVICE_HTTP_REQUESTS[name]
        myprint(1, '%s: Executing request "%s": %s' % (dt_now, name, rqst["info"]))
        myprint(2, json.dumps(rqst, indent=4))

        hdrs = hh.HttpHeaders()

        for k,v in rqst["rqst"]["headers"].items():
            if k == "Cookie":
                if 'str' in str(type(v)):	# Cookie is a string
                    cookieAsString = v
                else:				# Cookie is a list of cookies
                    assert('list' in str(type(v)))
                    cookieAsString = self._buildCookieString(v)

                # Add extra Cookie if requested
                if "extraCookie" in rqst["rqst"]:
                    cookieAsString += rqst["rqst"]["extraCookie"]
                hdrs.setHeader('Cookie', cookieAsString)
            else:
                hdrs.setHeader(k, v)

        rqstType = rqst["rqst"]["type"]
        rqstURL  = rqst["rqst"]["url"]
        try:
            rqstStream = rqst["rqst"]["stream"]
        except:
            rqstStream = False

        try:
            csvStream = rqst["rqst"]["csv"]
        except:
            csvStream = False
            
        myprint(1,'Request type: %s, Request URL: %s' % (rqstType, rqstURL))
        myprint(2,'Request Headers:', json.dumps(hdrs.headers, indent=2))

        errFlag = False
        
        if rqstType == 'GET':
            try:
                myprint(2,'Request Stream:', rqstStream, 'CSV Stream:', csvStream)
                r = self._session.get(rqstURL, headers=hdrs.headers, stream=rqstStream)
            except requests.exceptions.RequestException as e:
                errFlag = True
                
        elif rqstType == 'POST':
            rqstPayload  = rqst["rqst"]["payload"]
            myprint(1,"payload=%s" % rqstPayload)
            try:
                r = self._session.post(rqstURL, headers=hdrs.headers, data=rqstPayload)
            except requests.exceptions.RequestException as e:
                errFlag = True
                
        else:	# OPTIONS
            assert(rqstType == 'OPTIONS')
            try:
                r = self._session.options(rqstURL, headers=hdrs.headers)
            except requests.exceptions.RequestException as e:
                errFlag = True

        if errFlag:
            errorMsg = 'ErRoR while retrieving information: %s' % (e) # Dont't change the cast for ErRoR  !!!!
            myprint(0, errorMsg)
            return errorMsg

        myprint(1,'Response Code:',r.status_code)

        if r.status_code != rqst["resp"]["code"]:
            myprint(1,'Invalid Status Code: %d (expected %d). Reason: %s' % (r.status_code, rqst["resp"]["code"], r.reason))
            if rqst["returnText"]:
                return ''
            else:
                return

        myprint(2,'Response Headers:', json.dumps(dict(r.headers), indent=2))
        
        # Optional parameter "dumpResponse"
        try:
            outputFile = os.path.join(mg.moduleDirPath, rqst["resp"]["dumpResponse"])
            if rqstStream:
                if csvStream:
                    with open(outputFile, 'wb') as f:
                        for line in r.iter_lines():
                            f.write(line+'\n'.encode())
                else:
                    r.raw.decode_content = True
                    myprint(1, "Saving raw text to %s" % outputFile)
                    with open(outputFile, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
            else:
                myprint(1, "dumpToFile(%s, r.text)" % outputFile)
                dumpToFile(outputFile, r.text)
        except:
            myprint(1, 'Error while saving response -or- No "dumpResponse" requested')
            pass
        
        # Update cookies
        if rqst["resp"]["updateCookies"]:
            self._updateCookies(r.cookies)
            
        if rqst["returnText"]:
            return r.text


    def _parseTidesPage(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        data = []

        # Assuming the first table *IS* the tides table :(
        table = soup.find('table')
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele]) # Get rid of empty values

        # Get month name from first element of the first list
        myprint(1,data[0][0])
        
        monthName = data[0][0].replace("'", "").split()[0]
        myprint(1, monthName)
        
        year = date.today().year

        monthYear = '%s %s' % (monthName, year)
        mmyy = datetime.strptime(monthYear, '%B %Y').strftime('%m%y')
        myprint(1, monthYear, mmyy)

        #currMonthYear = mauritiusLocalMonthYear()         # current monthName and Year
        #myprint(1, 'Current Month Year', currMonthYear)
        currMonth = mauritiusLocalMonth()         # current monthName
        myprint(1, 'Current Month', currMonth)
        
        oneDayDict = dict()
        oneMonthDict = dict()
        
        # Parse first month (current month) only
        for oneDayList in data:

            myprint(2, oneDayList, len(oneDayList))
            
            #if len(oneDayList) == 1 and oneDayList[0] != currMonthYear:
            if not oneDayList or len(oneDayList) == 1 and oneDayList[0] != currMonth:
                myprint(1, 'End of month %s: %d entries in dict' % (monthYear,len(oneMonthDict)))
                break

            if oneDayList[0].isnumeric():	# skip header lines
                oneDayDict.clear()
                k = format(int(oneDayList[0]), '02d') + mmyy  # date (ddmmyy) as key
                oneMonthDict[k] = [unicodedata.normalize("NFKD", fld).lstrip() for fld in oneDayList]                
        myprint(1, oneMonthDict)

        # Update local cache file
        dumpJsonToFile(mg.DATA_CACHE_FILE, oneMonthDict)
        return oneMonthDict


####
# Load data from local cache. If cache is older than delay, return None to force a reload
def loadDataFromCacheFile():

    if not os.path.isfile(mg.dataCachePath):	# Cache file does not exists
        return None
    
    if isFileOlderThanXMinutes(mg.dataCachePath, minutes=config.UPDATEDELAY):
        if config.DEBUG:
            t = os.path.getmtime(mg.dataCachePath)
            dt = datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S')
            myprint(1, f'Cache file outdated {dt}. Deleting and reloading from MetService server')
        # Remove data cache file and reload from server
        os.remove(mg.dataCachePath)
        return None # Force a reload

    myprint(1, 'Loading data from local cache')

    try:
        with open(mg.dataCachePath, 'r') as infile:
            data = infile.read()
            res = json.loads(data)
            return res
    except Exception as error: 
        myprint(0, f"Unable to open data cache file {mg.dataCachePath}")
        return None


def getTidesInfoFromMetServiceServer():
    global cacheUpdated
    
    with requests.session() as session:
        # Create connection with MetService server
        mst = MetServiceTides(session)
        # Get information from server
        res = mst.getTidesInformation()
        if not res:
            myprint(1, 'Cache file updated')
            cacheUpdated = True
        return res


def getTidesInfo(tidesDate):

    # Load data from local cache
    data = loadDataFromCacheFile()
    if not data:
        myprint(0, 'Unable to retrieve tides information from cache file')
        return None

    # Check data format
    try:
        day,firstHTT,firstHTH,secHTT,secHTH,firstLTT,firstLTH,secLTT,secLTH = data[tidesDate]
    except:
        myprint(0, f'Unable to retrieve tides information for {tidesDate}')
        return None
    else:
        return data[tidesDate]

    
def mauritiusLocalTime():

    local_dt = datetime.now()	# Local datetime
    
    mauritius = pytz.timezone('Indian/Mauritius')
    mauritius_dt = local_dt.astimezone(mauritius)
    myprint(1, 'Mauritius Local Time:', mauritius_dt.strftime('%d/%m/%Y %H:%M:%S %Z%z'))
    return mauritius_dt.time()

def mauritiusLocalMonthYear():

    local_dt = datetime.now()	# Local datetime
    
    mauritius = pytz.timezone('Indian/Mauritius')
    mauritius_dt = local_dt.astimezone(mauritius)
    my = mauritius_dt.strftime('%B %Y')
    myprint(1, 'Mauritius Local Month Year:', my)
    return my

def mauritiusLocalMonth():

    local_dt = datetime.now()	# Local datetime
    
    mauritius = pytz.timezone('Indian/Mauritius')
    mauritius_dt = local_dt.astimezone(mauritius)
    m = mauritius_dt.strftime('%B')
    myprint(1, 'Mauritius Local Month:', m)
    return m

def mauritiusLocalDate():

    local_dt = datetime.now()	# Local datetime
    
    mauritius = pytz.timezone('Indian/Mauritius')
    mauritius_dt = local_dt.astimezone(mauritius)
    myprint(1, 'Mauritius Local Date:', mauritius_dt.strftime('%d/%m/%Y %H:%M:%S %Z%z'))
    return mauritius_dt.date()

def showTidesInfo(tidesDate):

    # Load data from local cache
    data = loadDataFromCacheFile()
    if not data:
        myprint(1, 'Failed to load tides data from local cache file. Retrieving data from server')
        # Read data from server
        res = getTidesInfoFromMetServiceServer()
        if res:
            myprint(0, 'Failed to create/update local data cache')
            return -1

        data = loadDataFromCacheFile()
        # Assuming no error
        
        if config.DEBUG:
            t = os.path.getmtime(mg.dataCachePath)
            dt = datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S')
            myprint(1, f'Cache file updated. Last modification time: {dt}')

    labels = ['Date',
             '1st High Tide Time',
             '1st High Tide Height',
             '2nd High Tide Time',
             '2nd High Tide Height',
             '1st Low Tide Time',
             '1st Low Tide Height',
             '2nd Low Tide Time',
             '2nd Low Tide Height']

    # example: ["5", "03:17", "54", "18:03", "49", "10:02", "26", "-", "-"]

    try:
        day,firstHTT,firstHTH,secHTT,secHTH,firstLTT,firstLTH,secLTT,secLTH = data[tidesDate]
    except:
        myprint(0, f'Invalid/Not found input date: {tidesDate}')
        return -1

    if config.VERBOSE:
        s = "{B}Tides for date: {DATE}{E} {CA}".format(
            B=color.BOLD,
            E=color.END,
            CA="(+)" if cacheUpdated else "",
            DATE=datetime.strptime(tidesDate, '%d%m%y').strftime("%a %d %b, %Y"))
        print(s)
        
        # build a list of tuples, each tuple containing: (time of tide, height of tide, label)
        l = list()
        for i in range(1, 9, 2):	# Skip over date field and height
            if data[tidesDate][i] == '-':
                continue		# remove phantom tide
            l.append((data[tidesDate][i], data[tidesDate][i+1], labels[i]))
            
        # Bubble sort the list by ascending time
        bubbleSort(l)
        
        # If reqesting today's tides (using Mauritius time), highlight next tide time
        #if datetime.strptime(tidesDate, '%d%m%y').date() == datetime.today().date():
        if datetime.strptime(tidesDate, '%d%m%y').date() == mauritiusLocalDate():
            timeNowInMauritius = mauritiusLocalTime()
            myprint(1, "Today's local date:", datetime.now(), "Mauritius local time", timeNowInMauritius)

            nextTideNotFound = True
            for ele in l:
                t = datetime.strptime(ele[0], '%H:%M').time()
                if t >= timeNowInMauritius:
                    if nextTideNotFound:
                        nextTideNotFound = False
                        s = "{L:<19}: {B}{T:6}{E}({H}) {B}*{E}".format(L=ele[2], T=ele[0], H=ele[1], B=color.BOLD, E=color.END)
                    else:
                        s = "{L:<19}: {T:6}({H})".format(L=ele[2], T=ele[0], H=ele[1], B=color.BOLD, E=color.END)
                else:
                    #s = "{L:<19}: {T:6}({H})".format(L=ele[2], T=ele[0], H=ele[1])
                    s = "{I}{L:<19}: {T:6}({H}){E}".format(I=color.ITALIC, E=color.END, L=ele[2], T=ele[0], H=ele[1])
                print(s)
        elif datetime.strptime(tidesDate, '%d%m%y').date() > mauritiusLocalDate():
            # Tides request for a day in the future
            for ele in l:
                s = "{L:<19}: {T:6}({H})".format(L=ele[2], T=ele[0], H=ele[1])
                print(s)
        else:	# Tides request for a past day
            for ele in l:
                s = "{G}{L:<19}: {T:6}({H}){E}".format(G=color.GREYED, E=color.END, L=ele[2], T=ele[0], H=ele[1])
                print(s)
    else:	# Short output
        print(data[tidesDate])
    return 0
