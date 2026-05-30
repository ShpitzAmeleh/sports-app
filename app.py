from flask import Flask, jsonify
import os
import urllib.request
import json
import re

app = Flask(__name__)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
SOCCER_LEAGUES = ['eng.1', 'fra.1', 'ger.1', 'esp.1', 'ita.1', 'uefa.champions']

def normalize_status(status, state=''):
    if not status and not state:
        return 'upcoming'
    s = f"{status} {state}".lower()
    if state in ('in', 'live') or any(key in s for key in ('in_progress', 'live', 'playing', 'halftime', '1st', '2nd', 'second half', 'first half', 'overtime', 'extra time', 'penalties', 'pen')):
        return 'live'
    if state in ('post', 'completed', 'complete', 'final', 'finished') or any(key in s for key in ('final', 'full_time', 'full time', 'post', 'complete', 'completed', 'ft', 'f/t', 'ended', 'after')):
        return 'finished'
    return 'upcoming'


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
                    status = comps.get('status', {})
                    status_name = status.get('type', {}).get('name') or status.get('type', {}).get('state') or ''
                    status_norm = normalize_status(status_name)
                    if status_norm == 'live':
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'live', 'homeScore': home.get('score','0'), 'awayScore': away.get('score','0')})
                    elif status_norm == 'finished':
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'finished', 'homeScore': home.get('score','0'), 'awayScore': away.get('score','0')})
                    else:
                        date = e.get('date','')
                        games.append({'home': home['team']['displayName'], 'away': away['team']['displayName'], 'status': 'upcoming', 'time': date})
        return games if games else fallback_nba()
    except Exception as ex:
        print('NBA error:', ex)
        return fallback_nba()

