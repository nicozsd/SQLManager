from SQLManager import TableController, EDTController
from model import EDTPack, EnumPack

class numbersequencetable(TableController):
    
    '''
    Tabela: numbersequencetable
    args:
        db_controller: Banco de dados ou transação
    '''
    def __init__(self, db):
        super().__init__(db=db, source_name="numbersequencetable")
    
        self.RECID = EDTController('any', EnumPack.DataType.Number)
        self.SEQUENCEID = EDTController('any', EnumPack.DataType.String, None, 10)
        self.NAMEALIAS = EDTController('any', EnumPack.DataType.String, None, 100)
        self.DESCRIPTION = EDTController('any', EnumPack.DataType.String, None, 200)
        self.ISDISABLE = EDTController('any', EnumPack.DataType.Number)
        self.PREVNUM = EDTController('any', EnumPack.DataType.Number)
        self.CURNUM = EDTController('any', EnumPack.DataType.Number)
        self.NEXTNUM = EDTController('any', EnumPack.DataType.Number)
        self.MINNUM = EDTController('any', EnumPack.DataType.Number)
        self.MAXNUM = EDTController('any', EnumPack.DataType.Number)
        self.CREATEDATETIME = EDTController('any', EnumPack.DataType.String)
