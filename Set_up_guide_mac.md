# Setup Guide

A step-by-step for getting these tools running on your machine.

## 1. Clone the Repo

```bash
git clone git@github.com:TenaciousXenon/GRO_WebScraper.git
cd GRO_WebScraper
```

## 2. Create & Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows
```

## 3. Install Python Dependencies

If you don't already have Python 3+ and pip3:

```bash
# Optional: install via Homebrew on macOS
brew update
brew install python3
```

Then install all required libraries in one go:

```bash
pip3 install pandas aiohttp requests selenium
```

## 4. Install ChromeDriver (for Selenium)

You need ChromeDriver to run dynamic-site-scraper:

```bash
brew install --cask chromedriver   # macOS
```

Or download the matching version from  
https://sites.google.com/chromium.org/driver/  
and add it to your `PATH`.

## 5. Run a Tool

```bash
# Static HTML scraper
python GroCSVReader.py --input samples.csv --output out.csv

# Dynamic JS scraper
python DynamicReader.py --input urls.csv --output gtm_results.csv

# Subdomain tester
python subdomainValidator.py domains.csv results.csv \
    --column "Subdomain(s)"
```

## 6. Push Changes Back (for contributors)

```bash
git checkout -b docs/add-readmes
git add .
git commit -m "Add comprehensive documentation"
git push -u origin docs/add-readmes
# Then open a pull request on GitHub.
```
