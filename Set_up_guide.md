# Setup Guide

A step-by-step for getting these tools running on your machine.

## 1. Clone the Repo

```bash
git clone git@github.com:YourOrg/company-web-tools.git
cd company-web-tools
```

## 2. Create & Activate Virtualenv

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

## 3. Install All Requirements

```bash
pip install -r static-site-scraper/requirements.txt
pip install -r dynamic-site-scraper/requirements.txt
pip install -r subdomain-tester/requirements.txt
```

## 4. Ensure ChromeDriver (for dynamic-site-scraper)

- Download matching ChromeDriver for your Chrome version.
- Place it on your `PATH`.

## 5. Run a Tool

```bash
# Static HTML
python static-site-scraper/scraper.py --input samples/urls.txt --output out.csv

# Dynamic JS
python dynamic-site-scraper/scraper.py

# Subdomain Test
python subdomain-tester/tester.py domains.csv results.csv
```

## 6. Push Changes Back (for contributors)

```bash
git checkout -b docs/add-readmes
git add .
git commit -m "Add comprehensive documentation"
git push --set-upstream origin docs/add-readmes
# Open a pull request on GitHub
```
