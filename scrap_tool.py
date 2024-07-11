import re
from datetime import datetime, timedelta
from time import localtime, strftime
import json
import os
from requests_html import HTMLSession, AsyncHTMLSession
from tqdm.asyncio import tqdm as async_tqdm
import asyncio
import webbrowser


class Scraper():
    def __init__(self) -> None:
        self.session            = HTMLSession()
        self.SCHEDULEMATCHURL   = "https://www.sofascore.com/api/v1/sport/football/scheduled-events/"
        self.EVENTURL           = "https://www.sofascore.com/api/v1/event/"
        self.TEAMURL   = "https://www.sofascore.com/api/v1/team/"
        pass

    def getLatestFinishedMatch(self, teamID):
        """
        Returns the latest finished match information for database check.
        """
        pastMatchURL = self.TEAMURL + str(teamID) + "/events/last/0"

        pass

    def findMatchWithPlayerStat(self, matchJsonData, matchIDs, teamName=None, numberOfMatchesWithData=None):
        """
        Determine whether the given match matchJsonData has
        player statistics. If it has the stats, then information
        regarding the match will be appended into matchIDs

        Parameters:
            - matchJsonData: JSON data containing information regarding the match
            - matchIDs: dict of dict, team name as key and another dict as its value
            - teamName (or None): the football team name
            - numberOfMatchesWithData (or None): counter for keeping the number of past matches with player stats appended

        Returns:
            - numberOfMatchesWithData (or None): counter for keeping the number of past matches with player stats appended
        """
        try:

            if matchJsonData["status"]["type"] == "finished" and "isAwarded" not in matchJsonData.keys():
                matchInfo = {
                    'customId': matchJsonData['customId'], 
                    'id': str(matchJsonData['id']), 
                    'slug': matchJsonData["slug"], 
                    'home': matchJsonData['homeTeam']['name'], 
                    'away': matchJsonData['awayTeam']['name'],
                    'home_id':matchJsonData['homeTeam']['id'], 
                    'away_id':matchJsonData['awayTeam']['id'],
                    'startTimestamp': matchJsonData["startTimestamp"],
                    'league': matchJsonData["tournament"]["name"]

                }

                if "hasEventPlayerStatistics" in matchJsonData.keys():
                    if matchJsonData["hasEventPlayerStatistics"] == True:
                        matchInfo["hasPlayerStats"] = True
                    else:
                        matchInfo["hasPlayerStats"] = False
                    
                elif matchJsonData['tournament']['uniqueTournament']['hasEventPlayerStatistics'] == True:
                    matchInfo["hasPlayerStats"] = True
                else:
                    matchInfo["hasPlayerStats"] = False
    
                if matchInfo["hasPlayerStats"] == True:

                    if teamName:
                        matchIDs[teamName].append(matchInfo)
                        numberOfMatchesWithData += 1
                    else:
                        matchIDs.append(matchInfo)
                
            return numberOfMatchesWithData

        except Exception as e:
            # log instead
            print(f"matchID : {matchJsonData['id']}, {e}")
            # don't append the current match info into matchIDs
            return numberOfMatchesWithData


    async def getPast5Matches(self, asession, teamID, teamName, matchIDs, pageNum):
        """
        If database doesn't have the latest H2H match, it will need to call this function to
        get the latest 5 h2h data
        """
        # init dict to store result
        if matchIDs is None:
            matchIDs = {teamName:[]}

        pastMatchURL = self.TEAMURL + str(teamID) + f"/events/last/{pageNum}"
        response = await asession.get(pastMatchURL, stream=True)
        dataJson = response.json()
        
        numberOfMatchesWithData = 0

        if len(dataJson["events"]) >= 5:
            # -6 since we want 5 results as range stops at target-1
            # latest result is at page 0 and at the end
            for i in range(len(dataJson["events"])-1, -1, -1):
                match = dataJson["events"][i]
                if "status" in match.keys():
                    numberOfMatchesWithData = self.findMatchWithPlayerStat(match, matchIDs, teamName, numberOfMatchesWithData)
               
                if numberOfMatchesWithData >= 5:
                    
                    break #stop loop if we got at least 5 data


        
        # go to the next page and get more data if possible
        if numberOfMatchesWithData < 5 and dataJson.get("hasNextPage", False):
            pageNum += 1
            await self.getPast5Matches(asession, teamID, teamName, matchIDs, pageNum)
        
        return matchIDs


    def findScheduledMatchWithPlayerStats(self, matchJsonData, matchIDs):
        if "status" in matchJsonData.keys():
            if matchJsonData["status"]["type"] == "notstarted" and "isAwarded" not in matchJsonData.keys():

                if matchJsonData['tournament']['uniqueTournament']['hasEventPlayerStatistics'] == True:
                    matchInfo = {
                        'customId': matchJsonData['customId'], 
                        'id': str(matchJsonData['id']), 
                        'slug': matchJsonData["slug"], 
                        'home': matchJsonData['homeTeam']['name'], 
                        'away': matchJsonData['awayTeam']['name'], 
                        'home_id':matchJsonData['homeTeam']['id'], 
                        'away_id':matchJsonData['awayTeam']['id'],
                        'startTimestamp': matchJsonData["startTimestamp"],
                        'league': matchJsonData["tournament"]["name"]
                    }
                    matchIDs.append(matchInfo)
        


    def getScheduledMatch(self):
        date = datetime.now() + timedelta(days=1)
        date = date.strftime("%Y-%m-%d")
        requestURL      = self.SCHEDULEMATCHURL + date
        response = self.session.get(requestURL)
        dictData = response.json()

        matchIDs = []
        for match in dictData['events']:
            dateStr = strftime('%Y-%m-%d', localtime(match["startTimestamp"]))
            if dateStr == date:
                self.findScheduledMatchWithPlayerStats(match, matchIDs)

        requestURL = requestURL + "/inverse"
        response = self.session.get(requestURL)
        moreData = response.json()

        for match in moreData['events']:
            dateStr = strftime('%Y-%m-%d', localtime(match["startTimestamp"]))
            if dateStr == date:
                self.findScheduledMatchWithPlayerStats(match, matchIDs)

        print(len(matchIDs))


        return matchIDs # return this to caller function to get historical data from database
                        # if data doesn't exist or not updated, call getPast5Matches function



    async def getPlayerMatchStat(self, asession, matchID):
        """
        Get player statistic such as shot made, shot on target, assist, goal scored, fouls, was fouled, shot saved if available
        
        Parameters:
            matchID: ID of the football match

        Returns:
            player_stats (dict of dict): a dictionary containing player names as key, and a dictionary containing the player stats as value
            {player:{statid, playerid, matchid, shot on target, assist, goal scored, fouls, was fouled, shot saved if available}, ...}
            {} if not valid
        """
        lineupPart = matchID["id"] + "/lineups"
        lineupURL = self.EVENTURL + lineupPart
        response = await asession.get(lineupURL, stream=True)

        # check for link validity, league such as Champions League Qualification
        # will not have players stats, but after qualification, they will have it
        if response.status_code == 404:
            # log instead!
            print(f"failed to obtain player stats: 404 not found", matchID['league'])
            return {}

        allPlayersStats = response.json()
        player_stats = {}
        customID = matchID["customId"]
        id = matchID["id"]
        slug = matchID["slug"]

        # stat_id (primary key)
        # match_id (foreign key referencing Match table)
        # player_id (foreign key referencing Player table)
        nextAvailablePlayerID = 0
        nextAvailableStatID = 0
        
        # check for available player id as all player id should be unique
        try:
            for player in allPlayersStats["home"]["players"]:

                # init dict
                player_stats[player["player"]["name"]] = {}
                player_dict = player_stats[player["player"]["name"]]

                player_dict["stat id"] = nextAvailableStatID
                player_dict["match id"] = f"{customID}_{id}_{slug}"
                player_dict["player id"] = nextAvailablePlayerID
                            
                # if key doesn't exist, it means 0
                if "statistics" in player.keys():
                    minutesPlayed = player["statistics"].get("minutesPlayed", 0)
                    player_dict["minutesPlayed"] = minutesPlayed

                    # get shots related data
                    blockedShots    = player["statistics"].get("blockedScoringAttempt", 0)
                    shotOffTargets  = player["statistics"].get("shotOffTarget", 0)
                    shotOnTargets   = player["statistics"].get("onTargetScoringAttempt", 0)
                    player_dict["shot made"] = blockedShots + shotOffTargets + shotOnTargets
                    player_dict["shot on target"] = shotOnTargets

                    # get goal related data
                    goalAssist = player["statistics"].get("goalAssist", 0)
                    player_dict["assist"] = goalAssist
                    goals = player["statistics"].get("goals", 0)
                    player_dict["goal scored"] = goals

                    # get foul related data
                    fouls = player["statistics"].get("fouls", 0)
                    player_dict["fouls"] = fouls
                    foulWon = player["statistics"].get("wasFouled", 0)
                    player_dict["foul won (was fouled)"] = foulWon

                    # get shot saved data
                    saves = player["statistics"].get("saves", 0)
                    player_dict["shot saved"] = saves
                
                # when player doesn't have the statistics keyword
                else:
                    player_dict["minutesPlayed"] = 'NA'
                    player_dict["shot made"] = 'NA'
                    player_dict["shot on target"] = 'NA'
                    player_dict["assist"] = 'NA'
                    player_dict["goal scored"] = 'NA'
                    player_dict["fouls"] = 'NA'
                    player_dict["foul won (was fouled)"] = 'NA'
                    player_dict["shot saved"] = 'NA'


                nextAvailablePlayerID += 1
                nextAvailableStatID += 1

        except Exception as e:
            print(f"failed to obtain player stats", repr(e))
            player_stats = {}

        return player_stats

    async def getMatchStat(self, asession, matchIDs):
        """
        Get overall match statistic such as team shot made, team shot on target, corner, offside, fouls, yellow/red cards, 
        for the whole match, 1st half, and 2nd half

        Parameters:
            matchID: ID of the football match

        Returns:
            match_stats (dict): a dictionary containing the match id and the overall match statistic as described above as value
            {match id: {stats}, ...}
        """
        statPart = matchIDs["id"] + "/statistics"
        lineupURL = self.EVENTURL + statPart
        response = await asession.get(lineupURL, stream=True)
        match_stats = {}
        match_stats["home"] = matchIDs["home"]
        match_stats["away"] = matchIDs["away"]

        if response.status_code == 200:
            allMatchStats = response.json()
            customID = matchIDs["customId"]
            id = matchIDs["id"]
            slug = matchIDs["slug"]
            matchID = f"{customID}_{id}_{slug}"

            periodPrefix = ""
            match_stats["match id"] = matchID
            

            for matchStats in allMatchStats["statistics"]:
                if matchStats["period"] != "ALL":
                    periodPrefix = matchStats["period"] + "_"

                else:
                    periodPrefix = ""
                    
                homePrefix = periodPrefix + "home_"
                awayPrefix = periodPrefix + "away_"
                # go through each stat type
                for statsType in matchStats["groups"]:
                    if statsType["groupName"] == "Match overview":

                        # go though each stats under the Match Overview category
                        # we only want corner kicks and fouls from this category
                        for statItem in statsType["statisticsItems"]:
                            if statItem["name"] == "Corner kicks":
                                
                                match_stats[f"{homePrefix}corner"] = statItem.get("home", 0)
                                match_stats[f"{awayPrefix}corner"] = statItem.get("away", 0)

                            elif statItem["name"] == "Fouls":
                                match_stats[f"{homePrefix}fouls"] = statItem.get("home", 0)
                                match_stats[f"{awayPrefix}fouls"] = statItem.get("away", 0)
                        

                    elif statsType["groupName"] == "Shots":

                        # go though each stats under the Shots category
                        # we only want total shots and shots on target from this category
                        for statItem in statsType["statisticsItems"]:
                            if statItem["name"] == "Total shots":
                                match_stats[f"{homePrefix}totalShot"] = statItem.get("home", 0)
                                match_stats[f"{awayPrefix}totalShot"] = statItem.get("away", 0)
                            
                            elif statItem["name"] == "Shots on target":
                                match_stats[f"{homePrefix}shotOnTarget"] = statItem.get("home", 0)
                                match_stats[f"{awayPrefix}shotOnTarget"] = statItem.get("away", 0)


                    elif statsType["groupName"] == "Goalkeeping":

                        # go though each stats under the Goalkeeping category
                        # we only want total saves from this category
                        for statItem in statsType["statisticsItems"]:
                            if statItem["name"] == "Total saves":
                                match_stats[f"{homePrefix}totalSaves"] = statItem.get("home", 0)
                                match_stats[f"{awayPrefix}totalSaves"] = statItem.get("away", 0)
                                break #exit the loop as we got the required stat already
            
        return match_stats
                    


    async def getAllMatchCompleteStat(self, matchIDs):
        """
        Get overall match stat and player stat

        Parameters:
            matchIDs (list of dict): list of dict containing customId, id, and slug. All of these are IDs of each match

        Returns:
            past_match_stat (dict of dict): a dictionary containing match ID as key, with dictionary containing 
            player statistic and overall match statistic as value        
        """
        asession = AsyncHTMLSession()

        # create a list of asynchronous task to execute
        tasks = [self.getPlayerMatchStat(asession, matchID) for matchID in matchIDs]

        

        # executes in the order of the awaits in the list
        # the result is an aggregate list of returned values
        playerStats = await async_tqdm.gather(*tasks, desc="getting player stats")

        tasks = [self.getMatchStat(asession, matchID) for matchID in matchIDs]
        past_match_stat = await async_tqdm.gather(*tasks, desc="getting match stats")
        

        for i , match in enumerate(matchIDs):
            past_match_stat[i]["player_stats"] = playerStats[i]

        return past_match_stat

        

    def getPastDateMatchStat(self, date:datetime):
        """
        Get finished matches complete stats for a particular past date

        Parameters:
            date: past datetime obj

        Returns:
            pastMatchesStats (dict of dict): a dictionary containing match ID as key, with dictionary containing 
            player statistic and overall match statistic as value
        """
        date = date.strftime("%Y-%m-%d")
        requestURL      = self.SCHEDULEMATCHURL + date
        response = self.session.get(requestURL)
        dictData = response.json()
        
        
       
        matchIDs = []

        self.filterMatchesWithPlayerStat(date,dictData,matchIDs)

        requestURL = requestURL + "/inverse"
        response = self.session.get(requestURL)
        moreData = response.json()
        self.filterMatchesWithPlayerStat(date,moreData,matchIDs)
        
                
        # for matchID in matchIDs:
        #     line = f"https://www.sofascore.com/{matchID['slug']}/{matchID['customId']}"
        #     webbrowser.open(line, new=0, autoraise=True)

        print(f"number Of Matches = {len(matchIDs)}")

        pastMatchesStats = asyncio.run(self.getAllMatchCompleteStat(matchIDs))

        return pastMatchesStats

    def filterMatchesWithPlayerStat(self, date, matchJSON:dict, matchIDs:list):
        for match in matchJSON['events']:
            dateStr = strftime('%Y-%m-%d', localtime(match["startTimestamp"]))
            if dateStr == date:
                if "status" in match.keys():
                    self.findMatchWithPlayerStat(match,matchIDs)

    def closeASession(self):
        """
        Close the browser for async
        """
        self.asession.close()

    def closeSession(self):
        """
        Close the browser
        """
        self.session.close()


    async def testing(self, matchIDs):
        
        asession = AsyncHTMLSession()
        pageNum = 0
        tasks = [self.getPast5Matches(asession, match["home_id"], match["home"], matchIDs=None, pageNum=pageNum) for match in matchIDs]
        tasks.extend([self.getPast5Matches(asession, match["away_id"], match["home"], matchIDs=None, pageNum=pageNum) for match in matchIDs])
        allPast5MatchIDs = await async_tqdm.gather(*tasks, desc="getting match stats")
        # print(allPast5MatchIDs)
        teamPastMatchID = []
        for teamMatchInfo in allPast5MatchIDs:
            for team, matchIDs in teamMatchInfo.items():
                teamPastMatchID.extend(matchIDs)

        pastMatchesStats = await self.getAllMatchCompleteStat(teamPastMatchID)

        return pastMatchesStats

test = Scraper()
matchIDs = test.getScheduledMatch()
allPast5MatchesID = asyncio.run(test.testing(matchIDs))
# fp = open("jsonData.json", "w")
# json.dump(allPast5MatchesID[0], fp, indent = 6)