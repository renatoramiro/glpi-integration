# Troubleshooting - Integração GLPI

## Erro: "Ticket não encontrado com external_id"

### Problema
Ao tentar adicionar uma mensagem usando `external_id`, você recebe o erro:
```
WARNING:__main__:Nenhum ticket encontrado com external_id: CONV-12345
```

### Causas Possíveis

#### 1. Ticket não foi criado com external_id

**Verificação:**
```bash
# Verifique se o ticket tem external_id
curl -X GET http://localhost:8080/apirest.php/Ticket/20 \
  -H "Session-Token: SEU_SESSION_TOKEN" \
  -H "App-Token: SEU_APP_TOKEN"
```

**Solução:**
Certifique-se de que ao criar o ticket, você está incluindo o campo `externalid`:

```python
ticket_data = {
    'name': 'Título do ticket',
    'content': 'Descrição',
    'entities_id': 0,
    'externalid': 'CONV-12345'  # ← IMPORTANTE!
}
```

#### 2. Nome do campo está incorreto

O GLPI pode usar `externalid` ou `external_id` dependendo da versão.

**Solução:**
Nosso código já tenta ambos os formatos:
```python
ticket_externalid = ticket.get('externalid') or ticket.get('external_id')
```

#### 3. Ticket está fora do range de busca

Por padrão, buscamos apenas os últimos 100 tickets.

**Solução:**
Use `ticket_id` em vez de `external_id`:

```bash
curl -X POST http://localhost:8000/api/add-message \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": 20,
    "message": "Mensagem do usuário",
    "user_name": "João Silva"
  }'
```

## Como Verificar se o Ticket Tem External ID

### Método 1: Via API

```bash
# 1. Inicie uma sessão
curl -X GET http://localhost:8080/apirest.php/initSession \
  -H "Content-Type: application/json" \
  -H "Authorization: user_token SEU_USER_TOKEN" \
  -H "App-Token: SEU_APP_TOKEN"

# Resposta: {"session_token": "abc123..."}

# 2. Busque o ticket
curl -X GET http://localhost:8080/apirest.php/Ticket/20 \
  -H "Session-Token: abc123..." \
  -H "App-Token: SEU_APP_TOKEN"

# Verifique se o campo "externalid" está presente na resposta
```

### Método 2: Via Interface do GLPI

1. Acesse o GLPI
2. Abra o ticket
3. Procure pelo campo "ID externo"
4. Verifique se está preenchido

## Soluções Alternativas

### Opção 1: Usar ticket_id

Se você sabe o ID do ticket no GLPI, use diretamente:

```bash
curl -X POST http://localhost:8000/api/add-message \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": 20,
    "message": "Mensagem",
    "user_name": "Usuário"
  }'
```

### Opção 2: Salvar o mapeamento

Quando criar um ticket, salve o mapeamento `conversation_id → ticket_id`:

```python
# Ao criar o ticket
response = requests.post(
    f"{GLPI_BASE_URL}/Ticket",
    headers=headers,
    json={'input': ticket_data}
)

ticket_id = response.json()['id']

# Salve o mapeamento (banco de dados, cache, etc.)
save_mapping(conversation_id='CONV-12345', ticket_id=ticket_id)

# Ao adicionar mensagem, use o ticket_id salvo
ticket_id = get_ticket_id_from_mapping('CONV-12345')
```

### Opção 3: Aumentar o range de busca

Edite o arquivo `ticket_webhook.py`:

```python
# Linha 237-241
params = {
    'range': '0-499',  # Aumentar de 100 para 500
    'order': 'DESC',
    'sort': 'id'
}
```

## Testando a Integração

### 1. Criar ticket com external_id

```bash
python create_ticket_with_external_id.py
```

Verifique a saída:
```
Ticket criado com sucesso!
ID do ticket no GLPI: 20
ID externo: SISTEMA_EXTERNO_12345
```

### 2. Verificar se o external_id foi salvo

```python
# Script de verificação
import requests
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("GLPI_BASE_URL")
app_token = os.getenv("APP_TOKEN")
user_token = os.getenv("USER_TOKEN")

# Inicia sessão
response = requests.get(
    f"{base_url}/initSession",
    headers={
        'Authorization': f'user_token {user_token}',
        'App-Token': app_token
    },
    verify=False
)

session_token = response.json()['session_token']

# Busca o ticket
ticket_id = 20  # Substitua pelo ID do seu ticket
response = requests.get(
    f"{base_url}/Ticket/{ticket_id}",
    headers={
        'Session-Token': session_token,
        'App-Token': app_token
    },
    verify=False
)

ticket = response.json()
print(f"Ticket {ticket_id}:")
print(f"  Nome: {ticket.get('name')}")
print(f"  External ID: {ticket.get('externalid')}")
```

### 3. Adicionar mensagem

```bash
curl -X POST http://localhost:8000/api/add-message \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "SISTEMA_EXTERNO_12345",
    "message": "Teste de mensagem",
    "user_name": "Teste"
  }'
```

## Logs Úteis

Ative o modo debug para ver mais informações:

```python
# No início do arquivo ticket_webhook.py
logging.basicConfig(level=logging.DEBUG)  # Mude de INFO para DEBUG
```

Isso mostrará todos os tickets sendo verificados:
```
DEBUG:__main__:Ticket 20: externalid = CONV-12345
DEBUG:__main__:Ticket 19: externalid = None
DEBUG:__main__:Ticket 18: externalid = EXT-12345
```

## Checklist de Verificação

- [ ] Ticket foi criado com o campo `externalid`
- [ ] O valor do `externalid` está correto
- [ ] O servidor webhook está rodando
- [ ] As credenciais do GLPI estão corretas no `.env`
- [ ] O ticket está entre os últimos 100 tickets criados
- [ ] O campo `externalid` não está vazio/null no GLPI

## Contato e Suporte

Se o problema persistir:
1. Verifique os logs do webhook
2. Verifique os logs do GLPI
3. Teste com `ticket_id` em vez de `external_id`
4. Verifique se o campo está visível na interface do GLPI
