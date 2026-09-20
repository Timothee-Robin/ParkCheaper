from dataclasses import dataclass

@dataclass
class Card():
    maskedCardNumber:str
    cardType:str
    paymentAccountId:str