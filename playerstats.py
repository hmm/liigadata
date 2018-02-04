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


class PlayerStatsData(ParserData):
    type = 'playerstats'




class PlayerStatsParser(object):
    baseurl = "http://liiga.fi/tilastot/{season}/{serie}/pelaajat/?team={team}&position=all&player_stats=players&sort=P#stats-wrapper"
    seasonsurl = "http://liiga.fi/tilastot/kaikki/runkosarja/pelaajat/"

    def __init__(self):
        for season in self.parseseasons():
            url = self.baseurl.format(season=season, serie='runkosarja', team='')

            for (team, teamname) in self.parseteams(url):

                 url = self.baseurl.format(season=season, serie='runkosarja', team=team)
                 for p in self.parseplayers(team, teamname, season, False, url):
                     print p.tojson()
                     
                 url = self.baseurl.format(season=season, serie='playoffs', team=team)
                 for p in self.parseplayers(team, teamname, season, True, url):
                     print p.tojson()


    def parseseasons(self):
        r = requests.get(self.seasonsurl)
        
        page = html.fromstring(r.content)
        seasonlist = page.xpath("//select[@name='season']/option")
        for o in seasonlist:
            value = o.attrib.get('value')
            if '-' in value:
                yield value # int(value.split('-')[1])
                

    def parseteams(self, url):
        r = requests.get(url)
        
        page = html.fromstring(r.content)
        teamlist = page.xpath("//select[@name='team']/option")
        for o in teamlist:
            team = o.attrib.get('value')
            name = o.text.strip()
            if team:
                yield (team, name)

    @classmethod
    def strvalue(self, value):
        if value == '-':
            return None
        if not value:
            return None
        return value

    @classmethod
    def pctvalue(self, s):
        if not s or s == '-':
            return None
        return float(s.replace(',','.'))

    @classmethod
    def intvalue(self, value):
        if value == '-':
            return None
        if not value:
            return None
        return int(value)
    
        
    def parseplayers(self, teamid, teamname, season, playoffs, url):
        r = requests.get(url)
        page = html.fromstring(r.content)

        stats = page.xpath("//table[@id='stats']/tbody/tr")
        for tr in stats:
            tds = tr.xpath("td")
            playerelem = tr.xpath("td[@class='ta-l']/a")
            if playerelem:
                player = playerelem[0]
                playerid = player.attrib.get('href')
                playername = player.text
                position = None

            team = tds[2].text.strip()
            if team == 'Yht.' or team != teamname:
                continue
            poselem = tds[3].text
            if poselem:
                position = self.strvalue(poselem.strip())

            games = tds[4].text.strip()
            goals = tds[5].text.strip()
            assists = tds[6].text.strip()
            points = tds[7].xpath("strong")[0].text.strip()
            penalties = tds[8].text.strip()

            plus = self.intvalue(tds[9].text.strip())
            minus = self.intvalue(tds[10].text.strip())
            plusminus = self.intvalue(tds[11].text.strip())

            ppgoals = self.intvalue(tds[12].text.strip())
            shgoals = self.intvalue(tds[13].text.strip())
            wingoals = self.intvalue(tds[14].text.strip())
            
            shots = self.intvalue(tds[15].text.strip())
            shotpct = self.pctvalue(tds[16].text.strip())

            faceoffs = self.intvalue(tds[17].text.strip())
            faceoffpct = self.pctvalue(tds[18].text.strip())

            playtime = self.strvalue(tds[19].text.strip())
            
            #print playerid, playername, team, position, games

            data = PlayerStatsData(
                playerid = playerid.replace('/pelaajat/',''),
                playername = playername,
                season = season,
                playoffs = playoffs,
                team = teamid,
                position = position,
                games = int(games),

                goals = int(goals),
                assists = int(assists),
                points = int(points),
                penalties = int(penalties),
                
                plus = plus,
                minus = minus,
                plusminus = plusminus,
                
                ppgoals = ppgoals,
                shgoals = shgoals,
                wingoals = wingoals,
                
                shots = shots,
                shotpct = shotpct,
                
                faceoffs = faceoffs,
                faceoffpct = faceoffpct,
                
                playtime = playtime,
            )
            yield data


    def parse(self, url):
        timestamp = FileTimestamp(
            timestamp = str(datetime.datetime.now()),
            season = self.season
        )
        yield timestamp
        
        for p in self.getplayers(page):
            yield p



if __name__ == "__main__":
    urltype = sys.argv[1]
    season = int(sys.argv[2])

    if urltype == 'players':
        parser = PlayerStatsParser()

