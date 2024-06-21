import webbrowser
import time

def runOpen(fileTypeList):
    fileName= None
    print(fileTypeList)

    for fileType in fileTypeList:
        if fileType == "o":
            fileName = "over"
        elif fileType == "u":
            fileName = "under"
        elif fileType == "btts":
            fileName = "bothTeamToScore"
        elif fileType == "nbtts":
            fileName = "notBothTeamToScore"
        elif fileType == "w":
            fileName = "win"
        elif fileType == "nbttsw":
            fileName = 'nbttswin'
        elif fileType == "team":
            fileName = 'teamOver'

        try:
            f = open(f"{fileName}.txt", "r")
        except Exception as e:
            print(f"{e}. Please run scraper again for the '{fileName}' result!")
            continue

        count = 0
        for url in f:
            print(url)
            
            if fileType == "team":
                url = url.split(",")[1]
            line = url.strip()
            webbrowser.open(line, new=0, autoraise=True)
            count += 1
            if count == 20:
                time.sleep(10)
                count = 0
