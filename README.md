# GLPI Ticket Webhook

Este projeto fornece um webhook para receber notificações de tickets fechados no GLPI.

## Estrutura do Projeto

- `handler.py`: Cliente para interagir com a API do GLPI
- `ticket_webhook.py`: Servidor FastAPI para receber webhooks
- `requirements.txt`: Dependências do projeto
- `.env`: Configurações de ambiente

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

Certifique-se de que o arquivo `.env` contém as configurações necessárias:

```
USER_TOKEN=seu_token_de_usuario
GLPI_BASE_URL=http://localhost:8080/apirest.php
APP_TOKEN=seu_token_de_aplicacao
```

## Executando o Webhook

Para iniciar o servidor de webhook:

```bash
uvicorn ticket_webhook:app --host 0.0.0.0 --port 8000 --reload
```

O servidor estará disponível em `http://localhost:8000`

## Endpoints Disponíveis

### POST /webhook/ticket-closed

Endpoint para receber notificações quando um ticket é fechado.

**Exemplo de payload:**

```json
{
  "ticket_id": 123,
  "ticket_name": "Problema com acesso ao sistema",
  "closed_by": "Suporte Técnico",
  "closed_at": "2023-10-02T10:30:00Z",
  "solution": "Reset de senha realizado com sucesso",
  "requester_email": "cliente@empresa.com",
  "requester_name": "Cliente Exemplo",
  "additional_data": {
    "priority": "alta",
    "category": "Acesso"
  }
}
```

### POST /webhook/ticket-updated

Endpoint genérico para receber notificações de atualização de tickets.

### GET /health

Endpoint de health check.

## Integração com GLPI

Para configurar o webhook no GLPI, você pode usar:

1. **Notificações do GLPI**: Configure notificações no GLPI para enviar requisições HTTP para o endpoint do webhook.
2. **Plugins de webhook**: Use plugins como o "Webhook" para GLPI.
3. **Scripts personalizados**: Crie scripts que chamem o webhook quando tickets forem fechados.

## Exemplo de Uso

```python
import requests

# Enviando notificação de ticket fechado
payload = {
  "ticket_id": 123,
  "ticket_name": "Problema com acesso ao sistema",
  "closed_by": "Suporte Técnico",
  "closed_at": "2023-10-02T10:30:00Z",
  "solution": "Reset de senha realizado com sucesso",
  "requester_email": "cliente@empresa.com",
  "requester_name": "Cliente Exemplo"
}

response = requests.post("http://localhost:8000/webhook/ticket-closed", json=payload)
print(response.json())
```
