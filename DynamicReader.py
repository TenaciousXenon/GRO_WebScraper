import pandas as pd
import time
import json
import subprocess
from urllib.parse import urlparse
import asyncio
import aiohttp
from collections import defaultdict
import re
import requests
from concurrent.futures import ThreadPoolExecutor

# --- Selenium imports for dynamic fallback ---
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# NOTE: pandas, subprocess, selenium, numpy must be downloaded in environment 

# -------------------------------------------------------------------
# FALLBACK #2: Pure-HTML regex parse of <script> & <noscript> tags
# -------------------------------------------------------------------
def fetch_gtm_ids_from_html(url):
    """
    Synchronous fallback to grab GTM IDs directly from raw page HTML.
    """
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        html = r.text
        ids = set(re.findall(r'gtm\\.js\\?id=(GTM-[A-Z0-9\\-]{4,})', html, re.IGNORECASE))
        ids |= set(re.findall(r'ns\\.html\\?id=(GTM-[A-Z0-9\\-]{4,})', html, re.IGNORECASE))
        return list(ids)
    except Exception:
        return []

# -------------------------------------------------------------------
# FALLBACK: Selenium-based GTM extractor for dynamically-injected snippets
# -------------------------------------------------------------------
def extract_gtm_id_selenium(url):
    """
    Spin up headless Chrome, enable CDP network logs, wait for scripts,
    and extract GTM IDs from performance logs and final page_source.
    """
    chrome_options = Options()
    # “new” headless often performs more like real Chrome
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.set_capability("pageLoadStrategy", "eager")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(60)

    found_ids = set()
    try:
        # Enable Network DevTools protocol before navigating
        driver.execute_cdp_cmd("Network.enable", {})

        try:
            driver.get(url)
        except TimeoutException:
            print(f"[WARN] Page load timed out for {url}, continuing anyway")

        # Wait up to 10 seconds for a GTM snippet to appear in the DOM
        # This helps ensure the async snippet has time to load
        max_wait = 10
        start_time = time.time()
        while time.time() - start_time < max_wait:
            # collect any IDs from performance logs first
            for entry in driver.get_log("performance"):
                try:
                    msg = json.loads(entry["message"])["message"]
                except (json.JSONDecodeError, KeyError):
                    continue
                if msg.get("method") == "Network.requestWillBeSent":
                    req_url = msg["params"]["request"].get("url", "")
                    m = re.search(r"id=(GTM-[A-Z0-9\\-]{4,})", req_url)
                    if m:
                        found_ids.add(m.group(1))

            # parse final page_source
            page_source = driver.page_source or ""
            for tag in re.findall(r'gtm\\.js\\?id=(GTM-[A-Z0-9\\-]{4,})', page_source, re.IGNORECASE):
                found_ids.add(tag)
            for tag in re.findall(r'ns\\.html\\?id=(GTM-[A-Z0-9\\-]{4,})', page_source, re.IGNORECASE):
                found_ids.add(tag)

            if found_ids:
                break
            time.sleep(1)

    except WebDriverException as e:
        print(f"[WARN] Selenium fallback failed for {url}: {e}")
    finally:
        driver.quit()

    return list(found_ids)

# limit concurrent Selenium sessions
SEL_FALLBACK_SEMAPHORE = asyncio.Semaphore(3)

def extract_main_domain(url):
    """Extract the main domain using manual parsing."""
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    parsed = urlparse(url)
    netloc = parsed.netloc.split(':')[0]
    while netloc.startswith('www.'):
        netloc = netloc[4:]
    parts = netloc.split('.')
    return '.'.join(parts[-2:]).lower() if len(parts) >= 2 else netloc.lower()

