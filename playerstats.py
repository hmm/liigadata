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

class PlayerMetaData(ParserData):
    type = 'playermeta'

class OtherSeriesData(ParserData):
    type = 'otherseries'


class PlayerStatsParser(object):
    baseurl = "http://liiga.fi/tilastot/{season}/{serie}/pelaajat/?team={team}&position=all&player_stats=players&sort=P#stats-wrapper"
    seasonsurl = "http://liiga.fi/tilastot/kaikki/runkosarja/pelaajat/"

    teamsmapping = {
        'Pelicans': ('Kiekkoreipas', 'kiekkoreipas'),
        'Kiekkoreipas': ('Hockey-Reipas', 'hockey-reipas'),
        'Hockey-Reipas': ('Reipas', 'reipas'),
        'JYP': ('JyP HT', 'jyp-ht'),
        'Blues': ('Kiekko-Espoo', 'kiekko-espoo'),
        'FPS': ('FoPS', 'fops'),
        'Jokipojat': ('JoKP', 'jokp'),
    }

    def __init__(self):
        for season in self.parseseasons():
            url = self.baseurl.format(season=season, serie='runkosarja', team='')

            for (team, teamname) in self.parseteams(url):
                url = self.baseurl.format(season=season, serie='runkosarja', team=team)
                #print "URL", season, team, teamname, url
                for p in self.parseplayers(team, teamname, season, False, url):
                    print p.tojson()
                     
            url = self.baseurl.format(season=season, serie='playoffs', team='')

            for (team, teamname) in self.parseteams(url):
                url = self.baseurl.format(season=season, serie='playoffs', team=team)
                #print "URL", season, team, teamname, url
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
                (fixedname, fixedid) = self.teamsmapping.get(teamname, (None, None))
                if fixedname != team:
                    #print "DISCARD", team, teamname, fixedname
                    continue
                else:
                    teamid = fixedid
                    
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
                playerid = playerid.replace('/fi/pelaajat/',''),
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


