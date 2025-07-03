# User Guide for GRO_WebScraper

- A friendly, step-by-step guide for anyone to use our scrapers and subdomain tester

---

## What’s in this folder?

- **GroCSVReader.py**  
  Reads a list of websites and finds any Google Tag Manager (GTM) IDs.  
  Input: a CSV of organizations/websites  
  Output: the same CSV, but with “GTM ID” and “Subdomain(s)” columns filled in.

- **DynamicReader.py**  
  Similar to GroCSVReader but with smarter fallbacks (Selenium/ChromeDriver).  
  Great if some sites load GTM only via JavaScript.

- **subdomainValidator.py**  
  Checks which subdomains in your CSV actually respond on port 80 or 443.  
  Doesn’t remove any rows—just reports “X out of Y subdomains are live.”

---

## Before You Start

1. You’ll need **Python 3.8+** installed.  
2. You’ll need **pip** (Python’s package installer).  
3. (For DynamicReader) you’ll also need **ChromeDriver**.

> Tip: If you don’t know what Python or pip are, just follow the installer links below—there’s nothing to code.

---

## 1. Download & Open

1. Go to https://github.com/TenaciousXenon/GRO_WebScraper  
2. Click the green **Code** button, then “Download ZIP.”  
3. Unzip to a folder, e.g. `C:\GRO_WebScraper`.

---

## 2. Install Python & Libraries

### A) Install Python  
– Visit https://python.org/downloads/windows  
– Download and run the installer  
– Make sure **“Add Python to PATH”** is checked on the installer screen.

### B) Open Windows PowerShell or Command Prompt  
1. Press **Windows Key + R**, type `powershell`, press Enter.  
2. In the new window, type:

   ```powershell
   python --version
   ```

   If you see `Python 3.x.x`, you’re good. Otherwise, repeat step A.

### C) Install the helper libraries

Paste this command into PowerShell and press Enter:

```powershell
pip install pandas aiohttp requests selenium
```

- **pandas** lets the scripts read & write CSV files  
- **aiohttp** & **requests** handle web downloads  
- **selenium** powers the “browser” fallback

---

## 3. (Optional) ChromeDriver for DynamicReader

If you plan to use **DynamicReader.py**, you need ChromeDriver:

1. In PowerShell run:

   ```powershell
   pip install chromedriver-binary
   ```

   OR

2. Download it from  
   https://sites.google.com/chromium.org/driver/  
   and unzip `chromedriver.exe` into the same folder as your `.py` files.

---

## 4. How to Run Each Tool

1. In your PowerShell, navigate to the folder:

   ```powershell
   cd C:\GRO_WebScraper
   ```

2. Run the tool you need:

   • **Static CSV & GTM scanner**  
     ```powershell
     python GroCSVReader.py --input your_list.csv --output results.csv
     ```  
     - *your_list.csv* must have columns: `Organization Name`, `Website`  
     - Produces *results.csv* with added `GTM ID` and updated `Subdomain(s)`.

   • **Dynamic JS scraper**  
     ```powershell
     python DynamicReader.py
     ```  
     - Reads `GTM.csv` in the folder and writes `GTM_updated.csv`.

   • **Subdomain reachability tester**  
     ```powershell
     python subdomainValidator.py all_domains.csv live_report.csv --column "Subdomain(s)"
     ```  
     - *all_domains.csv* needs a “Subdomain(s)” column.  
     - *live_report.csv* will be your full list, unchanged, but you’ll see in your terminal how many are live.

---

## 5. Where to Ask for Help

- **Slack #web-team**: drop your CSV and the exact command you ran  
- **Email**: jburke@gromarketing.com  
- **In-person**: ping @Joseph Burke on Teams

That’s it. No coding required. Just install, double-click or paste one of the commands above, and you’ll have your updated CSV in minutes  
