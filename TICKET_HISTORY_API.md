# API de Histórico de Tickets GLPI

Este documento descreve as novas rotas adicionadas para buscar o histórico completo de tickets do GLPI utilizando a API REST.

## Novas Rotas

### 1. POST /api/ticket-history

Busca o histórico completo de tickets usando payload JSON.

**Endpoint:** `POST /api/ticket-history`

**Content-Type:** `application/json`

#### Payload (Opcional)

```json
{
  "start_date": "2025-01-01",        // Data inicial no formato YYYY-MM-DD
  "end_date": "2025-12-31",          // Data final no formato YYYY-MM-DD
  "status_filter": 5,                // Filtro de status (número)
  "entity_id": 0,                    // ID da entidade
  "include_logs": true,              // Incluir logs de auditoria
  "include_followups": true,         // Incluir followups
  "include_solutions": true,         // Incluir soluções
  "max_tickets": 100                 // Número máximo de tickets
}
```

#### Exemplo de Requisição

```bash
curl -X POST http://localhost:8000/api/ticket-history \
     -H "Content-Type: application/json" \
     -d '{
       "start_date": "2025-01-01",
       "max_tickets": 50,
       "include_logs": true,
       "include_followups": true,
       "include_solutions": true
     }'
```

#### Resposta

```json
{
  "status": "success",
  "message": "Histórico de tickets obtido com sucesso",
  "summary": {
    "total_tickets": 25,
    "total_logs": 150,
    "total_followups": 80,
    "total_solutions": 20,
    "filters_applied": {
      "start_date": "2025-01-01",
      "end_date": null,
      "status_filter": null,
      "entity_id": null,
      "include_logs": true,
      "include_followups": true,
      "include_solutions": true,
      "max_tickets": 50
    }
  },
  "tickets": [
    {
      "id": 123,
      "details": {
        "id": 123,
        "name": "Título do Ticket",
        "content": "Descrição do ticket",
        "status": 5,
        "date_creation": "2025-01-15 10:30:00",
        "date_mod": "2025-01-16 14:20:00",
        "externalid": "CONV-12345"
      },
      "search_info": {
        "1": "Título do Ticket",
        "12": "5",
        "15": "2025-01-15 10:30:00"
      },
      "logs": [
        {
          "id": 1001,
          "itemtype": "Ticket",
          "items_id": 123,
          "itemtype_link": "User",
          "linked_action": 17,
          "user_name": "joao.silva (27)",
          "date_mod": "2025-01-15 10:30:00",
          "old_value": "",
          "new_value": "Aberto (1)"
        }
      ],
      "followups": [
        {
          "id": 501,
          "content": "Resposta do consultor",
          "date_creation": "2025-01-15 11:00:00",
          "users_id": 42
        }
      ],
      "solutions": [
        {
          "id": 201,
          "content": "Solução aplicada",
          "date_creation": "2025-01-16 14:20:00",
          "users_id": 42
        }
      ]
    }
  ]
}
```

### 2. GET /api/ticket-history

Busca o histórico completo de tickets usando parâmetros de query.

**Endpoint:** `GET /api/ticket-history`

#### Parâmetros de Query

- `start_date` (string, opcional): Data inicial no formato YYYY-MM-DD
- `end_date` (string, opcional): Data final no formato YYYY-MM-DD
- `status_filter` (int, opcional): Filtro de status
- `entity_id` (int, opcional): ID da entidade
- `include_logs` (bool, default: true): Incluir logs de auditoria
- `include_followups` (bool, default: true): Incluir followups
- `include_solutions` (bool, default: true): Incluir soluções
- `max_tickets` (int, default: 100): Número máximo de tickets

#### Exemplo de Requisição

```bash
# Buscar tickets solucionados
curl -X GET "http://localhost:8000/api/ticket-history?status_filter=5&max_tickets=10"

# Buscar tickets do último mês
curl -X GET "http://localhost:8000/api/ticket-history?start_date=2025-01-01&max_tickets=20"

# Buscar sem logs (mais rápido)
curl -X GET "http://localhost:8000/api/ticket-history?include_logs=false&max_tickets=50"
```

## Estrutura dos Dados

### Detalhes do Ticket (`details`)

- `id`: ID do ticket
- `name`: Título do ticket
- `content`: Descrição completa
- `status`: Status atual (número)
- `date_creation`: Data de criação
- `date_mod`: Data da última modificação
- `externalid`: ID externo (se existir)

