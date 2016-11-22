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
        return str(self.values)


class SeasonData(ParserData):
    type = 'season'

class TeamData(ParserData):
    type = 'team'

class GameData(ParserData):
    type = 'game'


class LGParser(object):

    def __init__(self, url):
        self.url = url

    def getseason(self, url):
        for p in url.split('/'):
            if p.startswith('20'):
                id = int(p.split('-')[-1])
                return SeasonData(id=id, years=p)


    def parseseason(self):
        r = requests.get(self.url)
        page = html.fromstring(r.content)

        self.season = self.getseason(self.url)

        yield self.season

        for e in self.getteams(page):
            yield e

        for e in self.getgames(page):
            yield e


    def getteams(self, page):
        teams = page.xpath("//select[@name='team']/option")
        self.teams = {}
        for t in teams:
            if t.attrib.get('value'):
                team = TeamData(name=t.text, id=t.attrib['value'])
                self.teams[team.name] = team
                yield team



    def getgames(self, page):
        games = page.xpath("//table[@id='games']/tbody/tr")
        #print games
        for tr in games:
            url = tr.xpath("td/a[@title='Seuranta']")
            tds = tr.xpath("td")
            teamstd = tr.xpath("td[@class='ta-l']/a")
            gametime = tr.xpath("td[@class='h-l']")[0].text
            teams = [t.strip() for t in teamstd[0].text.split('-')]
            gameno = int(tds[0].text)
            gamedate = tr.attrib.get('data-time')
            gameurl = url[0].attrib.get('href')

            for e in self.parsegame(gameno, gamedate, gametime, gameurl, teams):
                yield e

            
    def parsegame(self, gameno, gamedate, gametime, gameurl, teams, playoffs=False, seriesgameno=None):
        url = urlparse.urljoin(self.url, gameurl)
        #print gameno, url
        identifier = url.split('/')[-3]
        if gamedate:
            dt = datetime.date(int(gamedate[:4]), int(gamedate[4:6]), int(gamedate[6:8]))

        hometeam = self.teams[teams[0]].id
        awayteam = self.teams[teams[1]].id
        
        id = self.season.id*1000+gameno
        
        gamedata = GameData(
            id=id,
            number=gameno,
            identifier=identifier,
            date=str(dt),
            time=str(gametime),
            season=self.season.years,
            hometeam=hometeam,
            awayteam=awayteam,
            )
        yield gamedata


if __name__ == "__main__":
    urltype = sys.argv[1]
    url = sys.argv[2]

    parser = LGParser(url)
    if urltype == 'season':
        for event in parser.parseseason():
            print event.tojson()
    elif urltype == 'playoffs':
        for event in parser.parseplayoffs():
            print event.tojson()
    elif urltype == 'game':
        for event in parser.parsegameurl():
            print event.tojson()
        
        