def get_filtered_subdomains(domain):
    """
    Run subfinder for a domain, then filter out unwanted subdomains.
    Returns a list of subdomain URLs with `https://` prefix.
    """
    try:
        result = subprocess.run(
            ['subfinder', '-d', domain, '-silent'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"[WARN] Subfinder error for {domain}: {result.stderr}")
            return []
        raw = result.stdout.splitlines()
        exclude = {
            'www.', 'ns.', 'mail.', 'webdisk.', 'cpanel.',
            'cpcalenders.', 'webmail.', 'cpcontacts.',
            'rent.', 'rentnow.', 'ww2.', 'autodiscover.',
            'email.', 'lp.', 'child.', 'cpcalendars',
            'dev.', 'landing.'
        }
        out = []
        for sub in raw:
            host = urlparse(sub).netloc if sub.startswith('http') else sub.split('/')[0]
            host = host.split(':')[0]
            if host.endswith(domain) and not any(host.startswith(p) for p in exclude):
                out.append(f"https://{host}")
        return out
    except Exception as e:
        print(f"[WARN] Error processing subdomains for {domain}: {e}")
        return []

async def fetch_gtm_ids(session, url):
    """
    Fetch GTM IDs by HTTP GET first, then fallback:
      1) Selenium
      2) Pure-HTML regex
    """
    headers = {'User-Agent': 'Mozilla/5.0'}
    found = set()

    # 1) HTTP GET + regex on <script> & <noscript>
    try:
        async with session.get(url, headers=headers, allow_redirects=True, timeout=20) as resp:
            final = str(resp.url)
            if 'gtm.js' in final and 'id=' in final:
                m = re.search(r'id=(GTM-[A-Z0-9\\-]{4,})', final)
                if m:
                    found.add(m.group(1))
            for h in resp.history:
                u = str(h.url)
                if 'gtm.js' in u and 'id=' in u:
                    m = re.search(r'id=(GTM-[A-Z0-9\\-]{4,})', u)
                    if m:
                        found.add(m.group(1))
            text = await resp.text()
            for tag in re.findall(r'gtm\\.js\\?id=(GTM-[A-Z0-9\\-]{4,})', text, re.IGNORECASE):
                found.add(tag)
            for tag in re.findall(r'ns\\.html\\?id=(GTM-[A-Z0-9\\-]{4,})', text, re.IGNORECASE):
                found.add(tag)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        print(f"[WARN] HTTP issue for {url}; will try Selenium")
    except Exception as e:
        print(f"[WARN] Unhandled HTTP exception for {url}: {e}")

    if found:
        return list(found)

    # 2) Selenium fallback
    print(f"[INFO] Selenium fallback for {url}")
    async with SEL_FALLBACK_SEMAPHORE:
        loop = asyncio.get_running_loop()
        ids = await loop.run_in_executor(None, extract_gtm_id_selenium, url) or []
    if ids:
        return ids

    # 3) HTML-regex fallback
    print(f"[INFO] HTML-regex fallback for {url}")
    return fetch_gtm_ids_from_html(url)

async def process_url_gtm(session, url, results):
    ids = await fetch_gtm_ids(session, url)
    if ids:
        results[url].extend(ids)

async def process_domain_gtm(base_domain, subdomains):
    """
    Prune subdomains by HEAD check, then GET+fallback for GTM.
    """
    connector = aiohttp.TCPConnector(limit_per_host=5)
    headers = {'User-Agent': 'Mozilla/5.0'}
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        urls = [f"https://{base_domain}"] + subdomains

        live = []
        for u in urls:
            try:
                async with session.head(u, timeout=5, allow_redirects=True) as r:
                    if 200 <= r.status < 400:
                        live.append(u)
            except Exception:
                pass

        if not live:
            return []

        results = defaultdict(list)
        await asyncio.gather(*(process_url_gtm(session, u, results) for u in live))
        return list({tag for tags in results.values() for tag in tags})

async def main_gtm_processing(domain_dict):
    print("[INFO] Starting GTM ID discovery...")
    sem = asyncio.Semaphore(10)

    async def handle(idx, entry):
        async with sem:
            if entry['website'] == 'N/A':
                entry['discovered_gtm_ids'] = []
            else:
                entry['discovered_gtm_ids'] = await process_domain_gtm(
                    entry['base_domain'], entry.get('found_subdomains', [])
                )

    await asyncio.gather(*(handle(i, e) for i, e in domain_dict.items()))
    print("[INFO] GTM ID discovery complete!\n")

def debug_fallback_live(url):
    """
    Do a final pass in non-headless mode, capturing gtm.js network requests,
    as in a debug/interactive scenario. Returns a list of GTM IDs found.
    """
    found_ids = set()
    chrome_options = Options()
    chrome_options.headless = False  # Run with a visible browser
    chrome_options.add_argument("--auto-open-devtools-for-tabs")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.execute_cdp_cmd("Network.enable", {})

    try:
        driver.get(url)
        # Reduced wait time to 5 seconds
        time.sleep(5)

        logs = driver.get_log("performance")
        for entry in logs:
            msg = entry.get("message", "")
            try:
                payload = json.loads(msg)["message"]
                if (payload.get("method") == "Network.requestWillBeSent"
                   and "gtm.js?id=" in payload["params"]["request"]["url"]):
                    m = re.search(r'id=(GTM-[A-Z0-9\\-]{4,})', payload["params"]["request"]["url"])
                    if m:
                        found_ids.add(m.group(1))
            except:
                pass

        # Also check final page_source in case the snippet is inline
        page_source = driver.page_source
        for tag in re.findall(r'gtm\\.js\\?id=(GTM-[A-Z0-9\\-]{4,})', page_source, re.IGNORECASE):
            found_ids.add(tag)
        for tag in re.findall(r'ns\\.html\\?id=(GTM-[A-Z0-9\\-]{4,})', page_source, re.IGNORECASE):
            found_ids.add(tag)

    except Exception as e:
        print(f"[WARN] debug_fallback_live failed for {url}: {e}")
    finally:
        driver.quit()

    return list(found_ids)

def main():
    df = pd.read_csv('GTM.csv')
    df['GTM  ID'] = df['GTM  ID'].fillna('').astype(str)
    df['Subdomain(s)'] = df.get('Subdomain(s)', pd.Series('')).fillna('').astype(str)
    df.fillna({"Website": 'N/A'}, inplace=True)

    # Build domain dictionary, skipping rows with 'N/A' or existing GTM IDs
    domain_dictionary = {}
    for idx, row in df.iterrows():
        website = row['Website'].strip()
        gtm_current = row['GTM  ID'].strip()
        # Skip if website == 'N/A' or if there's already a GTM ID
        if website == 'N/A' or gtm_current:
            continue

        gtm0 = [x.strip() for x in row['GTM  ID'].split(',') if x.strip()]
        subs0 = [x.strip() for x in row['Subdomain(s)'].split(',') if x.strip()]
        base = extract_main_domain(website) if website != 'N/A' else 'N/A'
        domain_dictionary[idx] = {
            'website': website,
            'base_domain': base,
            'found_subdomains': [],
            'discovered_gtm_ids': [],
            'gtm_ids': gtm0,
            'subdomains': subs0
        }

    # Discover subdomains only for rows we didn't skip
    print("[INFO] Discovering subdomains...")
    def proc_sub(idx):
        dom = domain_dictionary[idx]['base_domain']
        return idx, (get_filtered_subdomains(dom) if dom != 'N/A' else [])
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(proc_sub, domain_dictionary))
        for idx, found in results:
            domain_dictionary[idx]['found_subdomains'] = found
    print("[INFO] Subdomain discovery complete!\n")

    # Normalize and combine subdomains
    for idx, entry in domain_dictionary.items():
        combined = set(entry['subdomains']) | set(entry['found_subdomains'])
        entry['found_subdomains'] = [
            s if s.startswith('https://') else f"https://{s}"
            for s in combined
        ]

    # Async GTM extraction
    asyncio.run(main_gtm_processing(domain_dictionary))

    # Merge results back into DataFrame
    for idx, entry in domain_dictionary.items():
        merged = list(dict.fromkeys(entry['gtm_ids'] + entry['discovered_gtm_ids']))
        if "No Tag" in merged and len(merged) > 1:
            merged = [m for m in merged if m != "No Tag"]
        df.at[idx, 'GTM  ID'] = ', '.join(merged)
        df.at[idx, 'Subdomain(s)'] = ', '.join(entry['found_subdomains'])

    # --- Immediate visibility on failures ---
    missing_mask = df['GTM  ID'].str.strip() == ''
    missing_count = missing_mask.sum()
    print(f"[INFO] {missing_count} rows still have no GTM ID")
    if missing_count:
        print(df.loc[missing_mask, ['Organization Name', 'Website']].to_string(index=False))
        # Final debug pass for rows that remain blank, main domain only
        print(f"[INFO] Attempting final debug fallback pass for {missing_count} rows...")
        for idx, row in df[missing_mask].iterrows():
            url = row['Website']
            if not url.lower().startswith('http'):
                url = f"https://{url}"
            found = debug_fallback_live(url)
            if found:
                df.at[idx, 'GTM  ID'] = ', '.join(found)
        still_missing_mask = df['GTM  ID'].str.strip() == ''
        still_missing_count = still_missing_mask.sum()
        print(f"[INFO] After debug fallback, {still_missing_count} rows are still missing GTM IDs")

    # Write out updated CSV
    df.to_csv('GTM_updated.csv', index=False)
    print("[INFO] CSV updated and saved to 'GTM_updated.csv'\n")

if __name__ == "__main__":
    main()
