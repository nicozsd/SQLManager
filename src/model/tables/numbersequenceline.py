from SQLManager import TableController, EDTController
from model import EDTPack, EnumPack

class numbersequenceline(TableController):
    
    '''
    Tabela: numbersequenceline
    args:
        db_controller: Banco de dados ou transação
    '''
    def __init__(self, db):
        super().__init__(db=db, source_name="numbersequenceline")
    
        self.RECID = EDTController('any', EnumPack.DataType.Number)
        self.REFRECID = EDTController('any', EnumPack.DataType.Number)
        self.PIECETYPE = EDTController('any', EnumPack.DataType.Number)
        self.SEQPIECE = EDTController('any', EnumPack.DataType.String, None, 5)
        self.LINENUM = EDTController('any', EnumPack.DataType.Number)
