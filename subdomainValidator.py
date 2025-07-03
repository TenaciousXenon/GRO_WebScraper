import csv
import socket
import argparse
from urllib.parse import urlparse

NOTE: No special libraries are needed to use this program!

def is_domain_reachable(domain, timeout=5):
    """Check if a domain is reachable via HTTP/HTTPS ports."""
    try:
        socket.create_connection((domain, 80), timeout=timeout)
        return True
    except (socket.gaierror, socket.timeout, ConnectionRefusedError, OSError):
        try:
            socket.create_connection((domain, 443), timeout=timeout)
            return True
        except (socket.gaierror, socket.timeout, ConnectionRefusedError, OSError):
            return False

def extract_domain(url):
    """Extract domain from URL with various formats."""
    # Handle wildcard domains
    if url.startswith(('*.', '.')):
        url = url.lstrip('*.')
    
    parsed = urlparse(url)
    if parsed.scheme:
        return parsed.netloc.split(':')[0]
    return url.split('://')[-1].split('/')[0].split(':')[0]

def find_header_and_index(rows, col_name):
    """
    Find the header row index and the column index that matches col_name.
    Returns (header_row_index, col_index).
    Raises ValueError if the column is not found.
    """
    header_row = None
    col_index = None
    lower_col_name = col_name.lower()
    for i, row in enumerate(rows):
        if any(lower_col_name in cell.lower() for cell in row):
            header_row = i
            # Now find exact match for the column in that row
            for j, cell in enumerate(row):
                if cell.strip().lower() == lower_col_name:
                    col_index = j
                    break
            break
    if header_row is None or col_index is None:
        raise ValueError(f"Column '{col_name}' not found in CSV.")
    return header_row, col_index

def process_csv(input_file, output_file, column_name='Subdomain(s)'):
    """
    Process a CSV file to check subdomains, keep all rows (including ones without
    subdomain data or having 'N/A'), and preserve original spacing/order.
    """
    with open(input_file, 'r', encoding='utf-8', newline='') as f:
        lines = f.readlines()
        if not lines:
            print("CSV file is empty.")
            return

    # Detect dialect based on the first non-empty line
    first_non_empty_line = next((l for l in lines if l.strip()), None)
    if not first_non_empty_line:
        print("CSV file has no valid content.")
        return
    dialect = csv.Sniffer().sniff(first_non_empty_line)

    # Parse rows with the CSV reader
    reader = csv.reader(lines, dialect=dialect)
    parsed_rows = list(reader)

    # Find header row and column index
    header_row_idx, subdomain_col_idx = find_header_and_index(parsed_rows, column_name)

    # We'll preserve every line's spacing, so mark all lines to keep
    keep_line_indices = set(range(len(lines)))

    total = 0
    working = 0

    # Check subdomains for subsequent rows but do not remove them
    for i, row in enumerate(parsed_rows):
        if i <= header_row_idx:
            continue
        if len(row) <= subdomain_col_idx:
            continue

        raw_domain = row[subdomain_col_idx].strip()

        # If there's no subdomain or it's "N/A", we still keep the row, just skip counting
        if not raw_domain or raw_domain.lower() == 'n/a':
            continue

        total += 1
        try:
            domain = extract_domain(raw_domain)
            if domain and is_domain_reachable(domain):
                working += 1
        except Exception as e:
            print(f"Error processing '{raw_domain}': {e}")

    # Write out every line, since we keep them all
    with open(output_file, 'w', encoding='utf-8', newline='') as out:
        for idx, line in enumerate(lines):
            if idx in keep_line_indices:
                out.write(line)

    print(f"Found {working} working subdomains out of {total}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Filter working subdomains from a CSV file without removing any rows.')
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('output', help='Output CSV file path')
    parser.add_argument('--column', default='Subdomain(s)',
                        help='Column name containing subdomains (default: "Subdomain(s)")')
    args = parser.parse_args()
    try:
        process_csv(args.input, args.output, args.column)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
