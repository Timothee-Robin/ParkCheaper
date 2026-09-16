from internal.client.client import Client




class AuthServices():
    def __init__(self,client:Client):
        self.client = client

    def login(self):
        url = "https://auth.paybyphoneapis.com/consumer/token"
        
        payload = f'grant_type=password&client_id=paybyphone_web&username=%2B{self.client.account.phone}&password={self.client.account.pswd}'
        
        headers = {
            'accept': '*/*',
            'accept-language': 'fr-FR,fr;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://m.paybyphone.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://m.paybyphone.com/',
            'sec-ch-ua': '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sec-gpc': '1',
            'x-pbp-clienttype': 'WebApp'
        }
        
        r = self.client.post(url,headers=headers,payload=payload)
        
        print(r.content)
        
        
        