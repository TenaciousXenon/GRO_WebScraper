# Dynamic Site Scraper

Extracts GTM IDs (or other dynamic snippets) from JS-driven pages using:

1. Async HTTP fetch + regex  
2. Selenium fallback  
3. HTML regex fallback

## Requirements

```bash
python3.8+
pip install -r requirements.txt
# You must have ChromeDriver on your PATH
```

## Usage

```bash
python scraper.py --input urls.csv --output gtm_results.csv
```

Where `urls.csv` has columns:

- `Website`  
- `Subdomain(s)` (optional comma list)  
- `GTM  ID` (existing IDs; new ones will be appended)

## Example

```bash
python scraper.py
# reads `GTM.csv` and writes `GTM_updated.csv`
```
