# myMMS

Get tides from **Mauritius Météorological Service**

The goal of this tool is to retrieve the tides information provided by http://metservice.intnet.mu.
Results are provided as a JSON entity containing the following information:

- Date,
- 1st High Tide Time,
- 1st High Tide Height,
- 2nd High Tide Time,
- 2nd High Tide Height,
- 1st Low Tide Time,
- 1st Low Tide Height,
- 2nd Low Tide Time,
- 2nd Low Tide Height


2 modes are available:
- Local/Standalone mode: You run the tool locally from the system it is installed on. If no date is provided on the command line, today's tides are provided.  
- Remote mode: You retrieve the information over the network using the URL: http://server:5002/mymetservicetides/api/v1.0/tides/[mmddyy].  
  If the date is not provided, today's date is used. 

## Examples:

### Stand-alone mode

    python3 myMetServiceTides.py          # Get today's tides

    ['10', ' 10:05', ' 55', ' 22:06', ' 62', ' 04:16', ' 23', ' 15:55', ' 27']

    python3 myMetServiceTides.py -C -v    # Get today's tides. Use data from cache if available. Verbose mode ON

    Tides for date: Fri 10 Jun, 2022
    1st Low Tide Time  : 04:16 (23)
    1st High Tide Time : 10:05 (55)
    2nd Low Tide Time  : 15:55 (27) *
    2nd High Tide Time : 22:06 (62)

    python3 myMetServiceTides.py -v       # Get today's tides. Don't use cache but ask to the metservice server. Verbose mode ON

    python3 myMetServiceTides.py -v 010622  # Get June, 1st 2022 tides Verbose mode ON

    Tides for date: Wed 01 Jun, 2022
    1st High Tide Time : 01:05 (64)
    1st Low Tide Time  : 07:41 (16)
    2nd High Tide Time : 14:32 (57)
    2nd Low Tide Time  : 19:55 (37)

### Server/Client mode

    python3 myMetServiceTides.py -s       # Start server mode

*On client machine:*
    
    curl http://localhost:5002/mymetservicetides/api/v1.0/tides
    [
      "10",
      " 10:05",
      " 55",
      " 22:06",
      " 62",
      " 04:16",
      " 23",
      " 15:55",
      " 27"
    ]
