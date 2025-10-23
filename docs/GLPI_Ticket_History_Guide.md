# Guia: Recuperando Histórico de Tickets no GLPI

## Visão Geral

Este documento apresenta as principais abordagens para recuperar o histórico completo de tickets no GLPI utilizando a API REST e GraphQL. O GLPI oferece múltiplas formas de acessar dados históricos, incluindo logs de auditoria, alterações de status e acompanhamentos.

## Métodos Principais

### 1. API REST - Endpoint de Logs

#### Recuperar Logs de um Ticket Específico
```bash
curl -X GET \
-H 'Content-Type: application/json' \
-H "Session-Token: SEU_SESSION_TOKEN" \
-H "App-Token: SEU_APP_TOKEN" \
'https://seu-glpi.com/apirest.php/Ticket/{ID_DO_TICKET}/Log'
```

#### Recuperar Logs de um Usuário
```bash
curl -X GET \
-H 'Content-Type: application/json' \
-H "Session-Token: SEU_SESSION_TOKEN" \
-H "App-Token: SEU_APP_TOKEN" \
'https://seu-glpi.com/apirest.php/User/{ID_DO_USUARIO}/Log'
```

**Resposta Esperada:**
```json
[
   {
      "id": 22117,
      "itemtype": "Ticket",
      "items_id": 123,
      "itemtype_link": "User",
      "linked_action": 17,
      "user_name": "joao.silva (27)",
      "date_mod": "2025-10-13 10:00:59",
      "id_search_option": 0,
      "old_value": "",
      "new_value": "Em andamento (4)"
   },
   {
      "id": 22118,
      "itemtype": "Ticket", 
      "items_id": 123,
      "itemtype_link": "",
      "linked_action": 0,
      "user_name": "maria.souza (2)",
      "date_mod": "2025-10-13 10:01:22",
      "id_search_option": 80,
      "old_value": "Aberto (1)",
      "new_value": "Resolvido (5)"
   }
]
```

### 2. API REST - Busca Avançada

#### Buscar Todos os Tickets com Histórico
```bash
curl -g -X GET \
-H 'Content-Type: application/json' \
-H "Session-Token: SEU_SESSION_TOKEN" \
-H "App-Token: SEU_APP_TOKEN" \
'https://seu-glpi.com/apirest.php/search/Ticket?criteria[0][link]=AND&criteria[0][field]=1&criteria[0][searchtype]=contains&criteria[0][value]=&range=0-1000&forcedisplay[0]=1&forcedisplay[1]=15&forcedisplay[2]=16&forcedisplay[3]=17&forcedisplay[4]=18'
```

#### Parâmetros Úteis:
- `range`: Define a paginação (ex: `0-1000` para os primeiros 1000 registros)
- `forcedisplay`: Força a exibição de campos específicos
- `criteria`: Permite filtrar por datas, status, usuários, etc.

### 3. GraphQL - Consulta Flexível

#### Consulta Básica de Tickets com Histórico
```graphql
query {
    Ticket(limit: 100, filter: "date_creation=ge=2025-01-01") {
        id
        name
        content
        status {
            id
            name
        }
        date_creation
        date_mod
        users_id_recipient {
            id
            name
        }
        _logs {
            id
            date_mod
            user_name
            old_value
            new_value
            linked_action
        }
    }
}
```

#### Consulta Avançada com Filtros
```graphql
query {
    Ticket(filter: "status=gt=1 and date_creation=ge=2025-09-01", limit: 500) {
        id
        name
        status {
            id
            name
        }
        urgency
        impact
        priority
        date_creation
        date_mod
        resolve_date
        close_date
        users_id_recipient {
            id
            name
        }
        users_id_lastupdater {
            id
            name
        }
        itilfollowups {
            id
            content
            date
            users_id {
                id
                name
            }
        }
        itiltasks {
            id
            content
            date
            users_id {
                id
                name
            }
        }
    }
}
```

### 4. Múltiplos Itens em Uma Requisição

```bash
curl -X GET \
-H 'Content-Type: application/json' \
-H "Session-Token: SEU_SESSION_TOKEN" \
-H "App-Token: SEU_APP_TOKEN" \
-d '{
  "items": [
    {"itemtype": "Ticket", "items_id": 123},
    {"itemtype": "Ticket", "items_id": 124},
    {"itemtype": "Ticket", "items_id": 125}
  ],
  "with_logs": true
}' \
'https://seu-glpi.com/apirest.php/getMultipleItems'
```

## Filtros RSQL para Histórico

### Operadores Disponíveis:
- `==` : Igual a
- `!=` : Diferente de
- `=in=` : Contido em
- `=out=` : Não contido em
- `=lt=` : Menor que
- `=le=` : Menor ou igual a
- `=gt=` : Maior que
- `=ge=` : Maior ou igual a
- `=like=` : Contém (case sensitive)
- `=ilike=` : Contém (case insensitive)

### Exemplos de Filtros:
```bash
# Tickets criados após 01/09/2025
filter="date_creation=ge=2025-09-01"

# Tickets com status diferente de "Fechado"
filter="status!=6"

# Tickets de usuários específicos
filter="users_id_recipient=in=(123,456,789)"

# Tickets modificados no último mês
filter="date_mod=ge=2025-09-21"
```

## Campos Importantes para Histórico

### Principais Campos de Ticket:
- `id`: Identificador único
- `name`: Título do ticket
- `content`: Descrição
- `status`: Status atual
- `date_creation`: Data de criação
- `date_mod`: Data da última modificação
- `resolve_date`: Data de resolução
- `close_date`: Data de fechamento
- `users_id_recipient`: Usuário solicitante
- `users_id_lastupdater`: Último atualizador

