# Credit Management PST Email Analysis Tool

This repository provides an automated, local pipeline to parse Outlook `.pst` files, extract email threads from the last 2 years, compute thread length and duration metrics, classify credit management root causes, and generate interactive Sankey diagrams.

## Features

- **PST Stream Extraction**: Reads `.pst` or `.msg` files and slices data dynamically to the specified timeframe (default: last 2 years).
- **Thread Reconstruction**: Reconstructs email conversation chains using `Message-ID`, `In-Reply-To`, `References`, and normalized subject matching via DuckDB.
- **Thread Metrics**: Computes email counts per thread, total thread duration (days/hours), and response lag between participants.
- **Taxonomy Classification**: Categorizes credit management threads into operational categories (Invoice Dispute, Dunning, Payment Allocation, Credit Limit, PO Process) and maps root causes.
- **Interactive Sankey Visualization**: Outputs standalone HTML dashboards showing `Category ➔ Root Cause ➔ Outcome`.

## Installation

```bash
git clone <your-repo-url>
cd credit-management-pst-analysis
pip install -r requirements.txt
```

## Usage

Run the analysis CLI by providing the path to your `.pst` file:

```bash
python analyze_pst.py --pst-path "/path/to/your/credit_export.pst" --years 2 --output-dir "./output"
```

### Options

- `--pst-path`: Path to the local 3 GB `.pst` file (required).
- `--years`: Rolling timeframe window in years to include (default: `2`).
- `--output-dir`: Target directory for Parquet data, CSV metrics, and Sankey HTML (default: `./output`).
- `--fallback-sample`: Run with synthetic sample data for verification if no PST file is present.

## Outputs Generated

1. `output/raw_emails_2yr.parquet`: Extracted filtered email metadata.
2. `output/credit_thread_metrics.csv`: Detailed metrics per thread (count, duration, category, root cause).
3. `output/sankey_root_cause.html`: Interactive Plotly Sankey diagram.
