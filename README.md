# liigadata
Utility for parsing Finnish ice hockey league game data from liiga.fi website

Output is series of json structures separated by a newline containing game results, game events (goals & penalties) etc.

Usage:

Series parsing:
    python liigaparser.py season http://liiga.fi/ottelut/2019-2020/runkosarja/

Playoffs parsing:
    python liigaparser.py playoffs http://liiga.fi/ottelut/2018-2019/playoffs/

Get all liiga seasons game results:
    python liigagames.py history

