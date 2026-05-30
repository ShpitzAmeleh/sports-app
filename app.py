from flask import Flask, jsonify
import urllib.request
import json
import re

app = Flask(__name__)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode('utf-8')

def get_nba():
    try:
        html = fetch('https://www.espn.com/nba/scoreboard')
        games = []
        # חפש משחקים בJSON שטמון בדף
        match = re.search(r'"events":(\[.*?\])', html)
        if match:
            events = json.loads(match.group(1))
            for e in events[:10]:
                comps = e.get('competitions', [{}])[0]
                competitors = comps.get('competitors', [])
                if len(competitors) == 2:
                    home = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                    away = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
                    status = comps.get('status', {}).get('type', {}).get('name', '')
                    if status == 'STATUS_IN_PROGRESS':
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'live', 'homeScore': home.get('score','0'), 'awayScore': away.get('score','0')})
                    elif status == 'STATUS_FINAL':
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'finished', 'homeScore': home.get('score','0'), 'awayScore': away.get('score','0')})
                    else:
                        date = e.get('date','')
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'scheduled', 'time': date})
        return games if games else fallback_nba()
    except Exception as ex:
        print('NBA error:', ex)
        return fallback_nba()

def fallback_nba():
    return [
        {'home': 'Oklahoma City Thunder', 'away': 'San Antonio Spurs', 'status': 'scheduled', 'time': 'Sun May 31, 3:00 AM - Game 7'},
        {'home': 'TBD', 'away': 'New York Knicks', 'status': 'scheduled', 'time': 'Thu Jun 4 - NBA Finals Game 1'},
        {'home': 'TBD', 'away': 'New York Knicks', 'status': 'scheduled', 'time': 'Sat Jun 6 - NBA Finals Game 2'},
        {'home': 'New York Knicks', 'away': 'TBD', 'status': 'scheduled', 'time': 'Tue Jun 9 - NBA Finals Game 3'},
        {'home': 'San Antonio Spurs', 'away': 'OKC Thunder', 'status': 'finished', 'homeScore': 118, 'awayScore': 91},
        {'home': 'New York Knicks', 'away': 'Cleveland', 'status': 'finished', 'homeScore': 130, 'awayScore': 93},
    ]

def get_ufc():
    try:
        html = fetch('https://www.ufc.com/events')
        events = []
        matches = re.findall(r'<h3[^>]*class="[^"]*c-card-event--result__headline[^"]*"[^>]*>(.*?)</h3>.*?<div[^>]*class="[^"]*c-card-event--result__date[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        for name, date in matches[:6]:
            name = re.sub(r'<[^>]+>', '', name).strip()
            date = re.sub(r'<[^>]+>', '', date).strip()
            events.append({'home': name, 'away': '', 'status': 'scheduled', 'time': date})
        return events if events else fallback_ufc()
    except Exception as ex:
        print('UFC error:', ex)
        return fallback_ufc()

def fallback_ufc():
    return [
        {'home': 'UFC 316', 'away': 'Islam Makhachev vs Arman Tsarukyan', 'status': 'scheduled', 'time': 'Sat May 30, 2026'},
        {'home': 'UFC 317', 'away': 'Card TBD', 'status': 'scheduled', 'time': 'Sat Jun 7, 2026'},
        {'home': 'UFC Fight Night', 'away': 'Card TBD', 'status': 'scheduled', 'time': 'Sat Jun 14, 2026'},
        {'home': 'UFC Fight Night', 'away': 'Card TBD', 'status': 'scheduled', 'time': 'Sat Jun 21, 2026'},
    ]

def get_soccer():
    try:
        html = fetch('https://www.espn.com/soccer/scoreboard')
        games = []
        match = re.search(r'"events":(\[.*?\])', html)
        if match:
            events = json.loads(match.group(1))
            for e in events[:15]:
                comps = e.get('competitions', [{}])[0]
                competitors = comps.get('competitors', [])
                league_name = e.get('season', {}).get('slug', '')
                if len(competitors) == 2:
                    home = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                    away = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
                    status = comps.get('status', {}).get('type', {}).get('name', '')
                    if status == 'STATUS_IN_PROGRESS':
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'live', 'homeScore': home.get('score','0'), 'awayScore': away.get('score','0'), 'league': league_name})
                    elif status == 'STATUS_FINAL':
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'finished', 'homeScore': home.get('score','0'), 'awayScore': away.get('score','0'), 'league': league_name})
                    else:
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'scheduled', 'time': e.get('date','TBD'), 'league': league_name})
        return games if games else fallback_soccer()
    except Exception as ex:
        print('Soccer error:', ex)
        return fallback_soccer()

def fallback_soccer():
    return [
        {'home': 'PSG', 'away': 'Arsenal', 'status': 'scheduled', 'time': 'Today 19:00', 'league': 'Champions League Final'},
        {'home': 'World Cup 2026', 'away': 'Group Stage Begins', 'status': 'scheduled', 'time': 'Thu Jun 11, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Round of 16', 'status': 'scheduled', 'time': 'Sat Jun 27, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Quarter Finals', 'status': 'scheduled', 'time': 'Fri Jul 3, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Semi Finals', 'status': 'scheduled', 'time': 'Tue Jul 14, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Final', 'status': 'scheduled', 'time': 'Sun Jul 19, 2026', 'league': 'FIFA World Cup'},
        {'home': 'Brighton', 'away': 'Man United', 'status': 'finished', 'homeScore': 0, 'awayScore': 3, 'league': 'Premier League'},
        {'home': 'Crystal Palace', 'away': 'Arsenal', 'status': 'finished', 'homeScore': 1, 'awayScore': 2, 'league': 'Premier League'},
        {'home': 'Man City', 'away': 'Aston Villa', 'status': 'finished', 'homeScore': 1, 'awayScore': 2, 'league': 'Premier League'},
        {'home': 'Sunderland', 'away': 'Chelsea', 'status': 'finished', 'homeScore': 2, 'awayScore': 1, 'league': 'Premier League'},
    ]

@app.route('/')
def home():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/scores/<league>')
def scores(league):
    if league == 'nba':
        games = get_nba()
    elif league == 'ufc':
        games = get_ufc()
    elif league == 'soccer':
        games = get_soccer()
    else:
        games = []
    return jsonify({'league': league, 'games': games})

if __name__ == '__main__':
    app.run(debug=True)