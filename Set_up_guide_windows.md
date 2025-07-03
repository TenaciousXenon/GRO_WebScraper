# Setup Guide

A step-by-step for getting these tools running on your Windows machine.

## 1. Clone the Repo

```powershell
git clone git@github.com:TenaciousXenon/GRO_WebScraper.git
cd GRO_WebScraper
```

## 2. Create & Activate a Virtual Environment

```powershell
python -m venv venv

# PowerShell
venv\Scripts\Activate.ps1

# or Command Prompt
venv\Scripts\activate.bat
```

## 3. Install Python Dependencies

If you don’t already have Python 3+ and pip:

1. Download and run the installer from https://www.python.org/downloads/windows/  
   - Ensure **“Add Python to PATH”** is checked.

2. (Optional) If you use Chocolatey:
   ```powershell
   choco install python
   ```

Then install all required libraries:

```powershell
pip install pandas aiohttp requests selenium
```

## 4. Install ChromeDriver (for Selenium)

You need ChromeDriver to run the dynamic-site-scraper.

- **Via Chocolatey**:
  ```powershell
  choco install chromedriver
  ```

- **Manual install**:
  1. Download the matching version for your Chrome browser from  
     https://sites.google.com/chromium.org/driver/  
  2. Unzip and place `chromedriver.exe` in a folder on your `PATH` (e.g. `C:\Windows\System32` or add the folder to your PATH).

## 5. Run a Tool

```powershell
# Static HTML scraper
python GroCSVReader.py --input samples.csv --output out.csv

# Dynamic JS scraper
python DynamicReader.py --input urls.csv --output gtm_results.csv

# Subdomain tester
python subdomainValidator.py domains.csv results.csv --column "Subdomain(s)"
```

## 6. Push Changes Back (for contributors)

```powershell
git checkout -b docs/add-readmes
git add .
git commit -m "Add comprehensive documentation"
git push -u origin docs/add-readmes
# Then open a pull request on GitHub.
```
