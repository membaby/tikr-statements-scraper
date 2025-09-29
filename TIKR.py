from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
import argparse
import datetime
import json
import os
import time
import pandas as pd

import keys
from config import TIKR_ACCOUNT_USERNAME, TIKR_ACCOUNT_PASSWORD, TIKR_EXPORT_FORMAT


class TIKR:
    def __init__(self):
        self.username = TIKR_ACCOUNT_USERNAME
        self.password = TIKR_ACCOUNT_PASSWORD
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': 'https://app.tikr.com',
            'Connection': 'keep-alive',
            'Referer': 'https://app.tikr.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'TE': 'trailers'
        }
        self.statements = keys.statements
        self.content = {
            'income_statement': [],
            'cashflow_statement': [],
            'balancesheet_statement': [],
        }
        if os.path.isfile('token.tmp'):
            with open('token.tmp', 'r') as f:
                self.access_token = f.read()
        else:
            self.access_token = ''

    def get_access_token(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        user_agent = ('Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) '
                      'Chrome/22.0.1216.0 Safari/537.2')
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument('window-size=1920x1080')
        s = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=s, options=chrome_options)
        browser.get('https://app.tikr.com/login')
        browser.find_element(By.XPATH, '//input[@type="email"]').send_keys(self.username)
        browser.find_element(By.XPATH, '//input[@type="password"]').send_keys(self.password)
        browser.find_element(By.XPATH, '//button/span').click()
        while 'Welcome to TIKR' not in browser.page_source:
            time.sleep(5)
        browser.get('https://app.tikr.com/screener?sid=1')

        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button/span[contains(text(), "Fetch Screen")]/..'))
        )
        browser.find_element(By.XPATH, '//button/span[contains(text(), "Fetch Screen")]/..').click()
        time.sleep(5)
        try:
            for request in browser.requests:
                if '/fs' in request.url and request.method == 'POST':
                    response = json.loads(request.body)
                    print('[ * ] Successfully fetched access token')
                    self.access_token = response['auth']
                    with open('token.tmp', 'w') as f:
                        f.write(self.access_token)
        except Exception as err:
            print(err)
        browser.close()

    def get_financials(self, tid, cid):
        url = 'https://api.tikr.com/tf'
        while True:
            payload = json.dumps({
                "auth": self.access_token,
                "tid": tid,
                "cid": cid,
                "p": "1",
                "repid": 1,
                "v": "v1"
            })
            response = requests.post(url, headers=self.headers, data=payload).json()
            if 'dates' not in response or 'financials' not in response:
                print('[ + ] Generating Access Token...')
                self.get_access_token()
            else:
                break

        # Reset previously cached content before loading new data
        self.content = {
            'income_statement': [],
            'cashflow_statement': [],
            'balancesheet_statement': [],
        }

        periods = response.get('dates', [])
        period_lookup = {period['value']: period for period in periods}
        period_keys = [period['value'] for period in periods]

        # Map the API response blocks to the statements we care about
        statement_indices = {
            'income_statement': 0,
            'balancesheet_statement': 1,
            'cashflow_statement': 2,
        }

        financials = response.get('financials', [])

        def normalize_label(label):
            if not isinstance(label, str):
                return ''
            return ''.join(ch for ch in label.lower() if ch.isalnum())

        statement_data = {}
        statement_name_index = {}
        statement_name_list = {}
        for statement_name, index in statement_indices.items():
            lines = financials[index] if index < len(financials) else []
            line_map = {}
            name_index = {}
            names_list = []
            for line in lines:
                dataitemid = line.get('dataitemid')
                if not isinstance(dataitemid, int):
                    continue
                line_map[dataitemid] = line
                name = line.get('name', '')
                normalized = normalize_label(name)
                if normalized and normalized not in name_index:
                    name_index[normalized] = dataitemid
                names_list.append((normalized, dataitemid, name))
            statement_data[statement_name] = line_map
            statement_name_index[statement_name] = name_index
            statement_name_list[statement_name] = names_list

        resdata_map = {}
        resdata_name_index = {}
        resdata_name_list = []
        for line in response.get('resData', {}).values():
            if not isinstance(line, dict):
                continue
            dataitemid = line.get('dataitemid')
            if not isinstance(dataitemid, int):
                continue
            resdata_map[dataitemid] = line
            name = line.get('name', '')
            normalized = normalize_label(name)
            if normalized and normalized not in resdata_name_index:
                resdata_name_index[normalized] = dataitemid
            resdata_name_list.append((normalized, dataitemid, name))

        def resolve_dataitem_id(statement_name, column_name, alias_name):
            search_terms = []
            if isinstance(alias_name, str) and alias_name:
                search_terms.append(alias_name)
            if column_name not in search_terms:
                search_terms.append(column_name)

            for term in search_terms:
                normalized = normalize_label(term)
                if not normalized:
                    continue
                item_id = statement_name_index.get(statement_name, {}).get(normalized)
                if item_id:
                    return item_id
                item_id = resdata_name_index.get(normalized)
                if item_id:
                    return item_id

            for term in search_terms:
                normalized = normalize_label(term)
                if not normalized:
                    continue
                for cand_norm, item_id, _ in statement_name_list.get(statement_name, []):
                    if not cand_norm:
                        continue
                    if normalized == cand_norm or normalized in cand_norm or cand_norm in normalized:
                        return item_id
                for cand_norm, item_id, _ in resdata_name_list:
                    if not cand_norm:
                        continue
                    if normalized == cand_norm or normalized in cand_norm or cand_norm in normalized:
                        return item_id
            return None

        statements_config = []
        for statement in self.statements:
            statement_name = statement['statement']
            resolved_keys = {}
            for column, alias in statement['keys'].items():
                if not alias:
                    resolved_keys[column] = ''
                    continue
                item_id = resolve_dataitem_id(statement_name, column, alias)
                if item_id is None:
                    resolved_keys[column] = ''
                else:
                    resolved_keys[column] = item_id
            statements_config.append({
                'statement': statement_name,
                'keys': statement['keys'],
                'resolved_keys': resolved_keys,
            })

        resolved_key_lookup = {
            cfg['statement']: cfg['resolved_keys'] for cfg in statements_config
        }

        def extract_value(line_map, item_id, period_key):
            if not item_id:
                return '', False
            line = line_map.get(item_id) or resdata_map.get(item_id)
            if not line:
                return '', False
            period_entry = line.get(period_key)
            if not isinstance(period_entry, dict):
                return '', False
            value = period_entry.get('v')
            if value == '1.11':
                return '', True
            if value in (None, '', 'NA'):
                return '', False
            try:
                return float(value), False
            except (TypeError, ValueError):
                return '', False

        income_statement_map = statement_data.get('income_statement', {})

        for period_key in period_keys:
            period_info = period_lookup.get(period_key, {})
            year = period_info.get('calendaryear')
            for statement_cfg in statements_config:
                statement_name = statement_cfg['statement']
                line_map = statement_data.get(statement_name, {})
                resolved_keys = statement_cfg['resolved_keys']
                config_keys = statement_cfg['keys']
                ACCESS_DENIED = 0
                data = {'year': year}
                for column, alias in config_keys.items():
                    if column == 'Free Cash Flow':
                        ops_id = resolved_keys.get('Cash from Operations')
                        capex_id = resolved_keys.get('Capital Expenditure')
                        ops_value, ops_denied = extract_value(line_map, ops_id, period_key)
                        capex_value, capex_denied = extract_value(line_map, capex_id, period_key)
                        if ops_denied or capex_denied:
                            ACCESS_DENIED += 1
                            data[column] = ''
                        elif ops_value != '' and capex_value != '':
                            data[column] = ops_value + capex_value
                        else:
                            data[column] = ''
                        continue

                    if column == '% Free Cash Flow Margins':
                        fcf = data.get('Free Cash Flow')
                        revenue_id = resolved_key_lookup.get('income_statement', {}).get('Revenues')
                        revenue_value, revenue_denied = extract_value(income_statement_map, revenue_id, period_key)
                        if revenue_denied:
                            ACCESS_DENIED += 1
                            data[column] = ''
                        elif (
                            fcf not in (None, '')
                            and revenue_value not in ('', None)
                            and revenue_value != 0
                        ):
                            data[column] = (float(fcf) / float(revenue_value)) * 100
                        else:
                            data[column] = ''
                        continue

                    resolved_item_id = resolved_keys.get(column)
                    if not resolved_item_id:
                        data[column] = ''
                        continue

                    value, denied = extract_value(line_map, resolved_item_id, period_key)
                    if denied:
                        ACCESS_DENIED += 1
                        data[column] = ''
                        continue

                    if value == '':
                        data[column] = ''
                        continue

                    if column == 'Income Tax Expense':
                        data[column] = value * -1
                    else:
                        data[column] = value

                if ACCESS_DENIED > 10:
                    continue
                self.content[statement_name].append(data)

        for statement in self.statements:
            statement_name = statement['statement']
            rows = self.content.get(statement_name, [])
            if not rows:
                continue

            yoy_columns = [column for column in statement['keys'] if 'YoY' in column]
            for idx, fiscalyear in enumerate(rows):
                for column in yoy_columns:
                    base_column = column.replace(' YoY', '')
                    if idx == 0:
                        fiscalyear[column] = ''
                        continue
                    current_value = rows[idx].get(base_column)
                    previous_value = rows[idx - 1].get(base_column)
                    if (
                        current_value not in ('', None)
                        and previous_value not in ('', None)
                        and previous_value != 0
                    ):
                        try:
                            fiscalyear[column] = round(
                                ((float(current_value) / float(previous_value)) - 1) * 100,
                                2,
                            )
                        except (TypeError, ValueError, ZeroDivisionError):
                            fiscalyear[column] = ''
                    else:
                        fiscalyear[column] = ''

            if statement_name == 'income_statement':
                margin_columns = {
                    '% Gross Margins': ('Gross Profit', 'Revenues'),
                    '% Operating Margins': ('Operating Income', 'Revenues'),
                    '% Net Income to Common Incl Extra Items Margins': (
                        'Net Income to Common Incl Extra Items',
                        'Revenues',
                    ),
                    '% Net Income to Common Excl. Extra Items Margins': (
                        'Net Income to Common Excl. Extra Items',
                        'Revenues',
                    ),
                }
                for fiscalyear in rows:
                    for column, (numerator, denominator) in margin_columns.items():
                        num_val = fiscalyear.get(numerator)
                        denom_val = fiscalyear.get(denominator)
                        if (
                            num_val not in ('', None)
                            and denom_val not in ('', None)
                            and denom_val != 0
                        ):
                            try:
                                fiscalyear[column] = (float(num_val) / float(denom_val)) * 100
                            except (TypeError, ValueError, ZeroDivisionError):
                                fiscalyear[column] = ''
                        else:
                            fiscalyear[column] = ''

    def find_company_info(self, ticker):
        headers = self.headers.copy()
        headers['content-type'] = 'application/x-www-form-urlencoded'
        data = '{"params":"query=' + ticker + '&distinct=2"}'
        url = ('https://tjpay1dyt8-3.algolianet.com/1/indexes/tikr-feb/query?'
               'x-algolia-agent=Algolia%20for%20JavaScript%20(3.35.1)%3B%20Browser%20'
               '(lite)&x-algolia-application-id=TJPAY1DYT8&'
               'x-algolia-api-key=d88ea2aa3c22293c96736f5ceb5bab4e')
        response = requests.post(url, headers=headers, data=data)

        if response.json()['hits']:
            tid = response.json()['hits'][0]['tradingitemid']
            cid = response.json()['hits'][0]['companyid']
            return tid, cid
        else:
            return None, None

    def export(self, filename_base):
        export_format = (TIKR_EXPORT_FORMAT or 'xlsx').lower()
        valid_formats = {'xlsx', 'csv', 'json', 'parquet'}
        if export_format not in valid_formats:
            print(f"[ - ] Unknown export format '{export_format}', defaulting to XLSX")
            export_format = 'xlsx'
        base_name = os.path.splitext(filename_base)[0]

        frames = {}
        for statement in self.statements:
            statement_name = statement['statement']
            rows = self.content.get(statement_name, [])
            if not rows:
                continue
            columns = list(rows[0].keys())
            years = [row['year'] for row in rows]
            if years:
                years[-1] = 'LTM'
            df = pd.DataFrame(rows, columns=columns, index=years)
            if 'year' in df.columns:
                df = df.drop(columns='year')
            frames[statement_name] = df

        if not frames:
            print('[ - ] No data available to export')
            return []

        exported_files = []
        report_label = os.path.basename(base_name).split('_')[0]

        if export_format == 'xlsx':
            output_path = f"{base_name}.xlsx"
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                for statement_name, df in frames.items():
                    df_transposed = df.T
                    df_transposed.to_excel(writer, sheet_name=statement_name)

                    worksheet = writer.sheets[statement_name]
                    worksheet.write('A1', report_label)
                    for idx, _ in enumerate(df.columns):
                        width = 45 if idx == 0 else 15
                        worksheet.set_column(idx, idx, width)
            exported_files.append(output_path)
        elif export_format == 'csv':
            for statement_name, df in frames.items():
                df_out = df.T.reset_index().rename(columns={'index': 'Metric'})
                output_path = f"{base_name}_{statement_name}.csv"
                df_out.to_csv(output_path, index=False)
                exported_files.append(output_path)
        elif export_format == 'json':
            output_path = f"{base_name}.json"
            payload = {
                statement_name: df.T.to_dict(orient='index')
                for statement_name, df in frames.items()
            }
            with open(output_path, 'w', encoding='utf-8') as handle:
                json.dump(payload, handle, indent=2)
            exported_files.append(output_path)
        elif export_format == 'parquet':
            for statement_name, df in frames.items():
                df_out = df.T.reset_index().rename(columns={'index': 'Metric'})

                # Clean up empty strings & enforce numeric where possible
                df_out = df_out.replace('', pd.NA)
                df_out = df_out.convert_dtypes()
                for col in df_out.columns[1:]:
                    df_out[col] = pd.to_numeric(df_out[col], errors='coerce')

                output_path = f"{base_name}_{statement_name}.parquet"
                try:
                    df_out.to_parquet(output_path, index=False)
                except ImportError as err:
                    raise RuntimeError(
                        'Parquet export requires either pyarrow or fastparquet to be installed.'
                    ) from err
                exported_files.append(output_path)

        return exported_files


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def main():
    """Command line entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description="Scrape TIKR financial statements to a data file",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Company name or ticker symbol",
    )
    args = parser.parse_args()

    query = args.query or input(
        f'{bcolors.WARNING}[...]{bcolors.ENDC} Please enter ticker symbol or company name: '
    )

    scraper = TIKR()
    print(f'[ . ] TIKR Statements Scraper: {bcolors.OKGREEN}Ready{bcolors.ENDC}')
    tid, cid = scraper.find_company_info(query)
    if not (tid and cid):
        print(f'[ - ] {bcolors.FAIL}[Error]{bcolors.ENDC}: Could not find company')
        return
    print(
        f'[ . ] {bcolors.OKGREEN}Found company{bcolors.ENDC}: {query} '
        f'[Trading ID: {tid}] [Company ID: {cid}]'
    )

    print('[ . ] Starting scraping...')
    scraper.get_financials(tid, cid)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d')
    base_filename = f"{query}_{timestamp}"
    exported_files = scraper.export(base_filename)
    if exported_files:
        for path in exported_files:
            print(f'[ + ] {bcolors.OKGREEN}Exported{bcolors.ENDC}: {path}')
    else:
        print(f'[ - ] {bcolors.FAIL}No files exported{bcolors.ENDC}')
        print('[ . ] Done')


if __name__ == '__main__':
    main()
