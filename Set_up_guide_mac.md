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
```

## 3. Install All Requirements

```bash
# 1. (If you don’t have Homebrew) install Homebrew:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Update Homebrew and install Python 3 (incl. pip3)
brew update
brew install python3

# 3. Verify Python 3 and pip3 are on your PATH
python3 --version
pip3 --version

# 4. Install the common Python libraries
pip3 install pandas aiohttp requests selenium

# 5. (Optional, for Selenium) install ChromeDriver
brew install --cask chromedriver
```

## 4. Ensure ChromeDriver (for dynamic-site-scraper)

- Download matching ChromeDriver for your Chrome version.
- Place it on your `PATH`.
- Also, everything needs to be in the same directory with virtual environment activated
- directory needs to be cd

## 5. Run a Tool

```bash
# Static HTML
python GroCSVReader.py --input samples.csv --output out.csv

# Dynamic JS
python DynamicReader.py

# Subdomain Test
python subdomainValidator.py domains.csv results.csv --column='example subdomain'
```

## 6. Push Changes Back (for contributors)

```bash
git checkout -b docs/add-readmes
git add .
git commit -m "Add comprehensive documentation"
git push --set-upstream origin docs/add-readmes
# Open a pull request on GitHub
```
