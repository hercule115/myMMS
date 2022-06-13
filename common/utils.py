import builtins as __builtin__
from csv import reader
from datetime import datetime
import inspect
import json
import os
import sys
import requests
import time
import unicodedata

import myGlobals as mg
import config

####
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


####        
def module_path(local_function):
    ''' returns the module path without the use of __file__.  
    Requires a function defined locally in the module.
    from http://stackoverflow.com/questions/729583/getting-file-path-of-imported-module'''
    return os.path.abspath(inspect.getsourcefile(local_function))


def myprint(level, *args, **kwargs):
    """My custom print() function."""
    # Adding new arguments to the print function signature 
    # is probably a bad idea.
    # Instead consider testing if custom argument keywords
    # are present in kwargs

    if level <= config.DEBUG:
        __builtin__.print('%s%s()%s:' % (color.BOLD, inspect.stack()[1][3], color.END), *args, **kwargs)


# Bubble sort function to sort a list of tuples
# Sort criteria (1st field of each tuple) is a time representation in the form "%H:%M"
def bubbleSort(elements):
    swapped = False
    # Looping from size of array from last index[-1] to index[0]
    for n in range(len(elements)-1, 0, -1):
        for i in range(n):
            if time.strptime(elements[i][0], "%H:%M") > time.strptime(elements[i+1][0], "%H:%M"):
                swapped = True
                # swapping data if the element is less than next element in the array
                elements[i], elements[i + 1] = elements[i + 1], elements[i]
        if not swapped:
            # exiting the function if we didn't make a single swap
            # meaning that the array is already sorted.
            return
        # reset swap flag
        swapped = False


# Leave the last 'l' characters of 'text' unmasked
def masked(text, l):
    nl=-(l)
    return text[nl:].rjust(len(text), "#")


####
def dumpListToFile(fname, aList):
    # open file in write mode
    with open(fname, 'w') as fp:
        for item in aList:
            # write each item on a new line
            fp.write("%s\n" % item)
        print('Done')


def dumpListOfListToFile(fname, aList):
    e = list()
    # open file in write mode
    with open(fname, 'w') as fp:
        for item in aList:
            #print(item,type(item))
            e.clear()
            for ele in item:
                e.append(unicodedata.normalize("NFKD", ele))
                
            # write each item on a new line
            fp.write("%s\n" % e)
        #print('Done')

        
def dumpToFile(fname, plainText):
    myprint(1,'Creating/Updating %s' % fname)
    myprint(1,'Text length: %d' % len(plainText))
    try:
        out = open(fname, 'w')
        out.write(plainText)
        out.close()
    except IOError as e:
        msg = "I/O error: Creating %s: %s" % (fname, "({0}): {1}".format(e.errno, e.strerror))
        myprint(1,msg)
        return -1
    return 0


####
def dumpJsonToFile(fname, textDict):
    myprint(1,'Creating/Updating %s' % fname)
    myprint(1,'Dict text length: %d, Plain text length: %d' % (len(textDict), len(str(textDict))))
    #myprint(1,textDict) 
    try:
        out = open(fname, 'w')
        out.write(json.dumps(textDict, ensure_ascii=False))
        out.close()
    except IOError as e:
        msg = "I/O error: Creating %s: %s" % (fname, "({0}): {1}".format(e.errno, e.strerror))
        myprint(1,msg)
        return -1
    return 0


