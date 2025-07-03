# Subdomain Tester

Checks reachability of subdomains listed in a CSV without dropping rows.

## Requirements

```bash
python3.8+
pip install -r requirements.txt
```

## Usage

```bash
python tester.py input.csv output.csv
```

- `input.csv`: any CSV with a `Subdomain(s)` column  
- `output.csv`: copy of the CSV (all rows kept)  
- Reports “Found X working subdomains out of Y”

## Example

```bash
python tester.py domains.csv results.csv
```
