''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

import sys
import os

# Ajuste de path para importar o SQLManager corretamente
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager.controller.RouterController import AutoRouter

from SQLManager.CoreConfig import CoreConfig
from SQLManager.connection import database_connection
from SQLManager.controller import *

# Definição da Tabela de Teste (Mapeia a tabela SQL criada no banco)
class AutoRouterTest(TableController):
    def __init__(self, db):
        super().__init__(db, "AutoRouterTest")
        self.RECID = EDTController("onlyNumbers", int)
        self.NAME = EDTController("any", str)
        self.PRICE = EDTController("float", float)
        self.ACTIVE = EDTController("bool", bool)

class TestAutoRouterIntegration():
    """
    Testando o AutoRouter com banco de dados real.
    
    Aqui a gente valida se tudo funciona direitinho com as operações básicas de CRUD.
    Precisa ter a tabela AutoRouterTest com os campos: RECID, NAME, PRICE e ACTIVE.
    """
    
    def __init__(self):
        config_dict = {
            'db_server': 'XX',
            'db_database': 'XX',
            'db_user': 'XX',
            'db_password': 'XX',
            'router_config': {
                'enable_dynamic_routes': True
            },
            'custom_regex': {
                'CompanyEmail': r'^[\w\.-]+@mycompany\.com$'
            }
        }        
    
        CoreConfig.configure_from_dict(config_dict)

        self.db = database_connection()
        self.db.connect()

        self.AutoRouter = AutoRouter(self.db)        

        pass    
    
    # TESTANDO AS OPERAÇÕES CRUD 
    def test_1_insert_success(self):
        """Testando se consegue inserir um produto novo (POST)"""
        print("\n[TESTE 1] Inserindo produto...")
        
        payload = {
            "NAME": "Mouse Gamer RGB",
            "PRICE": 150.99,
            "ACTIVE": True
        }
        
        response = self.AutoRouter.handle_request("POST", "AutoRouterTest", body=payload)
        print(f"Resposta: {response}")                

    def test_2_get_by_id(self):
        """Buscando produto por ID (GET)"""
        print("\n[TESTE 2] Buscando por ID...")
        
        # Insere um produto primeiro
        payload = {"NAME": "Teclado Mecânico", "PRICE": 320.00, "ACTIVE": True}
        create_resp = self.AutoRouter.handle_request("POST", "AutoRouterTest", body=payload)
        recid = str(create_resp['data']['RECID'])
        
        # Agora busca esse produto
        response = self.AutoRouter.handle_request("GET", "AutoRouterTest", path_parts=[recid])
        print(f"Resposta: {response}")                

    def test_3_update_patch(self):
        """Atualizando dados de um produto (PATCH)"""
        print("\n[TESTE 3] Atualizando produto...")
        
        # Bota um produto lá
        payload = {"NAME": "Headset Gamer", "PRICE": 250.00, "ACTIVE": True}
        create_resp = self.AutoRouter.handle_request("POST", "AutoRouterTest", body=payload)
        recid = str(create_resp['data']['RECID'])
        
        # Atualiza preço e nome
        update_payload = {"PRICE": 199.90, "NAME": "Headset Gamer (PROMOÇÃO!)"}
        response = self.AutoRouter.handle_request("PATCH", "AutoRouterTest", path_parts=[recid], body=update_payload)
        print(f"Resposta: {response}")                
        
        # Confere se mudou mesmo
        get_resp = self.AutoRouter.handle_request("GET", "AutoRouterTest", path_parts=[recid])
        print(f"Produto atualizado: {get_resp}")        

    def test_4_list_with_filters(self):
        """Listando produtos com filtros (GET com query params)"""
        print("\n[TESTE 4] Listando com filtros...")
        
        # Coloca alguns produtos no banco
        self.AutoRouter.handle_request("POST", "AutoRouterTest", body={"NAME": "Mousepad Barato", "PRICE": 15.00, "ACTIVE": True})
        self.AutoRouter.handle_request("POST", "AutoRouterTest", body={"NAME": "Webcam Full HD", "PRICE": 280.00, "ACTIVE": True})
        self.AutoRouter.handle_request("POST", "AutoRouterTest", body={"NAME": "Cadeira Gamer Premium", "PRICE": 1500.00, "ACTIVE": False})
        
        # Busca só os que custam mais de 50 reais
        response = self.AutoRouter.handle_request(
            "GET", 
            "AutoRouterTest", 
            query_params={"PRICE_gt": "50", "page": "1", "limit": "10"}
        )
        print(f"Resposta: {response}")                

    def test_5_delete(self):
        """Deletando um produto (DELETE)"""
        print("\n[TESTE 5] Deletando produto...")
        
        # Cria um produto só pra deletar
        payload = {"NAME": "Produto Temporário", "PRICE": 10.00, "ACTIVE": True}
        create_resp = self.AutoRouter.handle_request("POST", "AutoRouterTest", body=payload)
        recid = str(create_resp['data']['RECID'])
        
        # Deleta
        response = self.AutoRouter.handle_request("DELETE", "AutoRouterTest", path_parts=[recid])
        print(f"Resposta: {response}")                
        
        # Confere se sumiu mesmo
        get_resp = self.AutoRouter.handle_request("GET", "AutoRouterTest", path_parts=[recid])
        print(f"Buscando produto deletado: {get_resp}")

    def test_6_decorator_with_named_args(self):
        """Testando chamada com argumentos nomeados"""
        print("\n[TESTE 6] Argumentos nomeados...")
        
        response = self.AutoRouter.handle_request(
            method="GET",
            table_name="AutoRouterTest",
            path_parts=[],
            query_params={"page": "1", "limit": "5"},
            body={}
        )
        
        print(f"Resposta: {response}")

        print("Argumentos nomeados funcionando!")

    def test_7_decorator_with_positional_args(self):
        """Testando chamada com argumentos posicionais"""
        print("\n[TESTE 7] Argumentos posicionais...")
        
        response = self.AutoRouter.handle_request("GET", "AutoRouterTest", [], {"limit": "5", 'PRICE_lt': "50"}, {})
        
        print(f"Resposta: {response}")
        print("Argumentos posicionais funcionando!")   

if __name__ == '__main__':
    """Roda todos os testes e mostra o resultado"""
    print("=" * 50)
    print("TESTANDO O AUTOROUTER")    
    print("=" * 50)    

    tests = TestAutoRouterIntegration()
    
    print("\n" + "=" * 50)

    ''' APROVADO
    print("TESTES 01")
    tests.test_1_insert_success()    
    '''

    ''' APROVADO
    print("TESTES 02")
    tests.test_2_get_by_id()
    '''

    ''' APROVADO
    print("TESTES 03")
    tests.test_3_update_patch()    
    '''

    ''' APROVADO
    print("TESTES 04")
    tests.test_4_list_with_filters()
    '''
    
    ''' APROVADO
    print("TESTES 05")
    tests.test_5_delete()
    '''

    ''' APROVADO
    print("TESTES 06")
    tests.test_6_decorator_with_named_args()
    '''
        
    print("TESTES 07")
    tests.test_7_decorator_with_positional_args()        

    print("=" * 50) 

#testes
__all__ = ["AutoRouterTest"]

''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

