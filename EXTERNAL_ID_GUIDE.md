# Guia de Uso do ID Externo no GLPI

## O que é o ID Externo?

O campo `external_id` no GLPI permite que você associe um identificador de outro sistema ao ticket. Isso é útil para:

- Rastrear tickets que foram criados a partir de outros sistemas (CRM, ERP, etc.)
- Manter sincronização entre sistemas
- Facilitar a busca de tickets por ID de sistemas externos

## Como adicionar ID Externo ao criar um ticket

### Exemplo básico

```python
ticket_data = {
    'name': 'Título do ticket',
    'content': 'Descrição do problema',
    'entities_id': 0,
    'externalid': 'MEU_SISTEMA_12345'  # ID externo
}
```

### Exemplo completo

```python
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Configurações
base_url = os.getenv("GLPI_BASE_URL")
app_token = os.getenv("APP_TOKEN")
user_token = os.getenv("USER_TOKEN")

# Inicializa sessão
session_response = requests.get(
    f"{base_url}/initSession",
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'user_token {user_token}',
        'App-Token': app_token
    },
    verify=False
)

session_token = session_response.json()['session_token']

# Cria ticket com ID externo
ticket_data = {
    'name': 'Problema com sistema',
    'content': 'Descrição detalhada do problema',
    'entities_id': 0,
    'externalid': 'CRM-2024-001',  # ID do CRM, por exemplo
    'type': 1,  # 1 = Incidente
    'urgency': 3,  # 3 = Média
    'impact': 3,  # 3 = Médio
    'priority': 3  # 3 = Média
}

response = requests.post(
    f"{base_url}/Ticket",
    headers={
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    },
    json={'input': ticket_data},
    verify=False
)

result = response.json()
print(f"Ticket criado: ID {result['id']}")
print(f"ID Externo: CRM-2024-001")
```

## Campos disponíveis ao criar um ticket

| Campo | Tipo | Descrição | Valores |
|-------|------|-----------|---------|
| `name` | string | Título do ticket | Obrigatório |
| `content` | string | Descrição/conteúdo | Obrigatório |
| `entities_id` | int | ID da entidade | 0 = Root entity |
| `externalid` | string | ID externo | Qualquer string |
| `type` | int | Tipo do ticket | 1 = Incidente, 2 = Requisição |
| `urgency` | int | Urgência | 1-5 (1=Muito baixa, 5=Muito alta) |
| `impact` | int | Impacto | 1-5 (1=Muito baixo, 5=Muito alto) |
| `priority` | int | Prioridade | 1-6 (calculada automaticamente) |
| `itilcategories_id` | int | ID da categoria | ID da categoria ITIL |
| `requesttypes_id` | int | Origem da requisição | 1=Helpdesk, 2=E-mail, etc. |
| `status` | int | Status | 1=Novo, 2=Em andamento, etc. |

## Buscando tickets por ID Externo

Você pode buscar tickets usando o ID externo através da API de busca:

```python
# Busca ticket por ID externo
search_url = f"{base_url}/search/Ticket"
params = {
    'criteria[0][field]': 'externalid',
    'criteria[0][searchtype]': 'equals',
    'criteria[0][value]': 'CRM-2024-001'
}

response = requests.get(
    search_url,
    headers={
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    },
    params=params,
    verify=False
)

tickets = response.json()
```

## Exemplos de uso

### 1. Integração com CRM

```python
# ID do ticket no CRM
crm_ticket_id = "CRM-2024-12345"

ticket_data = {
    'name': 'Solicitação do cliente via CRM',
    'content': 'Cliente reportou problema através do CRM',
    'entities_id': 0,
    'externalid': crm_ticket_id
}
```

### 2. Integração com sistema de e-commerce

```python
# ID do pedido no e-commerce
order_id = "ORDER-2024-98765"

ticket_data = {
    'name': f'Problema com pedido {order_id}',
    'content': 'Cliente reportou problema com entrega',
    'entities_id': 0,
    'externalid': order_id
}
```

### 3. Integração com chatbot

```python
# ID da conversa no chatbot
conversation_id = "CHAT-SESSION-ABC123"

ticket_data = {
    'name': 'Atendimento via chatbot',
    'content': 'Cliente iniciou atendimento via chatbot',
    'entities_id': 0,
    'externalid': conversation_id
}
```

## Script de exemplo

Execute o script de exemplo:

```bash
python create_ticket_with_external_id.py
```

Este script demonstra como criar um ticket com ID externo e todos os campos relevantes.

## Notas importantes

1. O campo `externalid` aceita qualquer string, então você pode usar o formato que preferir
2. O ID externo não precisa ser único no GLPI (você pode ter múltiplos tickets com o mesmo ID externo)
3. É recomendado usar um formato consistente para facilitar buscas (ex: `SISTEMA-TIPO-ID`)
4. O ID externo é visível na interface do GLPI no formulário do ticket como "ID externo"