### Logs de Auditoria (`logs`)

- `id`: ID do log
- `itemtype`: Tipo do item (geralmente "Ticket")
- `items_id`: ID do ticket
- `itemtype_link`: Tipo do item relacionado
- `linked_action`: Ação realizada
- `user_name`: Nome do usuário que realizou a ação
- `date_mod`: Data da modificação
- `old_value`: Valor anterior
- `new_value`: Novo valor

### Followups (`followups`)

- `id`: ID do followup
- `content`: Conteúdo da mensagem
- `date_creation`: Data de criação
- `users_id`: ID do usuário que criou

### Soluções (`solutions`)

- `id`: ID da solução
- `content`: Conteúdo da solução
- `date_creation`: Data de criação
- `users_id`: ID do usuário que aplicou

## Filtros Disponíveis

### Status

- `1`: Aberto (Incoming)
- `2`: Atribuído (Assigned)
- `3`: Planejado (Planned)
- `4`: Em andamento (In progress)
- `5`: Solucionado (Solved)
- `6`: Fechado (Closed)

### Datas

- Formato: `YYYY-MM-DD`
- `start_date`: Inclusive
- `end_date`: Inclusive

## Performance e Boas Práticas

### Paginação

- Use `max_tickets` para limitar o número de resultados
- GLPI geralmente limita a 1000 resultados por página
- Para grandes volumes, faça múltiplas requisições

### Otimização

- Desative `include_logs` se não precisar de auditoria (melhora performance)
- Use filtros de data para reduzir o volume de dados
- Especifique apenas os campos que precisa

### Exemplos de Uso

#### 1. Buscar tickets recentes com logs completos

```bash
curl -X POST http://localhost:8000/api/ticket-history \
     -H "Content-Type: application/json" \
     -d '{
       "start_date": "2025-01-01",
       "max_tickets": 10,
       "include_logs": true,
       "include_followups": true,
       "include_solutions": true
     }'
```

#### 2. Buscar apenas tickets solucionados (sem logs para performance)

```bash
curl -X GET "http://localhost:8000/api/ticket-history?status_filter=5&include_logs=false&max_tickets=50"
```

#### 3. Buscar tickets de uma entidade específica

```bash
curl -X POST http://localhost:8000/api/ticket-history \
     -H "Content-Type: application/json" \
     -d '{
       "entity_id": 1,
       "start_date": "2025-01-01",
       "max_tickets": 25
     }'
```

## Testes

Use o script `test_ticket_history.py` para testar as rotas:

```bash
python test_ticket_history.py
```

O script testa:
- ✅ Saúde do serviço
- ✅ Rota POST com diferentes filtros
- ✅ Rota GET com parâmetros
- ✅ Busca por intervalo de datas
- ✅ Exemplos de uso

## Integração

### Python

```python
import requests

# Buscar histórico completo
response = requests.post(
    "http://localhost:8000/api/ticket-history",
    json={
        "start_date": "2025-01-01",
        "max_tickets": 10,
        "include_logs": True
    }
)

if response.status_code == 200:
    data = response.json()
    tickets = data['tickets']
    for ticket in tickets:
        print(f"Ticket {ticket['id']}: {ticket['details']['name']}")
```

### JavaScript

```javascript
// Buscar histórico via POST
const response = await fetch('http://localhost:8000/api/ticket-history', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        start_date: '2025-01-01',
        max_tickets: 10,
        include_logs: true
    })
});

const data = await response.json();
console.log(`Total de tickets: ${data.summary.total_tickets}`);
```

## Erros Comuns

### 400 Bad Request

- Payload JSON inválido
- Parâmetros com tipos incorretos

### 500 Internal Server Error

- Falha na conexão com GLPI
- Credenciais inválidas
- Timeout na requisição

### Soluções

1. Verifique as variáveis de ambiente:
   ```bash
   echo $GLPI_BASE_URL
   echo $USER_TOKEN
   echo $APP_TOKEN
   ```

2. Teste a conexão com GLPI:
   ```bash
   curl -H "App-Token: $APP_TOKEN" \
        -H "Authorization: user_token $USER_TOKEN" \
        "$GLPI_BASE_URL/initSession"
   ```

3. Verifique os logs da aplicação para detalhes do erro.

## Monitoramento

A API gera logs detalhados que podem ser usados para monitoramento:

- Número de tickets processados
- Tempo de resposta
- Erros de conexão
- Uso de filtros

Use esses logs para identificar gargalos e otimizar o desempenho.