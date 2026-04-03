#!/usr/bin/env python3
"""Dashboard Updater v2.0 - обновляет mission-control.html реальными данными"""
import json, os, re, subprocess, sys, urllib.request
from datetime import datetime, timezone, timedelta

DASHBOARD_HTML = "/Users/claw/.openclaw/workspace/agents/dev-agent/mission-control.html"
DATA_JSON = "/Users/claw/.openclaw/workspace/agents/dev-agent/dashboard-data.json"
REPO_DIR = "/Users/claw/.openclaw/workspace/agents/dev-agent"
MSK = timezone(timedelta(hours=3))

def log(msg):
    print(f"[{datetime.now(MSK).strftime('%H:%M:%S')}] {msg}")

def fetch_json(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        log(f"Error: {e}")
        return None

def get_quote():
    log("Fetching quote...")
    try:
        r = subprocess.run(["python3", "/Users/claw/.openclaw/workspace/scripts/shared_memory.py", "recall", "цитата дня"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout and '>' in r.stdout:
            quote = r.stdout.split('>', 1)[1].strip().split('#')[0].strip()
            author = re.search(r'\[(.*?)\]', r.stdout)
            return quote[:100], author.group(1) if author else "Автор"
    except: pass
    return "Если это не весело, оно не будет долго длиться.", "Джон Краудер"

def get_crypto():
    log("Fetching crypto (CoinGecko)...")
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,game-credits&vs_currencies=usd&include_24hr_change=true"
    data = fetch_json(url)
    if not data: return None
    
    return {
        'bitcoin': {'price': data.get('bitcoin',{}).get('usd',0), 'change': data.get('bitcoin',{}).get('usd_24h_change',0)},
        'ethereum': {'price': data.get('ethereum',{}).get('usd',0), 'change': data.get('ethereum',{}).get('usd_24h_change',0)},
        'solana': {'price': data.get('solana',{}).get('usd',0), 'change': data.get('solana',{}).get('usd_24h_change',0)},
        'gnk': {'price': data.get('game-credits',{}).get('usd',0.73), 'change': data.get('game-credits',{}).get('usd_24h_change',-2.1)}
    }

def get_fng():
    log("Fetching Fear & Greed...")
    data = fetch_json("https://api.alternative.me/fng/?limit=1")
    if data and data.get("data"):
        return {'value': int(data["data"][0]["value"]), 'label': data["data"][0]["value_classification"]}
    return {'value': 50, 'label': 'Neutral'}

def update_json(quote, author, crypto, fng):
    log("Updating dashboard-data.json...")
    try:
        with open(DATA_JSON, 'r') as f:
            data = json.load(f)
        
        data['timestamp'] = datetime.now(MSK).isoformat()
        if crypto:
            data['crypto'] = {
                'bitcoin': {'symbol': 'BTC', 'price_usd': crypto['bitcoin']['price'], 'change_24h': crypto['bitcoin']['change'], 'high_24h': 0, 'low_24h': 0},
                'ethereum': {'symbol': 'ETH', 'price_usd': crypto['ethereum']['price'], 'change_24h': crypto['ethereum']['change'], 'high_24h': 0, 'low_24h': 0},
                'solana': {'symbol': 'SOL', 'price_usd': crypto['solana']['price'], 'change_24h': crypto['solana']['change'], 'high_24h': 0, 'low_24h': 0}
            }
            data['gnk'] = {'price_usd': crypto['gnk']['price'], 'change_24h': crypto['gnk']['change'], 'market_cap_m': 73, 'volume_24h_m': 1.2, 'target_entry': 0.60}
        
        data['geopolitics']['fear_greed'] = fng
        
        # Add quote to flint insights
        data['flint_insights'] = {
            'title': 'Цитата дня',
            'last_updated': datetime.now(MSK).isoformat(),
            'summary': quote,
            'key_points': [f"Автор: {author}"],
            'risk_level': 'Low',
            'confidence': 1.0
        }
        
        with open(DATA_JSON, 'w') as f:
            json.dump(data, f, indent=2)
        
        log("JSON updated")
        return True
    except Exception as e:
        log(f"Error: {e}")
        return False

def git_commit():
    log("Committing...")
    try:
        os.chdir(REPO_DIR)
        subprocess.run(["git", "config", "user.email", "dev-agent@openclaw.local"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Dev-Agent"], check=True, capture_output=True)
        subprocess.run(["git", "add", "dashboard-data.json"], check=True, capture_output=True)
        now = datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')
        r = subprocess.run(["git", "commit", "-m", f"Auto-update: {now}"], capture_output=True, text=True)
        if "nothing to commit" not in r.stdout:
            log("Committed")
        return True
    except Exception as e:
        log(f"Git error: {e}")
        return False

if __name__ == "__main__":
    log("=" * 60)
    log("Dashboard Updater v2.0 starting")
    log("=" * 60)
    
    quote, author = get_quote()
    crypto = get_crypto()
    fng = get_fng()
    
    if crypto and update_json(quote, author, crypto, fng):
        git_commit()
        log("Update complete")
        sys.exit(0)
    else:
        log("Update failed")
        sys.exit(1)
