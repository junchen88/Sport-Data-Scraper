import requests_html as rh
import re
import webbrowser
import time
import tqdm
from datetime import datetime, timedelta
import json
import os


def getData(day):
    # cookies = {
    #     "Cookie": "OptanonConsent=isGpcEnabled=0&datestamp=Sun+Nov+07+2021+00%3A01%3A15+GMT%2B0800+(Australian+Western+Standard+Time)&version=6.19.0&isIABGlobal=false&hosts=&landingPath=NotLandingPage"
    # }
    session = rh.HTMLSession()
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "*",
        "Connection": "keep-alive",
        "Host": "d.flashscore.com.au",
        "Referer": "https://d.flashscore.com.au/x/feed/proxy-local",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "TE": "trailers",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0",
        "X-Fsign": "SW9D1eZo",
        "X-GeoIP": "1",
        "X-Referer": "https://www.flashscore.com.au/football/",
        "X-Requested-With": "XMLHttpRequest",
    }
    requesturl = f"https://d.flashscore.com.au/x/feed/f_1_{day}_8_en-au_1"
    response        = session.get(requesturl, headers=headers, stream=True)#, cookies=cookies)#, cookies=cookies)
    result          = response.text
    # print(result)
    # print(len(result))
    matchStrings    = re.findall(r'~AA÷(.*?)¬AD÷', result)
    print(str(len(matchStrings)) + " matches found")
    session.close()
    return matchStrings

def createLinks(ID):
    linkTemplate = "https://www.flashscore.com.au/match/"
    link = linkTemplate + ID + "#/h2h/overall"

    return link

# def openLinks():
#     i = 0
#     for links in createLinks():
#         webbrowser.open(links, new=0, autoraise=True)
#         i += 1
#         if i == 0:
#             time.sleep(5)

def getH2HResult(matchStrings, day):
    print("Finding past H2H for each match now...")
    additionalStr   = "https://d.flashscore.com.au/x/feed/df_hh_1_"
    matchData       = []
    headers         = {
        "Host": "d.flashscore.com.au",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://d.flashscore.com.au/x/feed/proxy-fetch",
        "x-fsign": "SW9D1eZo",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "TE": "trailers",
    }

    allH2HResult    = []
    # count = 0
    for element in tqdm.tqdm(matchStrings):
        H2HResult       = {}
        # if count > 10:
        #     break
        session = rh.HTMLSession()
        complete = additionalStr + element
        matchData.append(complete)
        response = session.get(complete, headers=headers, stream=True)
        # print(response.text)
        goalData        = re.search(r'Head-to-head(.*?)Home¬IS÷¬~KB÷Last matches:', response.text)
        homeAwayData    = re.findall(r'÷Last matches: (.*?)¬', response.text)

        # print(H2HData.group(0))
        H2HResultWithID = re.findall(r'¬KL÷(.*?)¬', goalData.group(0))

        H2HTeamData     = re.findall(r'KJ÷(.*?)¬KK÷', goalData.group(0))

        # print(H2HResult)
        H2HResultWithID.append(element)
        # print(H2HResultWithID)
        H2HResult["H2HResultWithID"] = H2HResultWithID
        H2HResult['home']            = homeAwayData[0]
        H2HResult['away']            = homeAwayData[1]
        H2HResult['H2HTeamData']     = H2HTeamData
        allH2HResult.append(H2HResult)
        # print(allH2HResult[0])
        session.close()
        # time.sleep(1)
        # count += 1

    # SAVE/WRITE TODAY'S MATCHES TO FILE
    dateTime = datetime.today()
    dateTime += timedelta(days=day)
    dateStr = dateTime.strftime('%Y-%m-%d')
    fileName = f"{dateStr}-all-matches-with-h2h"
    fp = open(fileName, 'w')
    json.dump(allH2HResult,fp)
    fp.close()        

    return allH2HResult

def homeOrAway(goals, home, away):
    if int(goals[0]) > int(goals[1]):
        return home

    elif int(goals[0]) == int(goals[1]):
        return "draw"

    else:
        return away

def writeToFile(filename, webLinks):
    fp = open(filename, 'w')
    for link in webLinks:
        fp.write(link + "\n")
    fp.close()

def findSuitableH2H(allH2HResult, goalNumThreshold, underGoalNumThreshold, noOfMatchesThresh, nbttswin):
    print("filtering results now...")
    print(goalNumThreshold, underGoalNumThreshold, noOfMatchesThresh, nbttswin)
    # goalNumThreshold = 5
    # underGoalNumThreshold = 3
    overGoalMatch = []
    underMatch = []
    winMatch = []
    bothTeamToScoreMatch = []
    notBothTeamToScoreMatch = []
    nbttswinMatch = []