### Campos de Log:
- `id`: ID do log
- `itemtype`: Tipo do item (geralmente "Ticket")
- `items_id`: ID do ticket
- `itemtype_link`: Tipo do item relacionado
- `linked_action`: Ação realizada
- `user_name`: Nome do usuário que realizou a ação
- `date_mod`: Data da modificação
- `old_value`: Valor anterior
- `new_value`: Novo valor

## Autenticação

### 1. Inicializar Sessão
```bash
curl -X GET \
-H 'Content-Type: application/json' \
-H "Authorization: Basic BASE64(login:password)" \
-H "App-Token: SEU_APP_TOKEN" \
'https://seu-glpi.com/apirest.php/initSession'
```

### 2. Usar Token de Sessão
Após obter o session_token, inclua-o nos headers:
```bash
-H "Session-Token: SESSION_TOKEN_OBTIDO"
```

### 3. Encerrar Sessão
```bash
curl -X GET \
-H 'Content-Type: application/json' \
-H "Session-Token: SESSION_TOKEN" \
-H "App-Token: SEU_APP_TOKEN" \
'https://seu-glpi.com/apirest.php/killSession'
```

## Boas Práticas

### 1. Paginação
- Use o parâmetro `range` para controlar a quantidade de dados
- GLPI geralmente limita a 1000 resultados por página
- Implemente paginação para grandes volumes de dados

### 2. Performance
- Use `expand_dropdowns=false` para respostas mais rápidas
- Especifique apenas os campos necessários com `forcedisplay`
- Considere usar GraphQL para consultas complexas

### 3. Tratamento de Erros
- Verifique sempre os códigos de status HTTP
- Implemente retry para falhas temporárias
- Monitore limites de taxa da API

### 4. Cache
- Cacheie dados que não mudam frequentemente
- Use o header `Last-Modified` para validação
- Implemente cache local para consultas recorrentes

## Exemplo Completo em Python

```python
import requests
import json
from datetime import datetime, timedelta

class GLPITicketHistory:
    def __init__(self, base_url, app_token, username, password):
        self.base_url = base_url.rstrip('/')
        self.app_token = app_token
        self.session_token = self._init_session(username, password)
        
    def _init_session(self, username, password):
        """Inicializa sessão com GLPI"""
        auth_string = f"{username}:{password}"
        import base64
        auth_b64 = base64.b64encode(auth_string.encode()).decode()
        
        response = requests.get(
            f"{self.base_url}/apirest.php/initSession",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Basic {auth_b64}',
                'App-Token': self.app_token
            }
        )
        
        if response.status_code == 200:
            return response.json()['session_token']
        else:
            raise Exception(f"Erro na autenticação: {response.text}")
    
    def get_ticket_logs(self, ticket_id):
        """Recupera logs de um ticket específico"""
        response = requests.get(
            f"{self.base_url}/apirest.php/Ticket/{ticket_id}/Log",
            headers={
                'Content-Type': 'application/json',
                'Session-Token': self.session_token,
                'App-Token': self.app_token
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erro ao buscar logs: {response.text}")
    
    def get_all_tickets_history(self, start_date=None, end_date=None):
        """Recupera histórico completo de tickets"""
        # Construir filtro
        filter_parts = []
        if start_date:
            filter_parts.append(f"date_creation=ge={start_date}")
        if end_date:
            filter_parts.append(f"date_creation=le={end_date}")
        
        filter_string = " and ".join(filter_parts) if filter_parts else ""
        
        # Buscar tickets
        url = f"{self.base_url}/apirest.php/search/Ticket"
        params = {
            'range': '0-1000',
            'forcedisplay[0]': '1',  # ID
            'forcedisplay[1]': '15', # Status
            'forcedisplay[2]': '16', # Data criação
            'forcedisplay[3]': '17', # Data modificação
            'forcedisplay[4]': '18', # Usuário solicitante
        }
        
        if filter_string:
            params['filter'] = filter_string
        
        response = requests.get(
            url,
            params=params,
            headers={
                'Content-Type': 'application/json',
                'Session-Token': self.session_token,
                'App-Token': self.app_token
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erro ao buscar tickets: {response.text}")
    
    def close_session(self):
        """Encerra sessão"""
        requests.get(
            f"{self.base_url}/apirest.php/killSession",
            headers={
                'Content-Type': 'application/json',
                'Session-Token': self.session_token,
                'App-Token': self.app_token
            }
        )

# Exemplo de uso
if __name__ == "__main__":
    glpi = GLPITicketHistory(
        base_url="https://seu-glpi.com",
        app_token="SEU_APP_TOKEN",
        username="seu_usuario",
        password="sua_senha"
    )
    
    try:
        # Buscar tickets do último mês
        last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        tickets = glpi.get_all_tickets_history(start_date=last_month)
        
        print(f"Total de tickets encontrados: {tickets['totalcount']}")
        
        # Para cada ticket, buscar seus logs
        for ticket in tickets['data']:
            ticket_id = list(ticket.keys())[0]
            logs = glpi.get_ticket_logs(ticket_id)
            print(f"Ticket {ticket_id}: {len(logs)} alterações")
            
    finally:
        glpi.close_session()
```

## Conclusão

O GLPI oferece múltiplas abordagens para recuperar o histórico de tickets, cada uma com suas vantagens:

- **API REST Logs**: Ideal para auditoria e rastreabilidade específica
- **Search API**: Melhor para consultas complexas com filtros avançados  
- **GraphQL**: Perfeito para consultas otimizadas e dados aninhados
- **Multiple Items**: Eficiente para buscar dados de vários tickets simultaneamente

Escolha o método que melhor se adapta às suas necessidades específicas de integração e volume de dados.