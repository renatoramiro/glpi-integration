# Endpoints da API do GLPI Webhook

Este documento descreve todos os endpoints disponíveis na API do GLPI Webhook.

## Índice

1. [Endpoints da Plataforma](#endpoints-da-plataforma)
   - [Criar Ticket](#criar-ticket)
   - [Adicionar Mensagem](#adicionar-mensagem)
   - [Buscar Histórico de Tickets (POST)](#buscar-histórico-de-tickets-post)
   - [Buscar Histórico de Tickets (GET)](#buscar-histórico-de-tickets-get)
2. [Webhooks do GLPI](#webhooks-do-glpi)
   - [Followup Adicionado](#followup-adicionado)
   - [Ticket Fechado](#ticket-fechado)
   - [Debug](#debug)
3. [Endpoints de Verificação](#endpoints-de-verificação)
   - [Health Check](#health-check)

## Endpoints da Plataforma

### Criar Ticket

**Endpoint:** `POST /api/create-ticket`

Cria um novo ticket no GLPI a partir de um ID da plataforma.

**Payload esperado:**
```json
{
  "user_chat_id": "chat-12345"
}
```

**Exemplo de uso com curl:**
```bash
curl -X POST http://localhost:8000/api/create-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "user_chat_id": "chat-12345"
  }'
```

**Resposta de sucesso:**
```json
{
  "status": "success",
  "message": "Ticket criado com sucesso",
  "ticket_id": 123,
  "external_id": "chat-12345",
  "user_chat_id": "chat-12345",
  "glpi_response": {
    "id": 123,
    "message": "Ticket criado com sucesso"
  }
}
```

### Adicionar Mensagem

**Endpoint:** `POST /api/add-message`

Adiciona mensagens da plataforma ao ticket do GLPI.

**Payload esperado (opção 1 - com external_id):**
```json
{
  "external_id": "CONV-12345",
  "message": "Mensagem do usuário",
  "user_name": "Nome do Usuário"
}
```

**Payload esperado (opção 2 - com ticket_id):**
```json
{
  "ticket_id": 20,
  "message": "Mensagem do usuário",
  "user_name": "Nome do Usuário"
}
```

**Nota**: Você pode usar `external_id` OU `ticket_id`. Se ambos forem fornecidos, `ticket_id` terá prioridade.

**Exemplo de uso com curl (external_id):**
```bash
curl -X POST http://localhost:8000/api/add-message \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "CONV-12345",
    "message": "Esta é uma mensagem de teste",
    "user_name": "João Silva"
  }'
```

**Exemplo de uso com curl (ticket_id):**
```bash
curl -X POST http://localhost:8000/api/add-message \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": 20,
    "message": "Esta é uma mensagem de teste",
    "user_name": "João Silva"
  }'
```

**Resposta de sucesso:**
```json
{
  "status": "success",
  "message": "Mensagem adicionada ao ticket com sucesso",
  "ticket_id": 20,
  "external_id": "CONV-12345",
  "followup_id": 28
}
```

**Erros possíveis:**
- `400`: external_id/ticket_id ou message não fornecidos
- `404`: Ticket não encontrado com o external_id ou ticket_id fornecido
- `500`: Erro ao conectar ao GLPI ou adicionar mensagem

### Buscar Histórico de Tickets (POST)

**Endpoint:** `POST /api/ticket-history`

Busca o histórico completo de tickets do GLPI com filtros.

**Payload esperado (opcional):**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "status_filter": 5,
  "entity_id": 0,
  "include_logs": true,
  "include_followups": true,
  "include_solutions": true,
  "max_tickets": 100
}
```

**Formato de datas:** As datas devem ser especificadas no formato `YYYY-MM-DD` (apenas data).

**Exemplo de uso com curl:**
```bash
curl -X POST http://localhost:8000/api/ticket-history \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "max_tickets": 50
  }'
```

**Resposta de sucesso:**
```json
{
  "status": "success",
  "message": "Histórico de tickets obtido com sucesso",
  "summary": {
    "total_tickets": 10,
    "total_logs": 50,
    "total_followups": 30,
    "total_solutions": 8,
    "filters_applied": {
      "start_date": "2025-01-01",
      "max_tickets": 50
    }
  },
  "tickets": [
    // Array com dados dos tickets
  ]
}
```

### Buscar Histórico de Tickets (GET)

**Endpoint:** `GET /api/ticket-history`

Busca o histórico completo de tickets do GLPI com parâmetros de query.

**Parâmetros de query:**
- `start_date`: Data inicial no formato YYYY-MM-DD (opcional)
- `end_date`: Data final no formato YYYY-MM-DD (opcional)
- `status_filter`: Filtro de status (opcional)
- `entity_id`: ID da entidade (opcional)
- `include_logs`: Incluir logs de auditoria (default: true)
- `include_followups`: Incluir followups (default: true)
- `include_solutions`: Incluir soluções (default: true)
- `max_tickets`: Número máximo de tickets (default: 100)

**Exemplo de uso com curl:**
```bash
curl -X GET "http://localhost:8000/api/ticket-history?start_date=2025-01-01&max_tickets=50"
```

## Webhooks do GLPI

### Followup Adicionado

**Endpoint:** `POST /webhook/followup-added`

Recebe notificações quando um consultor GLPI adiciona uma resposta ao ticket.

**Payload esperado do GLPI:**
```json
{
  "item": {
    "id": 123,
    "items_id": 456,
    "content": "Olá! Vou ajudá-lo com esse problema...",
    "users_id": 5,
    "date_creation": "2025-10-06 10:30:00",
    "is_private": 0
  }
}
```

**Configuração no GLPI:**
- **Evento**: `ITILFollowup` → `Add`
- **URL**: `http://host.docker.internal:8000/webhook/followup-added`

### Ticket Fechado

**Endpoint:** `POST /webhook/ticket-closed`

Recebe notificações quando um ticket é fechado (status 6) ou solucionado (status 5) no GLPI.

**Configuração no GLPI:**
- **Evento**: `Ticket` → `Update` (quando status = 6)
- **URL**: `http://host.docker.internal:8000/webhook/ticket-closed`

### Debug

**Endpoint:** `POST /webhook/debug`

Endpoint de debug para capturar exatamente o que está sendo enviado pelo GLPI.

## Endpoints de Verificação

### Health Check

**Endpoint:** `GET /health`

Verifica se o serviço está ativo.

**Exemplo de uso com curl:**
```bash
curl -X GET http://localhost:8000/health
```

**Resposta:**
```json
{
  "status": "healthy",
  "service": "GLPI Ticket Webhook"
}
```