def fallback_nba():
    return [
        {'home': 'Oklahoma City Thunder', 'away': 'San Antonio Spurs', 'status': 'upcoming', 'time': 'Sun May 31, 3:00 AM - Game 7'},
        {'home': 'TBD', 'away': 'New York Knicks', 'status': 'upcoming', 'time': 'Thu Jun 4 - NBA Finals Game 1'},
        {'home': 'TBD', 'away': 'New York Knicks', 'status': 'upcoming', 'time': 'Sat Jun 6 - NBA Finals Game 2'},
        {'home': 'New York Knicks', 'away': 'TBD', 'status': 'upcoming', 'time': 'Tue Jun 9 - NBA Finals Game 3'},
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
            events.append({'home': name, 'away': '', 'status': 'upcoming', 'time': date})
        return events if events else fallback_ufc()
    except Exception as ex:
        print('UFC error:', ex)
        return fallback_ufc()

def fallback_ufc():
    return [
        {'home': 'UFC 316', 'away': 'Islam Makhachev vs Arman Tsarukyan', 'status': 'upcoming', 'time': 'Sat May 30, 2026'},
        {'home': 'UFC 317', 'away': 'Card TBD', 'status': 'upcoming', 'time': 'Sat Jun 7, 2026'},
        {'home': 'UFC Fight Night', 'away': 'Card TBD', 'status': 'upcoming', 'time': 'Sat Jun 14, 2026'},
        {'home': 'UFC Fight Night', 'away': 'Card TBD', 'status': 'upcoming', 'time': 'Sat Jun 21, 2026'},
    ]

def get_soccer():
    games = []
    seen = set()
    for league in SOCCER_LEAGUES:
        try:
            url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/league/scoreboard?league={league}'
            data = json.loads(fetch(url))
            league_name = data.get('leagues', [{}])[0].get('name', league)
            for e in data.get('events', [])[:30]:
                comps = e.get('competitions', [{}])[0]
                competitors = comps.get('competitors', [])
                if len(competitors) != 2:
                    continue
                home = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                away = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
                match_key = (home.get('team', {}).get('id'), away.get('team', {}).get('id'), e.get('date') or comps.get('date', ''))
                if match_key in seen:
                    continue
                seen.add(match_key)
                status = comps.get('status', {})
                status_type = status.get('type', {})
                status_name = status_type.get('name') or status_type.get('description') or status_type.get('detail') or ''
                status_state = status_type.get('state') or ''
                status_norm = normalize_status(status_name, status_state)
                game = {
                    'home': home.get('team', {}).get('displayName', 'Home'),
                    'away': away.get('team', {}).get('displayName', 'Away'),
                    'status': status_norm,
                    'homeScore': home.get('score', '0'),
                    'awayScore': away.get('score', '0'),
                    'league': league_name,
                    'time': e.get('date') or comps.get('date', ''),
                    'clock': status.get('displayClock') or status_type.get('detail') or status_type.get('shortDetail') or '',
                    'statusDetail': status_type.get('detail') or status_type.get('description') or '',
                }
                games.append(game)
        except Exception as ex:
            print(f'Soccer league fetch error for {league}:', ex)
            continue
    return games if games else fallback_soccer()

def fallback_soccer():
    return [
        {'home': 'PSG', 'away': 'Arsenal', 'status': 'upcoming', 'time': 'Today 19:00', 'league': 'Champions League Final'},
        {'home': 'World Cup 2026', 'away': 'Group Stage Begins', 'status': 'upcoming', 'time': 'Thu Jun 11, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Round of 16', 'status': 'upcoming', 'time': 'Sat Jun 27, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Quarter Finals', 'status': 'upcoming', 'time': 'Fri Jul 3, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Semi Finals', 'status': 'upcoming', 'time': 'Tue Jul 14, 2026', 'league': 'FIFA World Cup'},
        {'home': 'World Cup 2026', 'away': 'Final', 'status': 'upcoming', 'time': 'Sun Jul 19, 2026', 'league': 'FIFA World Cup'},
        {'home': 'Brighton', 'away': 'Man United', 'status': 'finished', 'homeScore': 0, 'awayScore': 3, 'league': 'Premier League'},
        {'home': 'Crystal Palace', 'away': 'Arsenal', 'status': 'finished', 'homeScore': 1, 'awayScore': 2, 'league': 'Premier League'},
        {'home': 'Man City', 'away': 'Aston Villa', 'status': 'finished', 'homeScore': 1, 'awayScore': 2, 'league': 'Premier League'},
        {'home': 'Sunderland', 'away': 'Chelsea', 'status': 'finished', 'homeScore': 2, 'awayScore': 1, 'league': 'Premier League'},
    ]

def get_news():
    try:
        html = fetch('https://www.espn.com')
        items = []
        # find anchors and headlines
        matches = re.findall(r'<a[^>]+href="([^\"]+)"[^>]*>(.*?)</a>', html, re.DOTALL|re.IGNORECASE)
        whitelist = ['espn.com', 'www.espn.com', 'nba.com', 'www.nba.com', 'ufc.com', 'www.ufc.com', 'mlb.com', 'nhl.com']
        for href, text in matches:
            title = re.sub(r'<[^>]+>', '', text).strip()
            if not title: continue
            lower = title.lower()
            if any(k in lower for k in ('injury', 'injuries', 'injured', 'trade', 'traded')):
                # normalize href
                if href.startswith('//'):
                    href = 'https:' + href
                if href.startswith('/'):
                    href = 'https://www.espn.com' + href
                domain_match = re.match(r'https?://([^/]+)', href)
                domain = domain_match.group(1) if domain_match else ''
                if any(w in domain for w in whitelist):
                    items.append({'title': title, 'link': href, 'source': domain})
        # dedupe by link
        seen = set()
        out = []
        for it in items:
            if it['link'] in seen: continue
            seen.add(it['link'])
            out.append(it)
            if len(out) >= 20: break
        return out
    except Exception as ex:
        print('News error:', ex)
        return []


@app.route('/api/news')
def news():
    items = get_news()
    return jsonify({'news': items})

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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))