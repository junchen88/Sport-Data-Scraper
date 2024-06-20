import requests_html as rh
import re
from datetime import datetime, timedelta
import json
import os
from requests_html import AsyncHTMLSession
from tqdm.asyncio import tqdm as async_tqdm
import asyncio

#get and filter for useful data
async def getMatchH2H(asession, matchID):
    H2HResult       = {}
    additionalStr   = "https://d.flashscore.com.au/x/feed/df_hh_1_"
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
    completeUrl = additionalStr + matchID

    # Asynchronous requests to avoid unnecessary CPU wait time
    # Using AsyncHTMLSession instead of HTMLSession
    response = await asession.get(completeUrl, headers=headers, stream=True)
    # print(response.text)
    goalData        = re.search(r'Head-to-head(.*?)Home¬IS÷¬~KB÷Last matches:', response.text)
    homeAwayData    = re.findall(r'÷Last matches: (.*?)¬', response.text)

    # print(H2HData.group(0))
    H2HResultWithID = re.findall(r'¬KL÷(.*?)¬', goalData.group(0))

    H2HTeamData     = re.findall(r'KJ÷(.*?)¬KK÷', goalData.group(0))

    # print(H2HResult)
    H2HResultWithID.append(matchID)
    # print(H2HResultWithID)
    H2HResult["H2HResultWithID"] = H2HResultWithID
    H2HResult['home']            = homeAwayData[0]
    H2HResult['away']            = homeAwayData[1]
    H2HResult['H2HTeamData']     = H2HTeamData

    return H2HResult

# write filtered data to a file with today's date
async def getAllMatchesH2H(allMatchesID, day):
    print("Finding past H2H for each match now...")
    
    asession = AsyncHTMLSession()
    
    # create a list of asynchronous task to execute
    tasks = [getMatchH2H(asession, matchID) for matchID in allMatchesID]

    # executes in the order of the awaits in the list
    # the result is an aggregate list of returned values
    allH2HResult = await async_tqdm.gather(*tasks)
    await asession.close()

    # SAVE/WRITE TODAY'S MATCHES TO FILE
    dateTime = datetime.today()
    dateTime += timedelta(days=day)
    dateStr = dateTime.strftime('%Y-%m-%d')
    fileName = f"{dateStr}-all-matches-with-h2h.txt"
    fp = open(fileName, 'w')
    json.dump(allH2HResult,fp)
    fp.close()        

    return allH2HResult


async def getLeagueTeamData(asession, firstMatchID):
    """Returns a list containing information for each football team: 
    [[team name, team id, match played, goal scored:conceded, avg goal per match], [same information as before], ...]
    if avg goal per match = -1, this means the team have not played more than 5 matches in the league"""

    H2HResult       = {}
    completeUrl   = f"https://d.flashscore.com.au/x/feed/df_to_1_{firstMatchID}_1"
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


    # Asynchronous requests to avoid unnecessary CPU wait time
    # Using AsyncHTMLSession instead of HTMLSession
    # print(asession)
    response = await asession.get(completeUrl, headers=headers, stream=True)
    
    # results may contain empty list as it doesn't have standings, we need to remove it!
    # [(team name, team id, match played, goal scored:conceded), (same information as before), ...]
    allUsefulTeamData    = re.findall(r'TN÷(.*?)¬TI÷.*?TIU÷(.*?)¬TM÷(.*?)¬TW÷.*?TG÷(.*?)¬TP', response.text)

    if allUsefulTeamData:
        index = 0
        while index<len(allUsefulTeamData):

            allUsefulTeamData[index] = [usefulTeamData for usefulTeamData in allUsefulTeamData[index]]
            
            splitted = allUsefulTeamData[index][3].split(":")
            totalGoals = int(splitted[0]) + int(splitted[1])
            allUsefulTeamData[index][2]= int(allUsefulTeamData[index][2])
            if allUsefulTeamData[index][2] >= 5:
                avgGoalPerMatch = totalGoals/int(allUsefulTeamData[index][2])
                allUsefulTeamData[index].append(avgGoalPerMatch) # add avg goal information
            else:
                avgGoalPerMatch = -1 # not enough match played
                allUsefulTeamData[index].append(avgGoalPerMatch)
            index += 1

    return allUsefulTeamData 


