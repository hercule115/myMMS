from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import requests
import time
import shutil
import sys
import unicodedata

import myGlobals as mg
import httpHeaders as hh
import config

from common.utils import myprint, color, dumpToFile, dumpJsonToFile, dumpListToFile, dumpListOfListToFile, bubbleSort

class color:
    PURPLE    = '\033[95m'
    CYAN      = '\033[96m'
    DARKCYAN  = '\033[36m'
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
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
            #"dumpResponse" : 'metservice.intnet.mu.html',
            "updateCookies" : False,                
        },
        "returnText" : True,
    },
}


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

        # Parse returned information
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

        #print(soup.table)

        # Assuming the first table *IS* the tides table :(
        table = soup.find('table')
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele]) # Get rid of empty values

        #print(data)
        # Save lists to text file
        dumpListOfListToFile(mg.LOCAL_TAB_FILE, data)

        if not os.path.isfile(mg.LOCAL_TAB_FILE):
            myprint(1, 'Local chart file does not exist...')
            return None
            
        myprint(1, 'Local chart file exists. Parsing...')
        # empty list to read list from a file
        allLines = list()

        # open file and read the content in a list
        with open(mg.LOCAL_TAB_FILE, 'r') as fp:
            for line in fp:
                # remove linebreak from the current line
                # linebreak is the last character of each line
                x = line[1:-2]

                # add current item to the list
                allLines.append(x)

        monthYear = allLines[0].replace("'", "")
        mmyy = datetime.strptime(monthYear, '%B %Y').strftime('%m%y')

        myprint(1, monthYear, mmyy)

        oneDayDict = dict()
        oneMonthDict = dict()
        
        # Parse first month (current) only
        for oneLine in allLines[0:35]:	# enough for one month...
            oneLineList = [i.replace("'", "") for i in list(oneLine.split(","))]
            myprint(2, oneLineList)

            if oneLineList[0].isnumeric():	# skip header lines
                oneDayDict.clear()
                k = format(int(oneLineList[0]), '02d') + mmyy  # date (ddmmyy) as key
                oneMonthDict[k] = oneLineList
                
            if oneLineList[0] == '':
                myprint(1, 'End of month %s: %d entries in dict' % (monthYear,len(oneMonthDict)))
                break
        myprint(1, oneMonthDict)

        # Update local cache file
        dumpJsonToFile(mg.DATA_CACHE_FILE, oneMonthDict)
        return oneMonthDict


####
def loadDataFromCacheFile():

    try:
        with open(mg.dataCachePath, 'r') as infile:
            data = infile.read()
            res = json.loads(data)
            return res
    except Exception as error: 
        myprint(0, f"Unable to open data cache file {mg.dataCachePath}")
        return None


def getTidesInfoFromMetServiceServer():
        
    with requests.session() as session:
        # Create connection with MetService server
        mst = MetServiceTides(session)
        # Get information from server
        res = mst.getTidesInformation()
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

    
def showTidesInfo(tidesDate):

    # Load data from local cache
    data = loadDataFromCacheFile()
    if not data:
        myprint(0, 'Unable to retrieve tides information from cache file')
        return -1

    labels = ['Date',
             '1st High Tide Time',
             '1st High Tide Height',
             '2nd High Tide Time',
             '2nd High Tide Height',
             '1st Low Tide Time',
             '1st Low Tide Height',
             '2nd Low Tide Time',
             '2nd Low Tide Height']

    # example: ["5", " 03:17", " 54", " 18:03", " 49", " 10:02", " 26", " -", " -"]

    try:
        day,firstHTT,firstHTH,secHTT,secHTH,firstLTT,firstLTH,secLTT,secLTH = data[tidesDate]
    except:
        myprint(0, f'Invalid input date: {tidesDate}')
        return -1

    if config.VERBOSE:
        print(f'{color.BOLD}Tides for date: %s{color.END}' % datetime.strptime(tidesDate, '%d%m%y').strftime("%a %d %b, %Y"))

        # build a list of tuples, each tuple containing: (time of tide, height of tide, label)
        l = list()
        for i in range(1, 9, 2):	# Skip over date field and height
            l.append((unicodedata.normalize("NFKD", data[tidesDate][i]).lstrip(),
                      data[tidesDate][i+1].lstrip(),
                      labels[i]))

        # Bubble sort the list by ascending time
        bubbleSort(l)
        
        # If reqesting today's tides, highlight next tide time
        if datetime.strptime(tidesDate, '%d%m%y').date() == datetime.today().date():
            timeNow = datetime.now().time()
            myprint(1, 'Today is:', datetime.now())

            nextTideNotFound = True
            for ele in l:
                t = datetime.strptime(ele[0], '%H:%M').time()
                if t >= timeNow:
                    if nextTideNotFound:
                        nextTideNotFound = False
                        s = "{L:<19}: {B}{T:6}{E}({H}) {B}*{E}".format(L=ele[2], T=ele[0], H=ele[1], B=color.BOLD, E=color.END)
                    else:
                        s = "{L:<19}: {T:6}({H})".format(L=ele[2], T=ele[0], H=ele[1], B=color.BOLD, E=color.END)
                else:
                    s = "{L:<19}: {T:6}({H})".format(L=ele[2], T=ele[0], H=ele[1])
                print(s)
        else:	# Tides request for another day
            for ele in l:
                s = "{L:<19}: {B}{T:6}{E}({H})".format(L=ele[2], B=color.BOLD, T=ele[0], E=color.END,H=ele[1])
                print(s)

        # s = ''
        # i = 1
        # for lbl in ['1st High Tide Time', '1st High Tide Height', '2nd High Tide Time', '2nd High Tide Height']:
        #     s += "{L}:{B}{V:>7}{E}".format(L=lbl, B=color.BOLD, V= data[tidesDate][i], E=color.END)
        #     i += 1
        # s += '\n'
        # for lbl in ['1st Low Tide Time', '1st Low Tide Height', '2nd Low Tide Time', '2nd Low Tide Height']:
        #     s += "{L}: {B}{V:<7}{E}".format(L=lbl, B=color.BOLD, V= data[tidesDate][i], E=color.END)
        #     i += 1
        # print(s)

    else:
        print(data[tidesDate])
    return 0