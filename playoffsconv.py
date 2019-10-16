#!/usr/bin/env python

import json, sys, datetime

from liigagames import ParserData, GameData



class Data(object):
    def __init__(self, data):
        self._data = data
        for attr in data:
            value = data[attr]
            if type(value) is dict:
                value = Data(value)
            setattr(self, attr, value)

    def tojson(self):
        return json.dumps(self._data, indent=4, sort_keys=True)



def loader(path):
    with file(path) as fp:
        gameno = 900
        for l in fp:
            data = Data(json.loads(l))
            if data.type == "season":
                season = data
            elif data.type == "game":
                gameno = gameno + 1

                id = season.id*1000+gameno
                
                if data.time != '60:00':
                    resultattr = "JA"
                else:
                    resultattr = ""

                home = dict(score=data.home.score, team=data.home.team)
                away = dict(score=data.away.score, team=data.away.team)

                gamedata = GameData(
                    id=id,
                    number=gameno,
                    identifier=data.identifier,
                    date=data.date,
                    time='18:30',
                    season=season.years,
                    playoffs=True,
                    home=home,
                    away=away,
                    score=data.score,
                    resultattr=resultattr,
                )
                yield gamedata
                


if __name__ == "__main__":
    for a in sys.argv[1:]:
        for d in loader(a):
            print d.tojson()
