#[BEGIN CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {03/03/2026}
from . import *

CoreConfig.configure(
    load_from_env=False,                    
    db_user="XX",
    db_password="XX",
    db_server="XX",
    db_database="XX"
)

database = data()
database.connect()

class NumberSequenceTable(TableController):

    def __init__(self, db):
        super().__init__(db, source_name="NumberSequenceTable")

        self.RECID = Recid()
        self.SEQUENCEID = EDTController("any", DataType.String)
        self.NAMEALIAS = EDTController("any", DataType.String)
        self.DESCRIPTION = EDTController("any", DataType.String)
        self.ISDISABLE = EDTController("bool", DataType.Boolean)
        self.PREVNUM = EDTController("onlyNumbers", DataType.Number)
        self.CURNUM = EDTController("onlyNumbers", DataType.Number)
        self.NEXTNUM = EDTController("onlyNumbers", DataType.Number)
        self.MINNUM = EDTController("onlyNumbers", DataType.Number)
        self.MAXNUM = EDTController("onlyNumbers", DataType.Number)
        self.CREATEDATETIME = EDTController("datetime", DataType.DateTime)

class NumberSequenceLines(TableController):
    def __init__(self, db):
        super().__init__(db, source_name="NumberSequenceLine")

        self.RECID = Recid()
        self.REFRECID = EDTController("onlyNumbers",DataType.Number)
        self.PIECETYPE = EDTController("onlyNumbers", DataType.Number)
        self.SEQPIECE = EDTController("any", DataType.String)
        self.LINENUM = EDTController("onlyNumbers", DataType.Number)


with database.transaction() as trs:
    numSeq = NumberSequenceController(NumberSequenceTable(trs), NumberSequenceLines(trs))
    """
    res = numSeq.createNumberSequence(
        header={"seqId": "TESTE123",
                "name": "TESTE_TESTE",
                "desc": "So pra testar se ta funcionando",
                "isdis": 0,
                "minnum": 1,
                "maxnum": 9999
        },
        lines=[
            {"pieceType": 1, "piece": "teste",  "place": 1},
            {"pieceType": 2, "piece": "#",      "place": 2},
            {"pieceType": 3, "piece": "",       "place": 3},
        ]
    )
    """
    res = numSeq.getNextNum(2)
    

#[END CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {03/03/2026}