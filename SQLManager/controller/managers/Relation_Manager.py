''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #5 / made by: Nicolas Santos / created: 09/03/2026 '''

import inspect
import types
from typing    import TYPE_CHECKING, Optional, Union, List, Dict, Any
from ..EDTController import EDTController
from ..BaseEnumController import BaseEnumController
from ._conditions_Managers import FieldCondition, BinaryExpression

if TYPE_CHECKING:
    from ...connection import database_connection as db
    from ..TableController import TableController

class RelationManager:
    '''
    Gerencia relações entre tabelas com auto-população via SELECT.
    
    Exemplo:
        class SellerPlans(TableController):
            def __init__(self, db):
                super().__init__(db, "SellerPlansTable")
                self.PLANID = EDTController("int", DataType.Number)
                
                # Define a relação
                self.relations = {
                    "mensalities": self.new_Relation(PlanMensalities)
                                      .on(self.PLANID, PlanMensalities.PLANID)
                }
        
        # Uso com auto-população
        seller_plan.select().with_relations("mensalities").where(seller_plan.PLANID == 5)
        # Agora: seller_plan.records[0] e seller_plan.relations["mensalities"].records estão populados
    '''
    def __init__(self, database, source_table: 'TableController', ref_table_class: type):
        self.database         = database
        self.source_table     = source_table
        self.ref_table_class  = ref_table_class
        self.ref_table        = None  # Instância será criada quando necessário
        
        # Campos de relacionamento
        self.source_field: Optional[Union[str, EDTController, BaseEnumController]] = None
        self.target_field: Optional[Union[str, EDTController, BaseEnumController]] = None
        
        # Tipo de JOIN (INNER, LEFT, RIGHT)
        self.join_type: str = 'LEFT'
        
        # Condições extras de WHERE para a relation
        self.where_condition: Optional[Union[FieldCondition, BinaryExpression]] = None
        
        # Records da relation (populado após SELECT)
        self.records: List[Dict[str, Any]] = []
        
    def on(self, source_field: Union[str, EDTController, BaseEnumController], 
           target_field: Union[str, EDTController, BaseEnumController]) -> 'RelationManager':
        '''
        Define os campos de relacionamento entre tabelas.
        
        Args:
            source_field: Campo da tabela origem (self) - EDT/Enum ou string
            target_field: Campo da tabela relacionada - EDT/Enum ou string
            
        Exemplo:
            .on(self.PLANID, "PLANID")  # Usando string para campo da tabela relacionada
            .on(self.PLANID, related_table.PLANID)  # Usando EDT
            
        Returns:
            RelationManager: Self para encadeamento
        '''
        self.source_field = source_field
        self.target_field = target_field
        return self
    
    def join_type_as(self, join_type: str) -> 'RelationManager':
        '''
        Define o tipo de JOIN (INNER, LEFT, RIGHT).
        
        Args:
            join_type: Tipo de JOIN (padrão: LEFT)
        
        Returns:
            RelationManager: Self para encadeamento
        '''
        self.join_type = join_type.upper()
        return self
    
    def where(self, condition: Union[FieldCondition, BinaryExpression]) -> 'RelationManager':
        '''
        Adiciona condições WHERE específicas para esta relation.
        Útil para filtrar dados relacionados (ex: apenas ativos).
        
        Args:
            condition: Condição WHERE
        
        Returns:
            RelationManager: Self para encadeamento
        '''
        self.where_condition = condition
        return self
    
    def get_instance(self) -> 'TableController':
        '''
        Retorna ou cria a instância da tabela relacionada.
        
        Returns:
            TableController: Instância da tabela relacionada
        '''
        if self.ref_table is None:
            ref_class = self.ref_table_class
            if isinstance(ref_class, types.ModuleType):
                resolved = self._resolve_table_class_from_module(ref_class)
                if resolved is None:
                    raise TypeError(f"Relation ref_table_class is a module ({ref_class.__name__}) and no TableController class could be resolved")
                self.ref_table_class = resolved
                ref_class = resolved
            self.ref_table = ref_class(self.database)
        return self.ref_table

    def _resolve_table_class_from_module(self, module):
        '''
        Resolve uma classe de TableController a partir de um módulo, se necessário.
        '''
        from ..TableController import TableController

        # Tenta usar __all__ se disponível
        if hasattr(module, '__all__'):
            for name in module.__all__:
                attr = getattr(module, name, None)
                if inspect.isclass(attr) and issubclass(attr, TableController):
                    return attr

        # Busca a primeira classe pública que herda de TableController
        for name in dir(module):
            if name.startswith('_'):
                continue
            attr = getattr(module, name, None)
            if inspect.isclass(attr) and issubclass(attr, TableController):
                return attr

        return None

    def clear(self):
        '''Limpa os records da relation'''
        self.records = []
        if self.ref_table:
            self.ref_table.clear()
            self.ref_table.records = []
    
    def set_records(self, records: List[Dict[str, Any]]):
        '''
        Define os records da relation e popula a instância da tabela.
        
        Args:
            records: Lista de registros da relation
        '''
        self.records = records
        
        # Popula a instância da tabela relacionada
        table = self.get_instance()
        table.records = records
        
        # Define o primeiro record como atual se existir
        if records:
            table.set_current(records[0])
    
    def _extract_field_name(self, field: Union[str, EDTController, BaseEnumController]) -> str:
        '''Extrai o nome do campo de um EDT/Enum ou string'''
        if isinstance(field, (EDTController, BaseEnumController)):
            return field.field_name
        return field
    
    def build_join_condition(self) -> Union[FieldCondition, BinaryExpression]:
        '''
        Constrói a condição de JOIN baseada nos campos definidos.
        
        Returns:
            Condição de JOIN para usar no SelectManager
        '''
        if self.source_field is None or self.target_field is None:
            raise ValueError(f"Campos de relação não definidos. Use .on(source_field, target_field)")
        
        # Obtém as instâncias EDT/Enum reais dos campos
        if isinstance(self.source_field, str):
            source_edt = self.source_table._get_field_instance(self.source_field)
        else:
            source_edt = self.source_field
        
        target_table = self.get_instance()
        if isinstance(self.target_field, str):
            target_edt = target_table._get_field_instance(self.target_field)
        else:
            target_edt = self.target_field
        
        # Cria a condição de igualdade
        return source_edt == target_edt
        
''' [END CODE] Project: SQLManager Version 4.0 / issue: #5 / made by: Nicolas Santos / created: 09/03/2026 '''