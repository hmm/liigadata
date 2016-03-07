#!/usr/bin/env python

import datetime
import urlparse
import requests
import json
import sys

from lxml import html


class ParserData(object):
    
    def __init__(self, **values):
        self.values = values
        self.values['type'] = self.type
        for attr in values:
            setattr(self, attr, values[attr])

    def tojson(self):
        return json.dumps(self.values, sort_keys=True)

    def __str__(self):
        return str(self.values)


class SeasonData(ParserData):
    type = 'season'

class TeamData(ParserData):
    type = 'team'

class GameData(ParserData):
    type = 'game'

class GameEventData(ParserData):
    type = 'gameevent'

class LGParser(object):

    def __init__(self, url):
        self.url = url
        self.season = self.getseason(self.url)

    def getseason(self, url):
        for p in url.split('/'):
            if p.startswith('20'):
                id = int(p.split('-')[-1])
                return SeasonData(id=id, years=p)


    def parse(self):
        r = requests.get(self.url)
        page = html.fromstring(r.content)

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
            teams = [t.strip() for t in teamstd[0].text.split('-')]
            gameno = int(tds[0].text)
            gamedate = tr.attrib.get('data-time')
            gameurl = url[0].attrib.get('href')
            for e in self.parsegame(gameno, gamedate, gameurl, teams):
                yield e

            



    def parsegame(self, gameno, gamedate, gameurl, teams):
        url = urlparse.urljoin(self.url, gameurl)
        #print gameno, url
        identifier = url.split('/')[-3]
        dt = datetime.date(int(gamedate[:4]), int(gamedate[4:6]), int(gamedate[6:8]))
        if dt > datetime.date.today():
            return

        r = requests.get(url)
        page = html.fromstring(r.content)

        home = self.teams[teams[0]].id
        away = self.teams[teams[1]].id
        
        info = page.xpath("//div[@class='info']/p")
        (homescore, _, awayscore) = info[0].text.split()
        score = "%d-%d" % (int(homescore), int(awayscore))

        periods = info[1].text
        tm = info[2].text.split()[0]
        if tm == '60:00':
            if homescore > awayscore:
                homepoints = 3
                awaypoints = 0
            else:
                homepoints = 0
                awaypoints = 3
        else:
            if homescore > awayscore:
                homepoints = 2
                awaypoints = 1
            else:
                homepoints = 1
                awaypoints = 2

        attendance = int(info[4].text.split()[-1])
        id = self.season.id*1000+gameno
        

        gamedata = GameData(
            id=id,
            number=gameno,
            identifier=identifier,
            date=str(dt),
            season=self.season.years,
            time=tm,
            periods=periods,
            score=score,
            home = dict(score=homescore, points=homepoints, team=home),
            away = dict(score=awayscore, points=awaypoints, team=away),
            attendance=attendance,
            )
        yield gamedata

        events = page.xpath("//div[@class='table']//tr")
        eventnum = 1
        for e in events:
            if e.attrib.get('class') in ['odd', 'even']:
                tds = e.xpath("td")
                if tds and len(tds) == 3:
                    home, gtime, away = tds
                    if gtime.text and len(gtime.text) == 5 and gtime.text[2] == ':':
                        e = self.parsegameevent(gamedata, eventnum, home, gtime, away)
                        if e:
                            eventnum += 1
                            yield e
                            
    def parsegameevent(self, gamedata, eventnum, home, gtime, away):
        #print gtime.text
        id = gamedata.id * 1000000 + int(gtime.text.replace(':',''))*100 + eventnum
        ret = []
        if home.text:
            elem = home
            team = gamedata.home.get('team')
            vsteam = gamedata.away.get('team')
        if away.text:
            elem = away
            team = gamedata.away.get('team')
            vsteam = gamedata.home.get('team')
            if home.text:
                raise Exception("Both home and away event %s" % gtime)
        #print html.tostring(elem)

        strong = None
        playernums = []
        playermeta = []
        for c in elem.iterdescendants():
            #print c.tag, c.text, c.tail
            if c.tag == 'strong':
                strong = c
            elif c.tag == 'span' and c.text[0] == '#':
                playernums.append(c.text[1:])
            elif c.tag == 'a':
                playermeta.append((c.attrib['href'], c.text, c.tail.strip()))
                

        players = [(num, p[0], p[1], p[2]) for num, p in zip(playernums, playermeta)]

        def playerdata(data):
            return dict(
                number=int(data[0]),
                id=data[1].replace('/pelaajat/',''),
                name=data[2],
                team=team,
                vsteam=vsteam
            )
            
        eventattr = {}
        if strong is not None and players:
            eventtype = 'goal'
            scorer = players[0]
            eventattr['scorer'] = playerdata(scorer)
            eventattr['score'] = scorer[3]
            eventattr['assist1'] = None
            eventattr['assist2'] = None
            if len(players) > 1:
                eventattr['assist1'] = playerdata(players[1])
            if len(players) > 2:
                eventattr['assist2'] = playerdata(players[2])
            metatext = players[-1][3].replace(')','').strip() + "," + strong.tail.replace('(', '')
            goalmeta = []

            for meta in [m.strip() for m in metatext.split(',') if m.strip()]:
                if meta == eventattr['score']:
                    continue

                if meta in ['YV', 'YV2', 'AV', 'AV2', 'VT', 'VM', 'TM', 'TV', 'IM', 'SR', 'RL']:
                    goalmeta.append(meta)
                else:
                    raise Exception("Unknown game meta '%s'" % meta)
                    
            if gtime.text > '60:00':
                goalmeta.append('JA')

            eventattr['goalmeta'] = ' '.join(goalmeta)
                

        elif strong is not None and not players:
            eventtype = 'goal'
            eventattr['scorer'] = dict(
                number=int(strong.text.strip()[1:]),
                id=playermeta[0][0].replace('/pelaajat/',''),
                name=playermeta[0][1],
                team=team,
                vsteam=vsteam
            )
            eventattr['assist1'] = None
            eventattr['assist2'] = None
            eventattr['score'] = playermeta[0][2]
            eventattr['goalmeta'] = 'VL'

        elif players and (" min " in players[0][3] or " min " in elem.text):
            eventtype = 'penalty'
            eventattr['player'] = None
            eventattr['boxed'] = None
            if " min " in players[0][3]:
                words = players[0][3].split()

                eventattr['player'] = playerdata(players[0])
                eventattr['minutes'] = int(words[0])
                eventattr['reason'] = " ".join(words[2:])
            else:
                words = elem.text.split()
                minindex = words.index('min')
                eventattr['minutes'] = int(words[minindex-1])
                eventattr['reason'] = " ".join(words[minindex+1:])
                eventattr['penaltymeta'] = 'teampenalty'
                

            if len(players) > 1:
                eventattr['boxed'] = playerdata(players[1])

        elif players and ( 
            "koukkaaminen" in players[0][3] or
            "huitominen" in players[0][3] or
            "korkea maila" in players[0][3] or
            "kampitus" in players[0][3] or
            "kiekon sulkeminen" in players[0][3] or
            "pelin viivytt" in players[0][3] or
            "kiinnipit" in players[0][3] or
            "heitto" in players[0][3]
            ):
            eventtype = 'penalty'
            eventattr['minutes'] = 0
            eventattr['player'] = playerdata(players[0])
            eventattr['reason'] = players[0][3].strip()
            eventattr['boxed'] = None
            

        elif players and "Joukkuerangaistus" in elem.text:
            eventtype = 'penalty'
            eventattr['minutes'] = 0
            eventattr['player'] = None
            eventattr['boxed'] = playerdata(players[0])
            eventattr['reason'] = elem.text.strip()
            eventattr['penaltymeta'] = 'teampenalty'

        elif 'Joukkuerangaistus' in elem.text:
            eventtype = 'penalty'
            words = elem.text.split()
            minindex = words.index('min')
            eventattr['minutes'] = int(words[minindex-1])
            eventattr['reason'] = " ".join(words[minindex+1:])
            eventattr['penaltymeta'] = 'teampenalty'
            eventattr['player'] = None
            eventattr['boxed'] = None

        elif 'aikalis' in elem.text:
            eventtype = 'timeout'

        elif 'Maalivahti ulos' in elem.text:
            eventtype = 'goalkeeperout'
            eventattr['goalkeeperout'] = playerdata(players[0])
            eventattr['goalkeeperin'] = None

        elif 'Maalivahti sis' in elem.text:
            eventtype = 'goalkeeperin'
            eventattr['goalkeeperin'] = playerdata(players[0])
            eventattr['goalkeeperout'] = None

        elif 'Maalivahdin vaihto' in elem.text:
            if "ulos" in players[0][3]:
                eventtype = 'goalkeeperchange'
                eventattr['goalkeeperout'] = playerdata(players[0])
                eventattr['goalkeeperin'] = playerdata(players[1])

        elif 'Videotarkistus - ei maalia' in elem.text:
            eventtype = 'videocheck'

        elif 'Rangaistuslaukaus - ei maalia' in elem.text:
            eventtype = 'penaltyshot'
            eventattr['result'] = 'no goal'
            eventattr['player'] = dict(
                id = None,
                number = None,
                name = elem.text[elem.text.index('(')+1:elem.text.index(')')],
                team = team,
                vsteam = vsteam
                )

        elif gtime.text == '65:00' and playermeta and not players:
            eventtype = 'penaltyshot'
            
            eventattr['player'] = dict(
                number=int(elem.text.strip()[1:]),
                id=playermeta[0][0].replace('/pelaajat/',''),
                name=playermeta[0][1],
                team=team,
                vsteam=vsteam
            )
            if "ei maalia" in playermeta[0][2]:
                eventattr['result'] = 'no goal'
            elif "maali" in playermeta[0][2]:
                eventattr['result'] = 'goal'

        else:
            raise Exception("Unknown gameevent, players: %s, elem.text: '%s'" % (players, elem.text))

        if 'reason' in eventattr and eventattr['reason'].endswith('('):
            eventattr['reason'] = eventattr['reason'][:-2].strip()

        if gtime.text < '20:00':
            period = '1'
        elif gtime.text < '40:00':
            period = '2'
        elif gtime.text < '60:00':
            period = '3'
        elif gtime.text < '65:00':
            period = 'JA'
        elif gtime.text == '65:00':
            period = 'VL'

        return GameEventData(
            id = id,
            season = gamedata.season,
            gameid=gamedata.id,
            time=gtime.text,
            eventtype=eventtype,
            team=team,
            vsteam=vsteam,
            period=period,
            teammeta=elem.attrib['class'],
            **eventattr
        )
            


if __name__ == "__main__":
    for url in sys.argv[1:]:
        parser = LGParser(url)
        for event in parser.parse():
            print event.tojson()
