# GLPI Serverless API

Este projeto implementa uma API serverless para integração com o GLPI, utilizando AWS Lambda e o framework Serverless.

## Estrutura do Projeto

- `main.py`: Ponto de entrada principal para as funções Lambda
- `glpi_helper.py`: Classe auxiliar para interação com a API do GLPI
- `serverless.yml`: Configuração do framework Serverless para implantação na AWS

## Requisitos

- Node.js (para o framework Serverless)
- Python 3.12
- Conta AWS configurada
- Credenciais do GLPI (URL, tokens)
- Credenciais do Supabase (se necessário)

## Instalação

1. Instale o Serverless Framework globalmente:
   ```bash
   npm install -g serverless
   ```

2. Instale os plugins necessários:
   ```bash
   npm install serverless-python-requirements serverless-dotenv-plugin
   ```

3. Configure as variáveis de ambiente criando um arquivo `.env` baseado no `.env.example`:
   ```bash
   cp .env.example .env
   # Edite o arquivo .env com suas credenciais
   ```

## Deploy

Para implantar a aplicação na AWS:

```bash
# Deploy para ambiente de desenvolvimento
serverless deploy -s dev

# Deploy para ambiente de produção
serverless deploy -s prod

# Deploy de uma função específica
serverless deploy function -f main -s dev
```

## Endpoints

Após o deploy, os seguintes endpoints estarão disponíveis:

- `GET /health` - Verificação de saúde do serviço
- `POST /process` - Processamento genérico de dados
- `POST /glpi/ticket` - Criação/atualização de tickets no GLPI
- `POST /api/create-ticket` - Cria um novo ticket no GLPI
- `POST /webhook/ticket-closed` - Recebe notificações quando um ticket é fechado/solucionado
- `POST /webhook/followup-added` - Recebe notificações quando um consultor adiciona uma resposta ao ticket
- `POST /api/add-message` - Adiciona mensagens da plataforma ao ticket do GLPI
- `POST /api/ticket-history` - Busca o histórico completo de tickets (POST)
- `GET /api/ticket-history` - Busca o histórico completo de tickets (GET)

## Uso

### Criar um ticket no GLPI

```bash
curl -X POST https://seu-endpoint.amazonaws.com/dev/glpi/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ticket de exemplo",
    "content": "Descrição do problema",
    "entities_id": 0
  }'
```

### Atualizar um ticket no GLPI

```bash
curl -X POST https://seu-endpoint.amazonaws.com/dev/glpi/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": 123,
    "content": "Descrição atualizada do problema"
  }'
```

### Verificar saúde do serviço

```bash
curl https://seu-endpoint.amazonaws.com/dev/health
```

### Criar um ticket via API

```bash
curl -X POST https://seu-endpoint.amazonaws.com/dev/api/create-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "user_chat_id": "chat-12345"
  }'
```

**Parâmetros aceitos:**
- `user_chat_id` (obrigatório): ID do chat na plataforma que será usado para carregar o histórico de conversa e título

O método carrega automaticamente o histórico de conversa do Supabase baseado no `user_chat_id` e o inclui no conteúdo do ticket.

### Notificar fechamento de ticket

```bash
curl -X POST https://seu-endpoint.amazonaws.com/dev/webhook/ticket-closed \
  -H "Content-Type: application/json" \
  -d '{
    "item": {
      "id": 123,
      "status": {"id": 6}
    }
  }'
```

### Notificar adição de followup

```bash
curl -X POST https://seu-endpoint.amazonaws.com/dev/webhook/followup-added \
  -H "Content-Type: application/json" \
  -d '{
    "item": {
      "id": 456,
      "items_id": 123,
      "content": "Resposta do consultor"
    }
  }'
```

### Adicionar mensagem ao ticket

```bash
curl -X POST https://seu-endpoint.amazonaws.com/dev/api/add-message \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "CONV-12345",
    "message": "Mensagem do usuário",
    "user_name": "Nome do Usuário"
  }'
```

**Parâmetros aceitos:**
- `external_id` (obrigatório, se não fornecer `ticket_id`): ID externo do ticket na plataforma
- `ticket_id` (obrigatório, se não fornecer `external_id`): ID do ticket no GLPI
- `message` (obrigatório): Conteúdo da mensagem a ser adicionada ao ticket
- `user_name` (opcional): Nome do usuário que enviou a mensagem (padrão: "Usuário")

A mensagem será adicionada como um followup público ao ticket identificado pelo `external_id` ou `ticket_id`.

### Buscar histórico de tickets (POST)

```bash
curl -X POST https://seu-endpoint.amazonaws.com/dev/api/ticket-history \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "max_tickets": 50
  }'
```

### Buscar histórico de tickets (GET)

```bash
curl "https://seu-endpoint.amazonaws.com/dev/api/ticket-history?start_date=2025-01-01&max_tickets=50"
```

## Logs

Para visualizar os logs das funções:

```bash
# Logs da função principal em tempo real
serverless logs -f main -s dev -t
```

## Remoção

Para remover a aplicação da AWS:

```bash
serverless remove -s dev
```