async def getLeagueStanding(allFirstMatchOfLeagueID, day):
    print("Looking at team's data now...")
    
    asession = AsyncHTMLSession()
    
    # create a list of asynchronous task to execute
    tasks = [getLeagueTeamData(asession, firstMatchID) for firstMatchID in allFirstMatchOfLeagueID]

    # executes in the order of the awaits in the list
    # the result is an aggregate list of returned values
    allTeamUsefulData = await async_tqdm.gather(*tasks, desc="getting football team data")
    await asession.close()
    
    # combines a list of list of lists into a single list of lists and removes
    # empty list
    combinedAllTeamUsefulData = []
    [combinedAllTeamUsefulData.extend(sublist) for sublist in allTeamUsefulData]

    # SAVE/WRITE TODAY'S MATCHES TO FILE
    dateTime = datetime.today()
    dateTime += timedelta(days=day)
    dateStr = dateTime.strftime('%Y-%m-%d')
    fileName = f"{dateStr}-all-team-useful-data.txt"
    fp = open(fileName, 'w')
    json.dump(combinedAllTeamUsefulData,fp)
    fp.close()        

    return combinedAllTeamUsefulData

def getData(day):

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
    allMatchesID    = re.findall(r'~AA÷(.*?)¬AD÷', result)
    print(str(len(allMatchesID)) + " matches found")

    # Using first match ID from each league is easier to find the data
    # data between ZL÷ and ¬OAJ÷ pattern is the league url component
    # match ID within the league is usually after the url component
    # and before the next league url component.
    # Since we know the match ID is between ~AA÷ and ¬AD÷,
    # we can find the first match ID from each league using the pattern
    # below: after ¬OAJ÷ pattern, any characters can exist between the
    # first pattern and the ~AA÷ pattern, the ID we wanted is located
    # between ~AA÷ and ¬AD÷
    allFirstMatchOfLeagueID    = re.findall(r'¬OAJ÷.*?~AA÷(.*?)¬AD÷', result)

    print(str(len(allFirstMatchOfLeagueID)) + " leagues found")
    session.close()
    return allMatchesID, allFirstMatchOfLeagueID

def createLinks(ID):
    linkTemplate = "https://www.flashscore.com.au/match/"
    link = linkTemplate + ID + "#/h2h/overall"

    return link



def homeOrAway(goals, home, away):
    if int(goals[0]) > int(goals[1]):
        return home

    elif int(goals[0]) == int(goals[1]):
        return "draw"

    else:
        return away

def writeToFile(filename, suitableData):
    fp = open(filename, 'w')
    for data in suitableData:
        if type(data) is list:
            for element in data:
                fp.write(str(element) + ", ")
            fp.write("\n")
        else:
            fp.write(data + "\n")
    fp.close()

def findSuitableTeam(allTeamUsefulData, goalNumThreshold):
    print("filtering team results now...")
    suitableTeam = []

    for teamUsefulData in allTeamUsefulData:
        if teamUsefulData[4] > goalNumThreshold:
            teamUsefulData[1] = "https://www.flashscore.com.au" + teamUsefulData[1]
            suitableTeam.append(teamUsefulData)
            
    writeToFile("teamOver.txt", suitableTeam)


            

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
    H2HfileName = f"{dateStr}-all-matches-with-h2h.txt"

    allMatchesID, allFirstMatchOfLeagueID = getData(day)
    # h2hResult = None
    # if forceFlag:
    #     h2hResult = asyncio.run(getAllMatchesH2H(allMatchesID, day))
    # elif H2HfileName not in os.listdir('.'):
    #     h2hResult = asyncio.run(getAllMatchesH2H(allMatchesID, day))
    # else:
    #     fp = open(H2HfileName)
    #     h2hResult = json.load(fp)
    #     fp.close()
    # findSuitableH2H(h2hResult, goalNumThreshold, underGoalNumThreshold, noOfMatchesThresh, nbttswin)
    

    teamFileName = f"{dateStr}-all-team-useful-data.txt"
    if forceFlag:
        allTeamUsefulData =     asyncio.run(getLeagueStanding(allFirstMatchOfLeagueID, day))
    elif teamFileName not in os.listdir('.'):
        allTeamUsefulData =     asyncio.run(getLeagueStanding(allFirstMatchOfLeagueID, day))
    else:
        fp = open(teamFileName)
        allTeamUsefulData = json.load(fp)
        fp.close()
    findSuitableTeam(allTeamUsefulData,goalNumThreshold)