class PlayerDataParser(object):
    baseurl = "http://liiga.fi/tilastot/{season}/{serie}/pelaajat/?team={team}&position=all&player_stats=players&sort=P#stats-wrapper"
    seasonsurl = "http://liiga.fi/tilastot/kaikki/runkosarja/pelaajat/"
    playerurl = "http://liiga.fi/fi/pelaajat/{playerid}"

    teamsmapping = {
        u'JyP HT'        : 'jyp-ht',
        u'Jokerit'       : 'jokerit',
        u'Kiekko-Espoo'  : 'kiekko-espoo',
        u'Olympia-84'    : 'olympia-84',
        u'Blues'         : 'blues',
        u'Kiekkoreipas'  : 'kiekkoreipas',
        u'Hockey-Reipas' : 'hockey-reipas',
        u'FoPS'          : 'fops',
        u'JoKP'          : 'jokp',
        u'HIFK'          : 'hifk',
        u'HPK'           : 'hpk',
        u'Ilves'         : 'ilves',
        u'Jukurit'       : 'jukurit',
        u'JYP'           : 'jyp',
        u'KalPa'         : 'kalpa',
        u'KooKoo'        : 'kookoo',
        u'Kärpät'        : 'karpat',
        u'Lukko'         : 'lukko',
        u'Pelicans'      : 'pelicans',
        u'SaiPa'         : 'saipa',
        u'Sport'         : 'sport',
        u'Tappara'       : 'tappara',
        u'TPS'           : 'tps',
        u'Ässät'         : 'assat',
        u'Reipas'        : 'reipas',
        u'KOO-VEE'       : 'koo-vee',
        u'TuTo'          : 'tuto',
        u'Jokipojat'     : 'jokp',
    }

    teamsmapping2 = {
        'Pelicans': ('Kiekkoreipas', 'kiekkoreipas'),
        'Kiekkoreipas': ('Hockey-Reipas', 'hockey-reipas'),
        'Hockey-Reipas': ('Reipas', 'reipas'),
        'JYP': ('JyP HT', 'jyp-ht'),
        'Blues': ('Kiekko-Espoo', 'kiekko-espoo'),
        'FPS': ('FoPS', 'fops'),
        'Jokipojat': ('JoKP', 'jokp'),
    }


    def __init__(self, seasonparam=None):
        self.parsedplayers = []
        for season in self.parseseasons(seasonparam):
            seriesurl = self.baseurl.format(season=season, serie='runkosarja', team='')
            playoffsurl = self.baseurl.format(season=season, serie='playoffs', team='')
            #print season, seriesurl, playoffsurl

            for p in self.parseplayers(seriesurl):
                if p not in self.parsedplayers:
                    url = self.playerurl.format(playerid=p)
                    for data in self.parseplayer(url, p):
                        print data.tojson()
                    
                    self.parsedplayers.append(p)
                     

            for p in self.parseplayers(playoffsurl):
                if p not in self.parsedplayers:
                    url = self.playerurl.format(playerid=p)
                    self.parseplayer(url, p)
                    for data in self.parseplayer(url, p):
                        print data.tojson()
                    self.parsedplayers.append(p)

            for (team, teamname) in self.parseteams(seriesurl):
                teamurl = self.baseurl.format(season=season, serie='runkosarja', team=team)
                for p in self.parsekeepers(team, teamname, season, False, teamurl):
                    print p.tojson()

            for (team, teamname) in self.parseteams(playoffsurl):
                teamurl = self.baseurl.format(season=season, serie='playoffs', team=team)
                for p in self.parsekeepers(team, teamname, season, True, teamurl):
                    print p.tojson()


    def parseseasons(self, season=None):
        if season:
            yield "%d-%d" % (season-1, season)
            return

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
    
        
    def parseplayers(self, url):
        r = requests.get(url)
        page = html.fromstring(r.content)

        stats = page.xpath("//table[@id='stats']/tbody/tr")
        for tr in stats:
            tds = tr.xpath("td")
            playerelem = tr.xpath("td[@class='ta-l']/a")
            if playerelem:
                player = playerelem[0]
                playerid = player.attrib.get('href')
                yield playerid.replace('/fi/pelaajat/','')

    posmapping = {
        u'Hyökkääjä': 'H',
        u'Puolustaja': 'P',
        u'Maalivahti': 'MV',
        u'Vasen laitahyökkääjä': 'VH',
        u'Oikea laitahyökkääjä': 'OH',
        u'Keskushyökkääjä': 'KH',
        u'Vasen puolustaja': 'VP',
        u'Oikea puolustaja': 'OP',
        u'-': None,
    }
                
    def parseplayer(self, url, playerid):
        r = requests.get(url)
        page = html.fromstring(r.content)
        h1 = page.xpath("//div[@id='page']/h1")[0]
        title = h1.text.strip()
        if title[0] == '#':
            (num, name) = title.split(' ', 1)
            number = num[1:]
        else:
            number = None
            name = title

        meta = {}
        for tr in page.xpath("//table[@id='player-info']/tr"):
            attr = tr.xpath("th")[0].text.strip()
            value = tr.xpath("td")[0].text.strip()
            if attr == "Pelipaikka":
                position = self.posmapping[value]
            elif attr == 'Syntynyt':
                if value == '-':
                    born = None
                else:
                    (d,m,y) = [int(v) for v in value.split('.')]
                    born = "%d-%02d-%02d" % (y, m, d)
            elif attr == 'Kansalaisuus':
                nationality = self.strvalue(value)
            elif attr == u'Syntymäpaikka':
                homecity = self.strvalue(value)
            elif attr == 'Pituus':
                height = self.intvalue(value)
            elif attr == "Paino":
                weight = self.intvalue(value)
            elif attr == "Maila":
                stick = self.strvalue(value)

        metadata = PlayerMetaData(
            playerid = playerid,
            name = name,
            number = number,
            position = position,
            nationality = nationality,
            homecity = homecity,
            height = height,
            weight = weight,
            stick = stick,
            born = born
        )
        yield metadata

        seasonteams = {}

        tables = page.xpath("//div[@id='stats-section']//table")
        #print "TABLE", playerid, tables, position
        if not tables or position == 'MV':
            return

        for tbl in tables:
          for elem in tbl.iterchildren():
            #print "ELEM", elem.attrib.get('class'), elem.tag
            if elem.attrib.get('class') == 'header':
                th = elem.xpath('tr/th')[0].text.strip()
                #print "TH", th
                inseries = (th == 'Runkosarja')
                playoffs = (th == 'Playoffs')
            elif elem.tag == 'table' and inseries or playoffs:
                #print "TABLE"
                stats = elem.xpath("tbody/tr")

                lastseason = None
                
                for tr in stats:
                    tds = tr.xpath("td")
                    season = tds[0].text.strip()
                    if season == u'Yhteensä':
                        break
                    if not season:
                        season = lastseason
                    lastseason = season
                    series = tds[2].text.strip()
                    team = tds[1].text.strip()

                    if series != 'FIN':
                        other = OtherSeriesData(
                            playerid = playerid,
                            season = season,
                            series = series,
                            team = team
                        )
                        yield other
                        continue

                    if not playoffs:
                        teamid = self.teamsmapping[team]
                        seasonteams[season] = teamid
                    else:
                        if season in seasonteams:
                            teamid = seasonteams[season]
                        else:
                            teamid = self.teamsmapping[team]
                        
                    games = tds[3].text.strip()
                    goals = tds[4].text.strip()
                    assists = tds[5].text.strip()
                    points = tds[6].text.strip()
                    penalties = tds[7].text.strip()

                    plus = self.intvalue(tds[8].text.strip())
                    minus = self.intvalue(tds[9].text.strip())
                    plusminus = self.intvalue(tds[10].text.strip())

                    ppgoals = self.intvalue(tds[11].text.strip())
                    shgoals = self.intvalue(tds[12].text.strip())
                    wingoals = self.intvalue(tds[13].text.strip())
            
                    shots = self.intvalue(tds[14].text.strip())
                    shotpct = self.pctvalue(tds[15].text.strip())


                    data = PlayerStatsData(
                        playerid = playerid,
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
                        
                    )
                    yield data
            

    def parsekeepers(self, teamid, teamname, season, playoffs, url):
        #print "KEEPERS", teamid, teamname, season, playoffs, url
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
                (fixedname, fixedid) = self.teamsmapping2.get(teamname, (None, None))
                if fixedname != team:
                    #print "DISCARD", team, teamname, fixedname
                    continue
                else:
                    teamid = fixedid
                    
            poselem = tds[3].text
            if poselem:
                position = self.strvalue(poselem.strip())

            if position != 'MV':
                continue
            
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
                playerid = playerid.replace('/fi/pelaajat/',''),
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
                shotpct = shotpct
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
    season = None
    if len(sys.argv) > 2:
        season = int(sys.argv[2])
    if urltype == 'players':
        parser = PlayerStatsParser()
    elif urltype == 'playerdata':
        if season:
            parser = PlayerDataParser(season)
        else:
            parser = PlayerDataParser()

