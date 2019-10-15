#!/usr/bin/env python
# -*- coding: utf-8 -*-


import datetime
import urllib
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


class SeasonData(ParserData):
    type = 'season'

class TeamData(ParserData):
    type = 'team'

class GameData(ParserData):
    type = 'game'

class TeamStatData(ParserData):
    type = 'teamstat'


class LGParser(object):

    def __init__(self, url):
        self.url = url

    def getseason(self, url):
        for p in url.split('/'):
            if p.startswith('20'):
                id = int(p.split('-')[-1])
                return SeasonData(id=id, years=p)
            elif p.startswith('19'):
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


    def parseplayoffs(self, url):
        r = requests.get(url)
        page = html.fromstring(r.content)

        for e in self.getgames(page, playoffs=True):
            yield e


    def getstats(self, year):
        baseurl = "http://liiga.fi/tilastot/%d-%d/runkosarja/joukkueet/?stats_type=%s&home_away=&sort=#stats-wrapper"

        teams = {}

        for s, attrname, tdnums in (
                ('yleisomaara', 'attendance', (4, -1)),
                ('rangaistukset', 'minutes', (9,)),
                ('ylivoima', 'ppgoals', (4,)),
        ):
            url = baseurl % (year, year+1, s)
            r = requests.get(url)
            page = html.fromstring(r.content)

            stats = page.xpath("//table[@id='stats']/tbody/tr")

            for tr in stats:
                teamnametd = tr.xpath("td[@class='ta-l separator']")
                if not teamnametd:
                    teamnametd = tr.xpath("td[@class='ta-l']")
                teamname = teamnametd[0].text.strip()

                tds = tr.xpath("td")
                statvalue = None
                
                for tdnum in tdnums:
                    if attrname == 'minutes':
                        statelem = tds[tdnum].xpath("strong")[0]
                    else:
                        statelem = tds[tdnum]

                    if statelem is not None and statelem.text and int(statelem.text):
                        statvalue = statelem.text.strip()
                        break

                team = self.getteam(teamname)

                ts = teams.setdefault(team, TeamStatData(team=team.id, season=self.season.years))
                setattr(ts, attrname, statvalue)

                
        for t in teams.values():
            yield t



    def getteams(self, page):
        teams = page.xpath("//select[@name='team']/option")
        self.teams = {}
        for t in teams:
            if t.attrib.get('value'):
                team = TeamData(name=t.text, id=t.attrib['value'])
                self.teams[team.name] = team
                yield team


    teamsmapping = {
        'Pelicans': 'Kiekkoreipas', 
        'Kiekkoreipas': 'Hockey-Reipas', 
        'Hockey-Reipas': 'Reipas', 
        'JYP': 'JyP HT',
        'Blues': 'Kiekko-Espoo',
        'FPS': 'FoPS',
        'Jokipojat': 'JoKP',
    }

    def getteam(self, teamname):
        origname = teamname
        while teamname not in self.teams and teamname in self.teamsmapping:
            teamname = self.teamsmapping[teamname]
        try:
            return self.teams[teamname]
        except:
            print(origname, teamname)
            print(self.teams.keys())
            raise


    def correctdates(self, gameno, gamedate):
        if self.season.id == 1979 and gameno > 75 and gameno < 80:
            if gameno == 76:
                gameno = 79
                gamedate = '19781126'
            else:
                gameno -= 1
        elif self.season.id == 1988 and gameno > 125 and gameno < 130:
            if gameno == 129:
                gameno = 126
                gamedate = '19871203'
            else:
                gameno += 1
            
        return (gameno, gamedate)

    def getgames(self, page, playoffs=False):
        games = page.xpath("//table[@id='games']/tbody/tr")
        #print games

        for tr in games:
            url = tr.xpath("td/a[@title='Seuranta']")
            tds = tr.xpath("td")
            teamstd = tr.xpath("td[@class='ta-l']/a")
            gametime = tr.xpath("td[@class='h-l']")[0].text
            #teams = [t.strip() for t in teamstd[0].text.split('-')]
            teams = [s.strip() for s in teamstd[0].text.split('\n') if s.strip()]

            gameno = int(tds[0].text)
            gamedate = tr.attrib.get('data-time')

            # fix incorrect dates in liiga.fi 
            (gameno, gamedate) = self.correctdates(gameno, gamedate)
            
            gameurl = url[0].attrib.get('href')
            scorelist = tds[5].text.split()
            if scorelist[0] == '-':
                return
            homescore = int(scorelist[0])
            awayscore = int(scorelist[-1])
            resultattr = tds[6].text.strip()
            score = "%d-%d" % (int(homescore), int(awayscore))
            
            url = urllib.parse.urljoin(self.url, gameurl)
            identifier = url.split('/')[-3]
            if gamedate:
                dt = datetime.date(int(gamedate[:4]), int(gamedate[4:6]), int(gamedate[6:8]))

            hometeam = self.getteam(teams[0]).id
            awayteam = self.getteam(teams[-1]).id
        
            id = self.season.id*1000+gameno
            if playoffs:
                id+=900
            if self.season.id > 2004:
                winpoints = 3
                otwin = 2
                otloss = 1
            elif self.season.id < 2002:
                winpoints = 2
                otwin = 2
                otloss = 0
            else:
                winpoints = 2
                otwin = 2
                otloss = 1

        
            if not playoffs:
                if homescore == awayscore:
                    homepoints = awaypoints = 1
                elif resultattr not in ['JA', 'VL']:
                    if homescore > awayscore:
                        homepoints = winpoints
                        awaypoints = 0
                    else:
                        homepoints = 0
                        awaypoints = winpoints
                else:
                    if homescore > awayscore:
                        homepoints = otwin
                        awaypoints = otloss
                    else:
                        homepoints = otloss
                        awaypoints = otwin

                home = dict(score=homescore, points=homepoints, team=hometeam)
                away = dict(score=awayscore, points=awaypoints, team=awayteam)
            else:
                home = dict(score=homescore, team=hometeam)
                away = dict(score=awayscore, team=awayteam)

            gamedata = GameData(
                id=id,
                number=gameno,
                identifier=identifier,
                date=str(dt),
                time=str(gametime),
                season=self.season.years,
                playoffs=playoffs,
                home=home,
                away=away,
                score=score,
                resultattr=resultattr
            )
            yield gamedata



    


if __name__ == "__main__":
    urltype = sys.argv[1]

    if urltype == 'season':
        url = sys.argv[2]
        parser = LGParser(url)
        for event in parser.parseseason():
            print(event.tojson())
    elif urltype == "history":
        for i in range(1975, 2020):
            url = "http://liiga.fi/ottelut/%d-%d/runkosarja/" % (i, i+1)
            parser = LGParser(url)
            for event in parser.parseseason():
                print(event.tojson())
            url = "http://liiga.fi/ottelut/%d-%d/playoffs/" % (i, i+1)

            for event in parser.parseplayoffs(url):
                print(event.tojson())

            for event in parser.getstats(i):
                print(event.tojson())
            