#   LOOP FOR EACH MATCH
    # print(allH2HResult)
    for result in allH2HResult:

        noOfMatches   = 0
        SuitableCount   = 0
        SuitableUnder   = True
        SuitableWCount  = 0
        SuitableWin     = True
        winSide         = ""
        ID              = result["H2HResultWithID"].pop()
        count           = 0
        SuitableBothTeamToScore = True
        SuitableNotBothTeamToScore = True

        matchCounter    = 0
#       LOOP FOR EACH PAST H2H
        for match in result["H2HResultWithID"]:
            goals       = match.split(":")
            goalCount   = 0


#           WHEN IT IS ID, NOT GOAL RECORD
            if len(goals) < 1:
                # print(ID)
                continue

#           CHECK FOR CONDITION WHEN THE H2H RECORD MATCH IS AWARDED -
#           EG: DIDN'T PLAYED AND AWARDED ONE TEAM AS THE WINNER
            if len(goals) == 2:

#               LOOP FOR SPLITTED GOAL NUMBER
                i = 0                   #counter for tracking the goal numbers
                                        #larger than one for the h2h match
                for goal in goals:
                    goalCount += int(goal)

                    #
                    if int(goal) > 0:
                        i += 1

                # IF THE TWO GOAL NUMBER FOR THE MATCH IS NOT LARGER THAN 0, THEN NOT BTTS
                if i != 2:
                    SuitableBothTeamToScore = False
                else:
                    SuitableNotBothTeamToScore = False


            else:
                matchCounter += 1
                continue

#           ONLY CHECKS FOR THE LAST 4 MATCHES
            if noOfMatches < noOfMatchesThresh:
                if result['home'] in result['H2HTeamData'][matchCounter]:
                    home = result['home']
                    away = result['away']

                else:
                    home = result['away']
                    away = result['home']

                if winSide == "":
                    winSide = homeOrAway(goals, home, away)

                if winSide != homeOrAway(goals, home, away):
                    SuitableWin = False

                else:
                    SuitableWCount += 1

# #               IF MOST RECENT IS MORE THAN 4 GOALS, THEN IT'S GOOD MATCH
#                 if count == 0:
#                     if goalCount > 4:
#                         SuitableCount = 3





#               ALSO CHECKS FOR NOT SUITABLE UNDER GOAL
                if goalCount >= goalNumThreshold:
                    SuitableCount += 1


                if goalCount >= underGoalNumThreshold:
                    SuitableUnder = False

                noOfMatches += 1


            else:
                if goalCount >= underGoalNumThreshold:
                    SuitableUnder = False
                if count == 5:
                    break

            matchCounter += 1
            count += 1

        if SuitableCount > 2:
            overGoalMatch.append(createLinks(ID))

        if count > 4 and SuitableUnder == True:
            underMatch.append(createLinks(ID))

        if SuitableWin == True and SuitableWCount == noOfMatchesThresh:
            winMatch.append(createLinks(ID))

        if noOfMatches >= noOfMatchesThresh and SuitableBothTeamToScore == True:
            bothTeamToScoreMatch.append(createLinks(ID))

        if noOfMatches >= noOfMatchesThresh and SuitableNotBothTeamToScore == True:
            notBothTeamToScoreMatch.append(createLinks(ID))

        # IF nbbtswin FLAG IS ACTIVATED, THEN ADD THE RESULT THAT SATISFIES BOTH NBTTS AND WIN
        if nbttswin:
            if SuitableWin == True and SuitableWCount == noOfMatchesThresh:
                if noOfMatches >= noOfMatchesThresh and SuitableNotBothTeamToScore == True:
                    nbttswinMatch.append(createLinks(ID))


    writeToFile("over.txt", overGoalMatch)
    writeToFile("under.txt", underMatch)
    writeToFile("win.txt", winMatch)
    writeToFile("bothTeamToScore.txt", bothTeamToScoreMatch)
    writeToFile("notBothTeamToScore.txt", notBothTeamToScoreMatch)
    if nbttswin:
        writeToFile("nbttswin.txt", nbttswinMatch)
    

def runScraper(day, goalNumThreshold, underGoalNumThreshold, noOfMatchesThresh, nbttswin, forceFlag):

    dateTime = datetime.today()
    dateTime += timedelta(days=day)
    dateStr = dateTime.strftime('%Y-%m-%d')
    fileName = f"{dateStr}-all-matches-with-h2h"

    rawData = getData(day)
    h2hResult = None
    if forceFlag:
        h2hResult = getH2HResult(rawData, day)
    elif fileName not in os.listdir('.'):
        h2hResult = getH2HResult(rawData, day)
    else:
        fp = open(fileName)
        h2hResult = json.load(fp)
        fp.close()
    findSuitableH2H(h2hResult, goalNumThreshold, underGoalNumThreshold, noOfMatchesThresh, nbttswin)
