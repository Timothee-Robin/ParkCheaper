import requests
import json
from internal.models.account import Account


class Client():
    def __init__(self):
        
        self.session = requests.Session()
        
        self.session.headers.update({
            "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        })
        self.accessToken = None
        self.refreshToken = None
        
        
    def setAccount(self,account:Account):
        self.account = account
        
        
        
    def get(self,url,headers=None):
        
        r = self.session.get(url,headers)
        
        if r.status_code ==403:
            raise(ValueError("Error 403 Blocked"))

        return r
        
    def post(self,url,headers=None,payload=None,json=None):
            
        r = self.session.post(url,headers=headers,data=payload,json=json)
        
        if r.status_code==401 and url != "https://auth.paybyphoneapis.com/consumer/token":
            print("Error : Account not logged in refreshing...")
            self.refreshToken()
            self.post(url,headers=headers,payload=payload)
        
        if r.status_code ==403:
            raise(ValueError("Error 403 Blocked"))
        
        return r
    
    def refreshToken(self):
        url = "https://auth.paybyphoneapis.com/consumer/token"

        payload = f'grant_type=refresh_token&refresh_token={self.refreshToken}&client_id=paybyphone_web'
        headers = {
        'accept': '*/*',
        'accept-language': 'fr-FR,fr;q=0.7',
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

        r = self.post(url,headers=headers,payload=payload)
        data = r.json()
        if data and "access_token" in data:
            self.accessToken = data["access_token"]
            self.refreshToken = data["refresh_token"]
        
        elif data and "error" in data:
            raise ValueError(f"Error refreshing Token: {data["error_description"]}") 
        else:
            raise ValueError("Error refreshing Token")
    