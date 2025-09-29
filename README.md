# TIKR Financial Statements Scraper

A Python utility for downloading historical financial statements from [TIKR](https://www.tikr.com) and exporting them in multiple formats.

## Features

- **Comprehensive Statement Coverage**: Downloads income statements, cash flow statements, and balance sheets
- **Multiple Export Formats**: Export to Excel (XLSX), CSV, JSON, or Parquet
- **Smart Token Caching**: Stores authentication tokens to speed up repeated queries
- **Automatic Calculations**: Computes year-over-year growth rates, profit margins, and free cash flow metrics
- **Flexible Data Structure**: Transposed format with metrics as rows and periods as columns for easy analysis
- **Command Line Interface**: Simple CLI for quick data retrieval

## Requirements

- Python 3.7+
- Valid TIKR subscription (free accounts have limited data availability)
- Chrome/Chromium browser (for authentication)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/membaby/tikr-statements-scraper
   cd tikr-statements-scraper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your credentials in `config.py`:
   ```python
   TIKR_ACCOUNT_USERNAME = 'your_username'
   TIKR_ACCOUNT_PASSWORD = 'your_password'
   TIKR_EXPORT_FORMAT = 'xlsx'  # Options: 'xlsx', 'csv', 'json', 'parquet'
   ```

## Usage

### Basic Usage

Run the scraper with a ticker symbol or company name:

```bash
python TIKR.py AAPL
```

If no argument is provided, the script will prompt you interactively:

```bash
python TIKR.py
# [...] Please enter ticker symbol or company name: AAPL
```

### Output Files

Files are saved with the format `<TICKER>_<DATE>.<extension>`:

- **XLSX**: Single file with separate worksheets for each statement
- **CSV**: Multiple files (one per statement type)
- **JSON**: Single file with nested structure
- **Parquet**: Multiple files (one per statement type, optimized for analytics)

Example outputs are available in the [`sample-outputs`](sample-outputs) directory.

## Configuration Options

Edit `config.py` to customize:

| Option | Description | Default |
|--------|-------------|---------|
| `TIKR_ACCOUNT_USERNAME` | Your TIKR email | - |
| `TIKR_ACCOUNT_PASSWORD` | Your TIKR password | - |
| `TIKR_EXPORT_FORMAT` | Output format | `'xlsx'` |
| `TIKR_FINANCIAL_STATEMENT_FREQUENCY` | Period type ('Y' or 'Q') | `'Q'` |

## Exported Metrics

The scraper automatically extracts and calculates:

### Income Statement
- Revenue, gross profit, operating income
- Net income (including/excluding extraordinary items)
- Profit margins (gross, operating, net)
- Year-over-year growth rates

### Cash Flow Statement
- Operating cash flow, investing cash flow, financing cash flow
- Capital expenditures
- Free cash flow (calculated)
- Free cash flow margins

### Balance Sheet
- Total assets, total liabilities, stockholders' equity
- Current assets and liabilities
- Long-term debt

## Development

### Code Quality

The project uses [flake8](https://flake8.pycqa.org/) for linting. GitHub Actions automatically runs the linter on each push.

Run linting locally:
```bash
flake8 TIKR.py
```

### Project Structure

```
tikr-statements-scraper/
├── TIKR.py           # Main scraper script
├── config.py         # Configuration file
├── keys.py           # Statement field mappings
├── requirements.txt  # Python dependencies
├── sample-outputs/   # Example output files
└── README.md
```

## Troubleshooting

**Authentication Issues**: If you encounter login problems, delete the `token.tmp` file to force a fresh authentication.

**Missing Data**: Free TIKR accounts have limited historical data. Consider upgrading your subscription for full access.

**Parquet Export**: Requires either `pyarrow` or `fastparquet`. Install with:
```bash
pip install pyarrow
```

## License

This project is released under the [MIT License](LICENSE).

## Disclaimer

This tool is for personal use only. Ensure your usage complies with TIKR's Terms of Service. The authors are not responsible for any misuse or violations of third-party terms.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.