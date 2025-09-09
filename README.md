# TIKR Financial Statements Scraper

A small utility that downloads historical financial statements from [TIKR](https://www.tikr.com) and exports them to an Excel workbook.

## Features

- Downloads income, cash flow and balance sheet statements.
- Exports each statement to a dedicated worksheet.
- Caches authentication token to speed up repeated queries.
- Simple command line interface.

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

3. Add your TIKR credentials to `config.py`.

## Usage

Run the scraper with a ticker symbol or company name:

```bash
python TIKR.py AAPL
```

If no argument is provided, the script prompts for one interactively. The resulting Excel file is saved as `<TICKER>_<DATE>.xlsx`.

Sample outputs are available in the [`sample-outputs`](sample-outputs) directory.

## Development

The repository uses [flake8](https://flake8.pycqa.org/) for linting. On each push, GitHub Actions runs the linter.

## License

This project is released under the [MIT License](LICENSE).

## Notes

Access to the TIKR API requires a valid TIKR subscription. A free account has limited data availability.

