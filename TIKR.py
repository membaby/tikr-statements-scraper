import requests
import json
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import keys
import pandas as pd
import datetime
import os

class TIKR:
    def __init__(self):
        self.username = 'notify.e1@outlook.com'
        self.password = '123456789'
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
        self.column_names = keys.keys
        self.statements = keys.statements
        self.content = {'income_statement': [], 'cashflow_statement': [], 'balancesheet_statement': []}
        if os.path.isfile('token.tmp'):
            with open('token.tmp', 'r') as f:
                self.ACCESS_TOKEN = f.read()
        else:
            self.ACCESS_TOKEN = ''

    def getAccessToken(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        user_agent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2'
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument('window-size=1920x1080')
        browser = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        browser.get('https://app.tikr.com/login')
        browser.find_element(By.XPATH, '//input[@type="email"]').send_keys(self.username)
        browser.find_element(By.XPATH, '//input[@type="password"]').send_keys(self.password)
        browser.find_element(By.XPATH, '//button/span').click()
        while 'Welcome to TIKR' not in browser.page_source:
            time.sleep(5)
        browser.get('https://app.tikr.com/screener?sid=1')
        time.sleep(2)
        browser.find_element(By.XPATH, '//button/span[contains(text(), "Fetch Screen")]/..').click()
        time.sleep(5)
        try:
            for request in browser.requests:
                if 'amazonaws.com/prod/fs' in request.url and request.method == 'POST':
                    response = json.loads(request.body)
                    print('[ * ] Successfully fetched access token')
                    self.ACCESS_TOKEN = response['auth']
                    with open('token.tmp', 'w') as f:
                        f.write(self.ACCESS_TOKEN)
        except Exception as err:
            print(err)
        browser.close()

    def getFinancials(self, tid, cid):
        url = "https://oljizlzlsa.execute-api.us-east-1.amazonaws.com/prod/fin"
        while True:
            payload = json.dumps({
                "auth": self.ACCESS_TOKEN,
                "tid": tid,
                "cid": cid,
                "p": "1",
                "repid": 1,
                "v": "v1"
            })
            response = requests.request("POST", url, headers=self.headers, data=payload).json()
            if 'dates' not in response:
                print('[ + ] Generating Access Token')
                scraper.getAccessToken()
            else:
                break
        print('[ + ] Fetching Statements')
        for fiscalyear in response['dates']:
            fiscal_year_data = list(filter(lambda x: x['financialperiodid'] == fiscalyear['financialperiodid'], response['data']))
            year_data = {'income_statement': {}, 'cashflow_statement': {}, 'balancesheet_statement': {}}
            for statement in self.statements:
                ACCESS_DENIED = 0
                data = year_data[statement['statement']]
                data['year'] = fiscalyear['calendaryear']
                for column in statement['keys']:
                    # SPECIAL CASES
                    if column == 'Free Cash Flow':
                        cash_from_ops = list(filter(lambda x: x['dataitemid'] == 2006, fiscal_year_data))
                        capital_expen = list(filter(lambda x: x['dataitemid'] == 2021, fiscal_year_data))
                        if cash_from_ops and capital_expen:
                            data[column] = float(cash_from_ops[0]['dataitemvalue']) + float(capital_expen[0]['dataitemvalue'])
                        continue
                    elif column == '% Free Cash Flow Margins':
                        FCF = data['Free Cash Flow']
                        revenue = list(filter(lambda x: x['dataitemid'] == self.statements[0]['keys']['Revenues'], fiscal_year_data))
                        if revenue:
                            data[column] = (float(FCF) / float(revenue[0]['dataitemvalue'])) * 100
                        continue
                    # GENERAL CASE
                    value = list(filter(lambda x: x['dataitemid'] == statement['keys'][column], fiscal_year_data))
                    if value:
                        if value[0]['dataitemvalue'] == '1.11':
                            ACCESS_DENIED += 1
                            data[column] = ''
                        else:
                            data[column] = float(value[0]['dataitemvalue'])
                    else:
                        data[column] = ''
                if ACCESS_DENIED > 10: continue
                self.content[statement['statement']].append(year_data[statement['statement']])

        for statement in self.statements:
            for idx, fiscalyear in enumerate(self.content[statement['statement']][:-1]):
                for column in fiscalyear:
                    if 'YoY' in column:
                        if self.content[statement['statement']][idx - 1][column.replace(' YoY', '')]:
                            if not fiscalyear[column.replace(' YoY', '')] or not self.content[statement['statement']][idx - 1][column.replace(' YoY', '')]: continue
                            current_value = float(fiscalyear[column.replace(' YoY', '')])
                            old_value = float(self.content[statement['statement']][idx - 1][column.replace(' YoY', '')])
                            if old_value and old_value != 0:
                                fiscalyear[column] = round(abs(100 - (current_value / old_value) * 100), 2)
    
    def find_company_info(self, ticker):
        headers = self.headers.copy()
        headers['content-type'] = 'application/x-www-form-urlencoded'
        data = '{"params":"query=' + ticker + '&distinct=2"}'
        response = requests.post('https://tjpay1dyt8-3.algolianet.com/1/indexes/tikr-feb/query?x-algolia-agent=Algolia%20for%20JavaScript%20(3.35.1)%3B%20Browser%20(lite)&x-algolia-application-id=TJPAY1DYT8&x-algolia-api-key=d88ea2aa3c22293c96736f5ceb5bab4e', headers=headers, data=data)
        if response.json()['hits']:
            tid = response.json()['hits'][0]['tradingitemid']
            cid = response.json()['hits'][0]['companyid']
            return tid, cid
        else:
            return None, None

    def export(self, filename):
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            for statement in self.statements:
                statement = statement['statement']
                if not self.content[statement]: continue
                columns = list(self.content[statement][0].keys())
                years = [x['year'] for x in self.content[statement]]
                df = pd.DataFrame(self.content[statement], columns=columns, index=years)
                df = df.drop(columns='year')
                df.T.to_excel(writer, sheet_name=statement)
                
                # FIX SHEET FORMAT
                worksheet = writer.sheets[statement]
                worksheet.write('A1', filename.split('_')[0])
                for idx, col in enumerate(df):
                    if idx == 0:
                        worksheet.set_column(idx, idx, 45)
                    else:
                        worksheet.set_column(idx, idx, 15)

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

if __name__ == '__main__':
    scraper = TIKR()
    print(f'[ . ] TIKR Statements Scraper: {bcolors.OKGREEN}Ready{bcolors.ENDC}')
    user_input_1 = input(f'{bcolors.WARNING}[...]{bcolors.ENDC} Please enter ticker symbol or company name: ')
    tid, cid = scraper.find_company_info(user_input_1)
    if not (tid and cid):
        print(f'[ - ] {bcolors.FAIL}[Error]{bcolors.ENDC}: Could not find company')
        exit()
    print(f'[ . ] {bcolors.OKGREEN}Found company{bcolors.ENDC}: {user_input_1} [Trading ID: {tid}] [Company ID: {cid}]')
    print('[ . ] Starting scraping...')
    scraper.getFinancials(tid, cid)
    print('[ + ] Exporting Statements')

    filename = user_input_1 + '_' + datetime.datetime.now().strftime('%Y-%m-%d') + '.xlsx'
    scraper.export(filename)
    print(f'[ . ] {bcolors.OKGREEN}[Done]{bcolors.ENDC}: Exported to', filename)