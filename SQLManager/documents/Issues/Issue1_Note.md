# Issues [#1-TableController Remodel](https://github.com/nickzsd/SQLManager/issues/1) - SQLManager

## O que foi feito
Foi criada pasta managers para realizar a separação de cada necessidade da CRUD, sendo cada um, um arquivo proprio e pessoal, sendo totalmente dedicado. 

### Managers Criados
>**(C)** `Insert_Manager` - Gerenciador de processos de inserção.  
>**(R)** `Select_Manager` - Gerenciador de processos de buscas.  
>**(U)** `Update_Manager` - Gerenciador de processos de Atualização  
>**(D)** `Delete_Manager` - Gerenciador de processos de inserção  

Seus metodos e funcionalidades posteriores não foram alteradas e toda as funções foram mantidas, pequenas melhorias de codigo foram realizadas, sendo a mudança principal o antigo uso de ttsbegin manual.

## Exemplos

### Antigo
Usa de niveis de TTS manuais.
```python
try
    Controller.db.ttsbegin()
    {FUNÇÕES}
    Controller.db.ttscommit()
except Exception as e:
    Controller.db.ttsabort()
    print({e})
```

### Novo
Usa a transação automatica do banco.
```python
try
    with Controller.db.transaction() as trs
        {FUNÇÕES}    
except Exception as e:
    print({e})
```

> Todas as necessides de remodelar e deixar pontos do codigo mais limpo foram realizados como necessario.