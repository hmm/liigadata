#!/usr/bin/env python
# -*- coding: utf-8 -*-


import datetime
import urlparse
import requests
import json
import sys

from lxml import html


class ParserData(object):
    
    def __init__(self, **values):
        self.__values = values
        self.__values['type'] = self.type
        for attr in values:
            setattr(self, attr, values[attr])

    def __setattr__(self, attr, value):
        if not attr.startswith('_'):
            self.__values[attr] = value
        super(ParserData, self).__setattr__(attr, value)
    
    def tojson(self):
        return json.dumps(self.__values, sort_keys=True)

    def __str__(self):
        return str(self.__values)

class FileTimestamp(ParserData):
    type = 'timestamp'

class PlayerTimeData(ParserData):
    type = 'playertimestats'

class TeamPPData(ParserData):
    type = 'teamppstats'

class TeamSHData(ParserData):
    type = 'teamshstats'



class PlayerTimesParser(object):

    def __init__(self, season):
        self.season = season
        self.seasonstr = "%d-%d" % (season-1, season)
        self.url = "http://liiga.fi/tilastot/%s/runkosarja/pelaajat/?team=&position=all&home_away=&player_stats=time_on_ice&sort=O#stats-wrapper" % self.seasonstr
        

    def parse(self):
        r = requests.get(self.url)
        page = html.fromstring(r.content)

        timestamp = FileTimestamp(
            timestamp = str(datetime.datetime.now()),
            season = self.season
        )
        yield timestamp
        
        for p in self.getplayers(page):
            yield p


    def getplayers(self, page):

        stats = page.xpath("//table[@id='stats']/tbody/tr")
        for tr in stats:
            tds = tr.xpath("td")
            player = tr.xpath("td[@class='ta-l']/a")[0]
            playerid = player.attrib.get('href')
            playername = player.text
            
            team = tds[2].text.strip()
            position = tds[3].text.strip()

            games = tds[4].xpath("strong")[0].text.strip()
            avgtime = tds[5].text.strip()
            shifts = tds[6].text.strip()
            pptime = tds[7].text.strip()
            pp2time = tds[8].text.strip()
            shtime = tds[9].text.strip()
            sh2time = tds[10].text.strip()
            p1time = tds[11].text.strip()
            p2time = tds[12].text.strip()
            p3time = tds[13].text.strip()

            data = PlayerTimeData(
                id = playerid.replace('/pelaajat/',''),
                name = playername,
                team = team,
                position = position,
                games = int(games),
                avgtime = avgtime,
                shifts = int(shifts),
                pptime = pptime,
                pp2time = pp2time,
                shtime = shtime,
                sh2time = sh2time,
                p1time = p1time,
                p2time = p2time,
                p3time = p3time,
            )
            yield data

class TeamTimesParser(object):

    def __init__(self, season):
        self.season = season
        self.seasonstr = "%d-%d" % (season-1, season)

    def parse(self):

        timestamp = FileTimestamp(
            timestamp = str(datetime.datetime.now()),
            season = self.season
        )
        yield timestamp
        
        ppurl = "http://liiga.fi/tilastot/%s/runkosarja/joukkueet/?stats_type=ylivoima&home_away=&sort=#stats-wrapper" % self.seasonstr
        shurl = "http://liiga.fi/tilastot/%s/runkosarja/joukkueet/?stats_type=alivoima&home_away=&sort=#stats-wrapper" % self.seasonstr

        for p in self.getteams(ppurl, TeamPPData):
            yield p

        for p in self.getteams(shurl, TeamSHData):
            yield p

    def getteams(self, url, dataclass):
        r = requests.get(url)
        page = html.fromstring(r.content)

        stats = page.xpath("//table[@id='stats']/tbody/tr")
        for tr in stats:
            tds = tr.xpath("td")
            
            team = tds[1].text.strip()
            ppnum = tds[2].text.strip()
            timeval = tds[3].text.strip()
            ppgoals = tds[4].text.strip()
            shgoals = tds[5].text.strip()
            pp2num = tds[8].text.strip()
            time2val = tds[9].text.strip()
            pp2goals = tds[10].text.strip()
            sh2goals = tds[11].text.strip()

            data = dataclass(
                team = team,
                ppnum = int(ppnum),
                ppgoals = int(ppgoals),
                shgoals = int(shgoals),
                pp2num = int(pp2num),
                pp2goals = int(pp2goals),
                sh2goals = int(sh2goals),
            )
            if dataclass == TeamSHData:
                data.shtime = timeval
                data.sh2time = time2val
            else:
                data.pptime = timeval
                data.pp2time = time2val
                
            yield data

class TeamSHTimesParser(TeamTimesParser):

    def __init__(self, season):
        self.seasonstr = "%d-%d" % (season-1, season)
        self.url = "http://liiga.fi/tilastot/%s/runkosarja/joukkueet/?stats_type=alivoima&home_away=&sort=#stats-wrapper" % self.seasonstr
        

    def getteams(self, page):

        stats = page.xpath("//table[@id='stats']/tbody/tr")
        for tr in stats:
            tds = tr.xpath("td")
            
            team = tds[1].text.strip()
            shnum = tds[2].text.strip()
            shtime = tds[3].text.strip()
            ppgoals = tds[4].text.strip()
            shgoals = tds[5].text.strip()
            sh2num = tds[8].text.strip()
            sh2time = tds[9].text.strip()
            pp2goals = tds[10].text.strip()
            sh2goals = tds[11].text.strip()

            data = TeamSHData(
                team = team,
                ppnum = ppnum,
                pptime = pptime,
                ppgoals = ppgoals,
                shgoals = shgoals,
                pp2num = pp2num,
                pp2time = pp2time,
                pp2goals = pp2goals,
                sh2goals = shgoals,
            )
            yield data



if __name__ == "__main__":
    urltype = sys.argv[1]
    season = int(sys.argv[2])

    if urltype == 'players':
        parser = PlayerTimesParser(season)
        for event in parser.parse():
            print event.tojson()

    elif urltype == 'teams':
        parser = TeamTimesParser(season)
        for event in parser.parse():
            print event.tojson()
            
            
