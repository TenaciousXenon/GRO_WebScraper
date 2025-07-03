import pandas as pd
import subprocess
from urllib.parse import urlparse
import asyncio
import aiohttp
from collections import defaultdict
import re
from concurrent.futures import ThreadPoolExecutor

def extract_main_domain(url):
    """Extract the main domain using manual parsing."""
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    parsed = urlparse(url)
    netloc = parsed.netloc

    # Remove port if present
    if ':' in netloc:
        netloc = netloc.split(':')[0]

    # Remove repeated 'www.'
    while netloc.startswith('www.'):
        netloc = netloc[4:]
    
    domain_parts = netloc.split('.')
    if len(domain_parts) >= 2:
        return '.'.join(domain_parts[-2:]).lower()
    return netloc.lower()

def get_filtered_subdomains(domain):
    """
    Run subfinder for a domain, then filter out unwanted subdomains.
    Returns a list of subdomain URLs with `https://` prefix.
    """
    try:
        result = subprocess.run(
            ['subfinder', '-d', domain, '-silent'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            print(f"[WARN] Subfinder error for {domain}: {result.stderr}")
            return []
        
        raw_subdomains = result.stdout.splitlines()
        if not raw_subdomains:
            return []
        
        exclude_prefixes = {
            'www.', 'ns.', 'mail.', 'webdisk.', 'cpanel.',
            'cpcalenders.', 'webmail.', 'cpcontacts.',
            'rent.', 'rentnow.', 'ww2.', 'autodiscover.',
            'email.', 'lp.', 'child.', 'cpcalendars',
            'dev.', 'landing.'
        }
        
        filtered = []
        for sub in raw_subdomains:
            # Remove protocol if present
            if sub.startswith('http'):
                parsed = urlparse(sub)
                hostname = parsed.netloc
            else:
                hostname = sub.split('/')[0]
            
            # Remove port if present
            hostname = hostname.split(':')[0]
            
            # Avoid base domain and typical excluded prefixes
            if hostname == domain or hostname == f"www.{domain}":
                continue
            if any(hostname.startswith(prefix) for prefix in exclude_prefixes):
                continue
            
            # Add https:// prefix
            filtered.append(f"https://{hostname}")
        return filtered
    
    except subprocess.TimeoutExpired:
        print(f"[WARN] Subfinder timed out for {domain}")
        return []
    except Exception as e:
        print(f"[WARN] Error processing subdomains for {domain}: {e}")
        return []

async def fetch_gtm_ids(session, url):
    """
    Fetch GTM IDs from a URL by inspecting gtm.js requests or inline references.
    Returns a list of found GTM IDs.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/91.0.4472.124 Safari/537.36'
        }
        found_ids = set()

        async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as response:
            final_url = str(response.url)

            if 'gtm.js' in final_url and 'id=' in final_url:
                match = re.search(r'id=(GTM-[A-Z0-9]{4,9})', final_url)
                if match:
                    found_ids.add(match.group(1))

            for resp in response.history:
                hist_url = str(resp.url)
                if 'gtm.js' in hist_url and 'id=' in hist_url:
                    match = re.search(r'id=(GTM-[A-Z0-9]{4,9})', hist_url)
                    if match:
                        found_ids.add(match.group(1))

            html_text = await response.text()
            pattern = re.compile(r"GTM-[A-Z0-9\-]{4,}")
            inline_matches = pattern.findall(html_text)
            for match in inline_matches:
                found_ids.add(match)

        return list(found_ids)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        print(f"[WARN] Network/timeout issue for {url}")
        return []
    except Exception as e:
        print(f"[WARN] Unhandled exception for {url}: {e}")
        return []

async def process_url_gtm(session, url, results_dict):
    """
    Process a single URL and store the found GTM IDs in results_dict[url].
    """
    gtm_ids = await fetch_gtm_ids(session, url)
    if gtm_ids:
        results_dict[url].extend(gtm_ids)

async def process_domain_gtm(base_domain, found_subdomains):
    """
    For one domain, gather GTM IDs from the domain plus any subdomains.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                      ' AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    connector = aiohttp.TCPConnector(limit_per_host=5)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        domain_results = defaultdict(list)
        all_urls = [f"https://{base_domain}"] + found_subdomains
        tasks = [process_url_gtm(session, url, domain_results) for url in all_urls]
        await asyncio.gather(*tasks)

        all_found_ids = set()
        for ids_list in domain_results.values():
            all_found_ids.update(ids_list)

        return list(all_found_ids)

async def main_gtm_processing(domain_dictionary):
    """
    Launch concurrent GTM checks for all domains in domain_dictionary.
    """
    print("[INFO] Starting GTM ID discovery...")
    sem = asyncio.Semaphore(10)

    async def process_single_item(idx, entry):
        async with sem:
            if entry['website'] == 'N/A':
                entry['discovered_gtm_ids'] = []
                return
            base_domain = entry.get('base_domain', '')
            found_subdomains = entry.get('found_subdomains', [])
            gtm_ids = await process_domain_gtm(base_domain, found_subdomains)
            entry['discovered_gtm_ids'] = gtm_ids

    tasks = []
    for idx, entry in domain_dictionary.items():
        tasks.append(process_single_item(idx, entry))
    await asyncio.gather(*tasks)
    print("[INFO] GTM ID discovery complete!\n")

def main():
    # Read CSV
    df = pd.read_csv('DO.csv')  # For demonstration, you can rename or override as needed

    # Replace missing Website cells with 'N/A'
    df.fillna({"Website": 'N/A'}, inplace=True)

    # Build a dictionary keyed by row index
    domain_dictionary = {}
    for idx, row in df.iterrows():
        if pd.isna(row.get('GTM  ID', '')):
            initial_gtm_ids = ()
        else:
            initial_gtm_ids = tuple(gtm.strip() for gtm in str(row['GTM  ID']).split(',') if gtm.strip())
        
        if pd.isna(row.get('Subdomain(s)', '')):
            initial_subdomains = ()
        else:
            initial_subdomains = tuple(sub.strip() for sub in str(row['Subdomain(s)']).split(',') if sub.strip())
        
        website = row.get('Website', 'N/A').strip()

        base_domain = 'N/A'
        if website != 'N/A':
            base_domain = extract_main_domain(website)

        domain_dictionary[idx] = {
            'organization': row.get('Organization Name', ''),
            'website': website,
            'subdomains': initial_subdomains,
            'gtm_ids': initial_gtm_ids,
            'base_domain': base_domain,
            'found_subdomains': [],
            'discovered_gtm_ids': []
        }

    # Subdomain discovery
    print("[INFO] Discovering subdomains...")
    def process_subdomains(idx):
        entry = domain_dictionary[idx]
        if entry['website'] == 'N/A':
            return idx, []
        domain = entry['base_domain']
        found = get_filtered_subdomains(domain)
        return idx, found

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(process_subdomains, domain_dictionary.keys())

    for idx, found_subs in results:
        domain_dictionary[idx]['found_subdomains'] = found_subs

    print("[INFO] Subdomain discovery complete!\n")

    # Combine existing subdomains with discovered subdomains
    for idx, entry in domain_dictionary.items():
        existing = set(entry['subdomains'])
        discovered = set(entry['found_subdomains'])

        def standardize_subdomain(sub):
            sub = sub.strip()
            if not sub.startswith('https://'):
                return f"https://{sub}"
            return sub

        standard_existing = {standardize_subdomain(s) for s in existing}
        standard_discovered = {standardize_subdomain(s) for s in discovered}
        combined = list(standard_existing.union(standard_discovered))
        domain_dictionary[idx]['subdomains'] = combined

    # Asynchronously discover GTM IDs
    asyncio.run(main_gtm_processing(domain_dictionary))

    # Merge newly discovered GTM IDs into the original GTM field
    for idx, entry in domain_dictionary.items():
        original_ids = list(entry['gtm_ids'])
        newly_found = entry['discovered_gtm_ids']
        combined_ids = list(dict.fromkeys(original_ids + newly_found))  # preserve order, remove duplicates
        
        # If "No Tag" was present, handle carefully
        if "No Tag" in combined_ids:
            combined_ids = [i for i in combined_ids if i != "No Tag"]
            if not combined_ids:
                combined_ids = ["No Tag"]

        entry['gtm_ids'] = combined_ids

        df.at[idx, 'Subdomain(s)'] = ', '.join(entry['subdomains'])
        df.at[idx, 'GTM  ID'] = ', '.join(entry['gtm_ids'])

    df.to_csv('DO_updated.csv', index=False)
    print("[INFO] CSV updated and saved to 'DO_updated.csv'\n")

if __name__ == "__main__":
    main()