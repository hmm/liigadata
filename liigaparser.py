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

class PlayerData(ParserData):
    type = 'player'

class GoalkeeperData(ParserData):
    type = 'goalkeeper'

class PeriodData(ParserData):
    type = 'period'

class GameStatsData(ParserData):
    type = 'gamestats'

class GameEventData(ParserData):
    type = 'gameevent'

class ShotData(ParserData):
    type = 'shot'

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

            
    def genpct(self, s):
        if not s or s == '-':
            return None
        return float(s.replace(',','.'))

    def intorNone(self, i):
        if i is None:
            return i
        else:
            return int(i)

    def parseplayers(self, gameurl, gamedata, hometeam, awayteam):
        url = gameurl.replace('seuranta', 'tilastot')
        r = requests.get(url)
        page = html.fromstring(r.content)

        homerows = page.xpath("//div[@class='team home']//table[@class='player-stats']/tbody/tr")
        awayrows = page.xpath("//div[@class='team away']//table[@class='player-stats']/tbody/tr")
                
        ghomerows = page.xpath("//div[@class='team home']//table[@class='goalie-stats']/tbody/tr")
        gawayrows = page.xpath("//div[@class='team away']//table[@class='goalie-stats']/tbody/tr")


        for (team, rows) in [(hometeam, homerows),
                             (awayteam, awayrows)]:
            for r in rows:
                tds = r.xpath("td")
                pdata = tds[0].xpath("strong/a")[0]
                pid = pdata.attrib.get('href')
                pname = pdata.text
                values = [t.text for t in tds[1:]]
                player = PlayerData(
                    id=pid.replace('/pelaajat/',''),
                    gameid=gamedata.id,
                    season=gamedata.season,
                    name=pname,
                    number=int(values[0]),
                    team=team,
                    position=values[1],
                    goals=int(values[2]),
                    passes=int(values[3]),
                    points=int(values[4]),
                    penalties=int(values[5]),
                    plus=int(values[6]),
                    minus=int(values[7]),
                    plusminus=int(values[8]),
                    ppgoals=int(values[9]),
                    shgoals=int(values[10]),
                    wingoal=int(values[11]),
                    shots=int(values[12]),
                    shotpct=self.genpct(values[13]),
                    faceoffs=int(values[14]),
                    faceoffpct=self.genpct(values[15]),
                    playtime=values[16],
                )
                yield player

        for (team, rows) in [(hometeam, ghomerows),
                             (awayteam, gawayrows)]:
            for r in rows:
                tds = r.xpath("td")
                pdata = tds[0].xpath("strong/a")[0]
                pid = pdata.attrib.get('href')
                pname = pdata.text
                values = [t.text for t in tds[1:]]
                gk = GoalkeeperData(
                    id=pid.replace('/pelaajat/',''),
                    gameid=gamedata.id,
                    season=gamedata.season,
                    name=pname,
                    number=int(values[0]),
                    team=team,
                    saves=int(values[1]),
                    goalsagainst=int(values[2]),
                    savepct=self.genpct(values[3]),
                    goals=int(values[4]),
                    passes=int(values[5]),
                    points=int(values[6]),
                    penalties=int(values[7]),
                    playtime=values[8],
                )
                yield gk
                

    def parsegame(self, gameno, gamedate, gameurl, teams):
        url = urlparse.urljoin(self.url, gameurl)
        #print gameno, url
        identifier = url.split('/')[-3]
        dt = datetime.date(int(gamedate[:4]), int(gamedate[4:6]), int(gamedate[6:8]))
        if dt > datetime.date.today():
            return

        r = requests.get(url)
        page = html.fromstring(r.content)

        hometeam = self.teams[teams[0]].id
        awayteam = self.teams[teams[1]].id
        
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
            home = dict(score=homescore, points=homepoints, team=hometeam),
            away = dict(score=awayscore, points=awaypoints, team=awayteam),
            attendance=attendance,
            )
        yield gamedata

        playersbyname = {}
        for e in self.parseplayers(url, gamedata, hometeam, awayteam):
            player = dict(
                team = e.team, 
                id = e.id, 
                number = e.number
            )
            nname = " ".join(e.name.split(',')[::-1]).strip()
            playersbyname[(e.team, nname)] = player
            yield e

        periods = []
        for i in range(1,4):
            periods.append(dict(number=i, name=str(i)))
        if tm > '60:00':
            periods.append(dict(number=4, name='JA'))
        gamestats = dict()

        events = page.xpath("//div[@class='table']//tr")
        eventnum = 1
        category = None
        for e in events:
            ecls = e.attrib.get('class')
            if ecls in ['odd', 'even', 'period', 'shooting-stats odd', 'shooting-stats even']:
                tds = e.xpath("td")
                if tds and len(tds) == 3:
                    home, gtime, away = tds
                    if gtime.text and len(gtime.text) == 5 and gtime.text[2] == ':':
                        e = self.parsegameevent(gamedata, eventnum, home, gtime, away, playersbyname)
                        if e:
                            eventnum += 1
                            yield e
                    elif category == 'Aloitusvoitot':
                        hnums = [int(n) for n in home.text.split()[0::2]]
                        anums = [int(n) for n in away.text.split()[0::2]]
                        if len(hnums) == len(periods)+1 and len(anums) == len(periods)+1:
                            for (p, h, a) in zip(periods, hnums, anums):
                                p['homefaceoffs'] = h
                                p['awayfaceoffs'] = a
                        gamestats['homefaceoffs'] = hnums[-1]
                        gamestats['awayfaceoffs'] = anums[-1]
                            
                    elif category == 'Laukaisukartta':
                        if gtime.text == 'Maali':
                            attrname = 'score'
                        elif gtime.text == 'Ohi':
                            attrname = 'missed'
                        elif gtime.text == 'Torjuttu':
                            attrname = 'saved'
                        elif gtime.text == 'Blokattu':
                            attrname = 'blocked'
                        elif gtime.text.startswith('Yhteens'):
                            attrname = 'total'
                        for p in periods:
                            p['home%s' % attrname] = home.attrib.get('data-period%d' % p['number'], 0)
                            p['away%s' % attrname] = away.attrib.get('data-period%d' % p['number'], 0)

                        gamestats['home%s' % attrname] = int(home.text)
                        gamestats['away%s' % attrname] = int(away.text)


                    elif category == 'Maalivahdit':
                        pass

                elif ecls == 'period' and tds and len(tds) == 1:
                    category = tds[0].text

        shotdivs = page.xpath("//div[@class='shooting-map-container']/div")
        location = None
        for s in shotdivs:
            scls = s.attrib.get('class').split()
            if len(scls) == 4:
                (_, location, periodtxt, playertxt) = scls
            elif len(scls) == 5:
                (_, __, location, periodtxt, playertxt) = scls
            elif 'shot-tooltip' in scls:
                #print location, period, player
                shootername = s.text.strip().split(':')[-1].strip()
                (team, timetxt, resultxt) = [e.tail.strip().split(':', 1)[-1].strip() for e in s.xpath('br')]
                #print shooter, team, timetxt, resultxt
                blocker = None

                if not location:
                    print html.tostring(s)
                    print gamedata
                    raise Exception("No location")

                if location == 'home':
                    team = hometeam
                    vsteam = awayteam
                elif location == 'away':
                    team = awayteam
                    vsteam = hometeam
                else:
                    raise Exception("Unknown shot location '%s' (should be home or away)" % location)

                result = {
                    'Laukaus ohi maalin': 'miss',
                    'Maalivahti torjui': 'save',
                    'Maali': 'goal',
                    }.get(resultxt)

                shooter = playersbyname[(team, shootername)]

                if not result and 'blokkasi' in resultxt:
                    result = 'blocked'
                    blocker = playersbyname[(vsteam, resultxt[resultxt.index('(')+1:resultxt.index(')')])]

                if not result:
                    raise Exception("Unknown shot result '%s'" % resultxt)

                period = periodtxt.split('-')[-1]
                if period == '4':
                    period = 'JA'

                id = gamedata.id * 10000 + int(timetxt.replace(':',''))
                shot = GameEventData(
                    id = id,
                    season = gamedata.season,
                    gameid = gamedata.id,
                    time = timetxt,
                    eventtype = 'shot',
                    team = team,
                    vsteam = vsteam,
                    period = period,
                    location = location,
                    shooter = shooter,
                    blocker = blocker,
                    result = result,
                )
                yield shot

        homegamescore = 0
        awaygamescore = 0

        for p in periods + [gamestats]:
            homegamescore += int(p['homescore'])
            awaygamescore += int(p['awayscore'])
            pdict = dict(
                home = dict(
                    team=hometeam,
                    score=int(p['homescore']),
                    gamescore = homegamescore,
                    shots=int(p['hometotal']),
                    faceoffs=self.intorNone(p.get('homefaceoffs')),
                    blocked=self.intorNone(p.get('homeblocked')),
                    missed=int(p['homemissed']),
                    saved=int(p['homesaved']),
                ),
                away = dict(
                    team=awayteam,
                    score=int(p['awayscore']),
                    gamescore = awaygamescore,
                    shots=int(p['awaytotal']),
                    faceoffs=self.intorNone(p.get('awayfaceoffs')),
                    blocked=self.intorNone(p.get('awayblocked')),
                    missed=int(p['awaymissed']),
                    saved=int(p['awaysaved']),
                )
            )
            if 'number' in p:
                pd = PeriodData(
                    id=gamedata.id*100+p['number'],
                    gameid = gamedata.id,
                    season = gamedata.season,
                    period=p['name'],
                    **pdict)
                yield pd
            else:
                del pdict['home']['gamescore']
                del pdict['away']['gamescore']
                gamestats = GameStatsData(
                    id=gamedata.id,
                    gameid = gamedata.id,
                    season = gamedata.season,
                    **pdict)
                yield gamestats
                            
    def parsegameevent(self, gamedata, eventnum, home, gtime, away, playersbyname):
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
                #name=data[2],
                team=team,
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
            attrtext = players[-1][3].replace(')','').strip() + "," + strong.tail.replace('(', '')
            goalattr = []

            for attr in [m.strip() for m in attrtext.split(',') if m.strip()]:
                if attr == eventattr['score']:
                    continue

                if attr in ['YV', 'YV2', 'AV', 'AV2', 'VT', 'VM', 'TM', 'TV', 'IM', 'SR', 'RL']:
                    goalattr.append(attr)
                else:
                    raise Exception("Unknown game attr '%s'" % attr)
                    
            if gtime.text > '60:00':
                goalattr.append('JA')

            eventattr['goalattr'] = ' '.join(goalattr)
                

        elif strong is not None and not players:
            eventtype = 'goal'
            eventattr['scorer'] = dict(
                number=int(strong.text.strip()[1:]),
                id=playermeta[0][0].replace('/pelaajat/',''),
                #name=playermeta[0][1],
                team=team,
            )
            eventattr['assist1'] = None
            eventattr['assist2'] = None
            eventattr['score'] = playermeta[0][2]
            eventattr['goalattr'] = 'VL'

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
                eventattr['penaltyattr'] = 'teampenalty'
                

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
            eventattr['penaltyattr'] = 'teampenalty'

        elif 'Joukkuerangaistus' in elem.text:
            eventtype = 'penalty'
            words = elem.text.split()
            minindex = words.index('min')
            eventattr['minutes'] = int(words[minindex-1])
            eventattr['reason'] = " ".join(words[minindex+1:])
            eventattr['penaltyattr'] = 'teampenalty'
            eventattr['player'] = None
            eventattr['boxed'] = None

        elif 'aikalis' in elem.text:
            eventtype = 'timeout'

        elif 'Maalivahti ulos' in elem.text:
            eventtype = 'goalkeeper'
            eventattr['event'] ='out'
            eventattr['playerout'] = playerdata(players[0])
            eventattr['playerin'] = None

        elif 'Maalivahti sis' in elem.text:
            eventtype = 'goalkeeper'
            eventattr['event'] = 'in'
            eventattr['playerin'] = playerdata(players[0])
            eventattr['playerout'] = None

        elif 'Maalivahdin vaihto' in elem.text:
            if "ulos" in players[0][3]:
                eventtype = 'goalkeeper'
                eventattr['event'] = 'change'
                eventattr['playerout'] = playerdata(players[0])
                eventattr['playerin'] = playerdata(players[1])

        elif 'Videotarkistus - ei maalia' in elem.text:
            eventtype = 'videocheck'

        elif 'Rangaistuslaukaus - ei maalia' in elem.text:
            eventtype = 'penaltyshot'
            eventattr['scored'] = False
            pp = playersbyname[(team, elem.text[elem.text.index('(')+1:elem.text.index(')')])]
            eventattr['player'] = pp

        elif gtime.text == '65:00' and playermeta and not players:
            eventtype = 'penaltyshot'
            
            eventattr['player'] = dict(
                number=int(elem.text.strip()[1:]),
                id=playermeta[0][0].replace('/pelaajat/',''),
                #name=playermeta[0][1],
                team=team,
            )
            if "ei maalia" in playermeta[0][2]:
                eventattr['scored'] = False
            elif "maali" in playermeta[0][2]:
                eventattr['scored'] = True


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
            location=elem.attrib['class'],
            **eventattr
        )
            


if __name__ == "__main__":
    for url in sys.argv[1:]:
        parser = LGParser(url)
        for event in parser.parse():
            print event.tojson()
