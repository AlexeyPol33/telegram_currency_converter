

class NoDataBaseValueError(Exception):

    message:str
    status_code:int

    def __init__(self, message:str = None) -> None:
        super().__init__()
        self.message = message
        self.status_code = 404

    def to_dict(self):
        return {'message':self.message}
    
class CurrencyConversionError(Exception):
    message:str
    status_code:int

    def __init__(self, message:str = None) -> None:
        super().__init__()
        self.message = message
        self.status_code = 500
    dict()