# Fluxo de Integração Plataforma ↔ GLPI

## Visão Geral do Fluxo

```
PLATAFORMA → GLPI → CONSULTOR → GLPI → PLATAFORMA
```

## Fluxo Detalhado

### 1. Usuário envia pergunta na Plataforma

**Ação**: Usuário faz uma pergunta na sua plataforma

**O que fazer**: Criar um ticket no GLPI com `external_id`

```python
import requests

# Dados da conversa na plataforma
conversation_id = "CONV-12345"  # ID da conversa na sua plataforma
user_message = "Estou com problema no sistema"

# Cria ticket no GLPI
ticket_data = {
    'name': 'Atendimento via Plataforma',
    'content': user_message,
    'entities_id': 0,
    'externalid': conversation_id,  # ← ID da conversa na plataforma
    'type': 1,  # Incidente
    'urgency': 3,
    'requesttypes_id': 2  # E-mail ou outro tipo
}

# Envia para GLPI
response = requests.post(
    f"{GLPI_BASE_URL}/Ticket",
    headers={
        'Content-Type': 'application/json',
        'Session-Token': session_token,
        'App-Token': app_token
    },
    json={'input': ticket_data}
)

glpi_ticket_id = response.json()['id']
```

### 2. Consultor responde no GLPI

**Ação**: Consultor adiciona uma resposta (followup) no ticket

**Evento no GLPI**: `ITILFollowup` é criado

**Webhook acionado**: `POST /webhook/followup-added`

### 3. Webhook captura a resposta e envia para a Plataforma

**Payload recebido do GLPI**:
```json
{
  "item": {
    "id": 123,
    "items_id": 456,  // ID do ticket
    "content": "Olá! Vou ajudá-lo com esse problema...",
    "users_id": 5,
    "date_creation": "2025-10-06 10:30:00",
    "is_private": 0
  }
}
```

**O que o webhook faz**:
1. Extrai o `items_id` (ID do ticket)
2. Busca o ticket no GLPI para obter o `externalid`
3. Envia a resposta de volta para a plataforma usando o `externalid`

## Configuração dos Webhooks no GLPI

### Webhook 1: Quando followup é adicionado (PRINCIPAL)

**Endpoint**: `http://host.docker.internal:8000/webhook/followup-added`

**Evento**: `ITILFollowup` → `Add`

**Uso**: Capturar respostas do consultor e enviar para a plataforma

### Webhook 2: Quando ticket é fechado (OPCIONAL)

**Endpoint**: `http://host.docker.internal:8000/webhook/ticket-closed`

**Evento**: `Ticket` → `Update` (quando status = 6)

**Uso**: Notificar a plataforma que o ticket foi fechado

## Implementação na sua Plataforma

### Função para enviar resposta de volta

Edite a função `send_response_to_platform` no arquivo `ticket_webhook.py`:

```python
def send_response_to_platform(response_data: dict):
    """
    Envia a resposta do consultor de volta para a plataforma.
    """
    external_id = response_data.get('external_id')
    content = response_data.get('content')
    user_name = response_data.get('user_name')
    
    if not external_id:
        logger.warning("Ticket não possui external_id")
        return
    
    # URL da API da sua plataforma
    platform_api_url = "https://sua-plataforma.com/api/conversations/{}/messages".format(external_id)
    
    # Payload para sua plataforma
    payload = {
        "conversation_id": external_id,
        "message": content,
        "sender_name": user_name,
        "sender_type": "agent",
        "source": "glpi"
    }
    
    # Envia para a plataforma
    try:
        response = requests.post(
            platform_api_url,
            json=payload,
            headers={'Authorization': 'Bearer SEU_TOKEN_DA_PLATAFORMA'}
        )
        
        if response.status_code == 200:
            logger.info(f"Resposta enviada com sucesso para a plataforma")
        else:
            logger.error(f"Falha ao enviar resposta: {response.status_code}")
    except Exception as e:
        logger.error(f"Erro ao enviar para plataforma: {str(e)}")
```

## Configurando Webhooks no GLPI

### Opção 1: Usando Plugin Webhook

1. Instale o plugin "Webhook" no GLPI
2. Configure os webhooks:
   - **Nome**: Followup Adicionado
   - **URL**: `http://host.docker.internal:8000/webhook/followup-added`
   - **Evento**: `ITILFollowup` → `Add`
   - **Ativo**: Sim

### Opção 2: Usando Notificações do GLPI

Configure notificações para enviar requisições HTTP quando eventos ocorrerem.

### Opção 3: Usando Hook Personalizado (PHP)

Crie um arquivo `hook.php` no diretório do plugin:

```php
<?php

function plugin_webhook_item_add_itilfollowup($item) {
    // URL do webhook
    $webhook_url = 'http://host.docker.internal:8000/webhook/followup-added';
    
    // Prepara o payload
    $payload = [
        'item' => $item->fields
    ];
    
    // Envia para o webhook
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => $webhook_url,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 5
    ]);
    
    curl_exec($ch);
    curl_close($ch);
}

?>
```

## Fluxo Completo de Dados

### 1. Criação do Ticket

```
Plataforma (CONV-12345)
    ↓
    [API POST] Cria ticket com externalid='CONV-12345'
    ↓
GLPI (Ticket #456 criado)
```

### 2. Resposta do Consultor

```
GLPI (Consultor adiciona followup no Ticket #456)
    ↓
    [Webhook POST] /webhook/followup-added
    ↓
Webhook busca ticket #456 → encontra externalid='CONV-12345'
    ↓
    [API POST] Envia resposta para Plataforma usando CONV-12345
    ↓
Plataforma (Usuário recebe resposta na conversa CONV-12345)
```

## Testando o Fluxo

### 1. Teste de criação de ticket

```bash
python create_ticket_with_external_id.py
```

### 2. Teste de recebimento de followup

```bash
# Simula um followup do GLPI
curl -X POST http://localhost:8000/webhook/followup-added \
  -H "Content-Type: application/json" \
  -d '{
    "item": {
      "id": 1,
      "items_id": 456,
      "content": "Olá! Vou ajudá-lo com esse problema.",
      "users_id": 5,
      "date_creation": "2025-10-06 10:30:00",
      "is_private": 0
    }
  }'
```

## Próximos Passos

1. **Configure o webhook no GLPI** para o evento `ITILFollowup` → `Add`
2. **Implemente a função `send_response_to_platform`** com a API da sua plataforma
3. **Teste o fluxo completo**:
   - Crie um ticket via API com `externalid`
   - Adicione uma resposta no GLPI
   - Verifique se a resposta chegou na sua plataforma
4. **Adicione tratamento de erros** e retry logic se necessário
