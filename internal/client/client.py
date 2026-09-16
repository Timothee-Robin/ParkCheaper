import requests
import json
from internal.models.account import Account


class Client():
    def __init__(self):
        
        self.session = requests.Session()
        
        self.session.headers.update({
            "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        })
        
    def setAccount(self,account:Account):
        self.account = account
        
        
        
    def get(self,url,headers=None):
        
        r = self.session.get(url,headers)
        
        if r.status_code ==403:
            raise(ValueError("Error 403 Blocked"))

        return r
        
    def post(self,url,headers=None,payload=None,json=None):
            
        r = self.session.post(url,headers=headers,data=payload,json=json)
        
        if r.status_code ==403:
            raise(ValueError("Error 403 Blocked"))
        
        return r