####
def humanBytes(size):
    power = float(2**10)     # 2**10 = 1024
    n = 0
    power_labels = {0 : 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size = float(size / power)
        n += 1
    return '%s %s' % (('%.2f' % size).rstrip('0').rstrip('.'), power_labels[n])


####
def isFileOlderThanXMinutes(file, minutes=1): 
    fileTime = os.path.getmtime(file) 
    # Check against minutes parameter
    return ((time.time() - fileTime) > (minutes *  60))


####
def get_linenumber():
    cf = inspect.currentframe()
    return cf.f_back.f_lineno


####
def findBetween(s, first, last):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""


####
def parseConsumptionData(rawDataDict):
    outputDict = dict()

    myprint(1, 'Parsing rawDataDict. Length=%d' % (len(rawDataDict)))
            
    for interval,value in rawDataDict.items():
        if interval == '30MIN' or interval == 'JOUR':
            resource,date,cons = value.replace('"','').split(';')
            outputDict[interval] = {
                "resource" : resource,
                "date"  : date,
                "value" : float(cons.split()[0]),
                "unit"  : cons.split()[1],
            }
            
        if interval == 'MOIS' or interval == 'ANNEE':
            resource,date0,date1,cons = value.replace('"','').split(';')
            outputDict[interval] = {
                "resource" : resource,
                "date0"  : date0,
                "date1"  : date1,
                "value" : float(cons.split()[0]),
                "unit"  : cons.split()[1],
            }

    #print(json.dumps(outputDict, indent=4, ensure_ascii=False))
    return outputDict


####
def computeConsumptionByDays():
    # Parse .consumption-by-JOUR.csv data file and compute
    # consumption for each and every *complete* day (48 measurements). Example:
    #Électricité;01/07/2021;"2.4 kWh"

    inputFile = mg.consumptionFilesDict['JOUR']
    if not os.path.isfile(inputFile):
        myprint(0, '%s consumption file does not exist' % (inputFile))
        return {}

    myprint(1, f'Parsing file: {inputFile}')

    outputDict = dict()
    outputDict['date'] = list()
    outputDict['cons'] = list()
    outputDict['unit'] = list()
    outputDict['longDate'] = list()
        
    try:
        with open(inputFile, 'r') as f:
            csvReader = reader(f)
            next(csvReader) # Discard 1st line

            # Iterate over each row in the csv using reader object
            for row in csvReader:
                resource,date,rawCons = row[0].split(';')
                cons = float(rawCons.replace('"','').split(' ')[0]) # Keep numeric value only
                unit = rawCons.replace('"','').split(' ')[1] # Keep unit only                    

                try:
                    dts = datetime.strptime(date, '%d/%m/%Y').strftime('%Y-%m-%d')
                    # Build a long date to be used as name (Thursday, April 4 2030)
                    longDate = datetime.strptime(date, '%d/%m/%Y').strftime('%A, %B %d %Y')
                    # Get month name
                    monthName = datetime.strptime(date, '%d/%m/%Y').strftime('%B')
                    # Get year
                    year = datetime.strptime(date, '%d/%m/%Y').strftime('%Y')

                except:
                    myprint(1, 'ERROR while parsing date: %s' % date)

                if dts in outputDict['date']:
                    myprint(1, 'Skipping duplicate line for date %s' % (dts))
                    continue

                # Add this record to output dict
                outputDict['date'].append(dts)
                outputDict['cons'].append(cons)
                outputDict['unit'].append(unit)
                outputDict['longDate'].append(longDate)

    except:
        myprint(0, 'ERROR while parsing input file')
        return {} # Empty dict

    # Keep last N records
    dlen = len(outputDict['date'])
    KEEP_LAST_N_RECS = 14

    outputDict['date'] = outputDict['date'][dlen-KEEP_LAST_N_RECS:]
    outputDict['cons'] = outputDict['cons'][dlen-KEEP_LAST_N_RECS:]
    outputDict['unit'] = outputDict['unit'][dlen-KEEP_LAST_N_RECS:]
    outputDict['longDate'] = outputDict['longDate'][dlen-KEEP_LAST_N_RECS:]
    #print(json.dumps(outputDict, indent=4))
    return outputDict


####
# Parse input row. If an error is detected in the 'date' fields, then check in the next row
def parseRow(row, hack):
    myprint(2, f'Parsing row: {row}. hack={hack}')

    output = list()
    
    # Parse row
    # Example: Électricité;09/2018;09/2018;"101 kWh"

    rowAsList = row[0].split(';')
    resource  = rowAsList[0]    # not used
    fullDate0AsString = rowAsList[1]
    fullDate1AsString = rowAsList[2]

    dateAsString = fullDate0AsString[:7]
    month  = dateAsString[:2]
    year   = dateAsString[3:]
    longDate = datetime.strptime(dateAsString, '%m/%Y').strftime('%B %Y')

    consAsString = rowAsList[3].replace('"','')
    cons = int(consAsString.split(' ')[0])
    unit = consAsString.split(' ')[1]

    # If a hack is provided, it contains the previous row data
    if hack:
        isError = False
        
        myprint(1, 'Checking current row with previous record (hack)')

        month_hack = hack[1]
        year_hack  = hack[2]

        if int(month_hack)+1 == int(month) and int(year_hack) == int(year):
            # Must return 2 items (one with info from hack and one for current row)
            # Compute average between 'cons' fields and update both fields
            avg_cons = int((hack[4] + cons) / 2)
            hack[4] = avg_cons
            output.append(hack)
            output.append([dateAsString, month, year, longDate, avg_cons, unit])
            
    elif fullDate0AsString != fullDate1AsString:
        myprint(1, f'Warning: Invalid input row (malformed dates): {row}')
        
        isError = True
            
        dts0 = datetime.strptime(fullDate0AsString, '%m/%Y')
        dts1 = datetime.strptime(fullDate1AsString, '%m/%Y')
        
        dm = diff_month(dts1, dts0)
        if dm > 1:
            myprint(1, f'Skipping malformed input row: {row}')
        elif dm == 1:
            myprint(1, f'One Month difference detected between {dts0} and {dts1}. Creating hack record')
            hack = [dateAsString, month, year, longDate, cons, unit]
            output.append(hack)
    else:
        isError = False
        # Return single item for current row
        output.append([dateAsString, month, year, longDate, cons, unit])

    return isError, output


####
def parseConsumptionByMonths():
    # Parse .consumption-by-MOIS.csv data file

    inputFile = mg.consumptionFilesDict['MOIS']
    if not os.path.isfile(inputFile):
        myprint(0, f'{inputFile} consumption file does not exist')
        return ({}, 0)

    myprint(1, f'Parsing file: {inputFile}')
    
    try:
        with open(inputFile, 'r') as f:
            csvReader = reader(f)
            next(csvReader) # Discard 1st line

            fullmonths = dict()
            fullmonths['date'] = list()
            fullmonths['month'] = list()
            fullmonths['year'] = list()
            fullmonths['cons'] = list()
            fullmonths['longDate'] = list()
            fullmonths['unit'] = list()

            hack = None	# Used to store invalid input row

            for row in csvReader:
                isError, records = parseRow(row, hack)
                if isError == True:
                    hack = records[0]	# Save our hack record to be used in the next loop
                    continue

                # Update list ofrecords
                for item in records:
                    dateAsString = item[0]
                    month        = item[1]
                    year         = item[2]
                    longDate     = item[3]
                    cons         = item[4]
                    unit         = item[5]

                    myprint(2, f'Adding: {dateAsString} {month} {year} {longDate} {cons} {unit}')
                    
                    # Add this record to output dict
                    fullmonths['date'].append(dateAsString)
                    fullmonths['month'].append(month)
                    fullmonths['year'].append(year)
                    fullmonths['longDate'].append(longDate)
                    fullmonths['cons'].append(cons)
                    fullmonths['unit'].append(unit)

                hack = None
    except:
        myprint(0, 'ERROR while parsing input file')
        return ({}, 0)

    totalConsumption = sum(fullmonths['cons'])
    return (fullmonths, totalConsumption)


####
def computeTotalConsumption():
    consumptionByMonths, totalConsumption = parseConsumptionByMonths()
    myprint(1, f'Total Consumption: {totalConsumption}')
    return totalConsumption


####
def computeConsumptionByMonths():
    consumptionByMonths, totalConsumption = parseConsumptionByMonths()

    if not consumptionByMonths:
        return {}
    
    # Keep last 12 elements of the list
    outputDict = dict()
    for x in ['date', 'month', 'year', 'longDate', 'cons', 'unit']:
        outputDict[x] = consumptionByMonths[x][-12:]
        
    return outputDict


####
def generateConsumptionChart(d, interval, opt=''):
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import math
    
    myprint(1, 'interval=%s opt=%s' % (interval, opt))
    df = pd.DataFrame(d)
    #print (df)

    #my_colors = [(x/10.0, x/20.0, 0.75) for x in range(len(df))] # <-- Quick gradient example
    my_colors = ['C0', 'C1', 'C2', 'C3', 'C4']    
    df.plot(x="date", y="cons", kind='bar', xlabel='', color=my_colors)
    
    # Clear out odd xticks to increase readibility
    xticks = d['date']
    xticks[1::2] = [''] * math.floor(len(d['date'])/2)
    plt.xticks(range(0,len(xticks)), xticks)

    #plt.title('Consumption by %s %s' % (interval,opt))
    plt.gcf().suptitle('Consumption by %s %s' % (interval,opt), fontsize=16)
    #plt.legend(["kWh"])
    plt.gcf().autofmt_xdate(rotation=25.0)

   # Compute average and add an horizontal line
    avg = sum(d['cons']) / len(d['cons'])
    avghline = plt.axhline(avg, color='red', ls='--')

    #blue_patch = mpatches.Patch(color='blue', label='kWh')
    #plt.legend([blue_patch, avghline], ["kWh", "Average (%.1f)" % (avg)])
    plt.legend([avghline], ["Average (%.1f)" % (avg)])
    
    #plt.show()
    outputFile = os.path.join(mg.moduleDirPath, 'consumption-by-%s.png' % (interval))
    plt.savefig(outputFile, dpi=100)
    if not os.path.isfile(outputFile):
        myprint(0, 'Failed to create %s' % (outputFile))
        return None
    return outputFile


####
def sleepUntil(sleep_until):
    # Adds todays date to the string sleep_until.
    sleep_until = time.strftime("%m/%d/%Y " + sleep_until, time.localtime())
    # Current time in seconds from the epoch time.
    now_epoch = time.time()
    # Sleep_until time in seconds from the epoch time.
    alarm_epoch = time.mktime(time.strptime(sleep_until, "%m/%d/%Y %I:%M%p"))

    #If we are already past the alarm time today.
    if now_epoch > alarm_epoch:
        # Adds a day worth of seconds to the alarm_epoch, hence setting it to next day instead.
        alarm_epoch = alarm_epoch + 86400
        myprint(1, 'Alarm time is behind, sleeping until tomorrow: {}...'.format(alarm_epoch))

    dt = datetime.fromtimestamp(alarm_epoch).strftime('%Y/%m/%d %H:%M:%S')        
    myprint(1, 'Sleeping for: %d seconds (%s)' % (alarm_epoch - now_epoch, dt))

    # Sleeps until the next time the time is the set time, whether it's today or tomorrow.
    time.sleep(alarm_epoch - now_epoch)


####
def diff_month(d1, d2):
    #print(d1.year,d2.year,d1.month,d2.month)
    return (d1.year - d2.year) * 12 + d1.month - d2.month


####
def dumpContractInformation(contract, info): #(contract, info): #, type='all'):
    if config.VERBOSE:
        print('Contract N°: %s%s%s' % (color.BOLD, contract, color.END))

    print(json.dumps(info, indent=4, ensure_ascii=False))
