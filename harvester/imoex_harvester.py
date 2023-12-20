import requests

url = 'https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates/securities/USD/RUB'



if __name__ == '__main__':

    p = requests.get(url,params={'iss.only':'securities.current'}).json()['wap_rates']['data']
    for i in p:
        print(list(i))