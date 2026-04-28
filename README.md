# 📡 RTPy — Reliable Transport in Python

## 📌 Sobre o Projeto

Implementação de uma aplicação **Cliente-Servidor** em Python utilizando sockets TCP. O projeto estabelece comunicação confiável com handshake inicial de configuração, verificação de integridade via checksum e suporte a dois modos de transporte: **Go-Back-N** e **Repetição Seletiva**.

> **Escopo atual:** canal de comunicação ideal — sem simulação de erros ou perdas de pacotes.

---

## 🚀 Funcionalidades Implementadas

### 🔹 Conexão via Socket TCP
- Cliente e servidor se conectam via `socket.AF_INET / SOCK_STREAM` (TCP)
- Servidor aguarda novas conexões em loop, podendo atender múltiplos clientes sequencialmente

### 🔹 Handshake Inicial
Ao estabelecer a conexão, cliente e servidor trocam as seguintes informações antes de qualquer envio de dados:

| Campo | Descrição |
|---|---|
| `tamanho_maximo` | Tamanho máximo permitido para mensagens (em caracteres) |
| `modo_operacao` | Modo de transporte escolhido (`1` = Go-Back-N, `2` = Repetição Seletiva) |

### 🔹 Verificação de Integridade (Checksum)
- Cada pacote enviado inclui um **checksum de 16 bits** calculado sobre a mensagem (soma com complemento de 1, estilo TCP/UDP)
- O servidor recalcula o checksum ao receber o pacote e compara com o valor recebido
- Garante detecção de corrupção nos dados

### 🔹 Formato dos Pacotes
```
<sequencia>|<checksum>|<mensagem>
```
Exemplo: `1|a3f2|Olá, servidor!`

### 🔹 Respostas do Servidor (ACK / NACK)

| Resposta | Quando é enviada |
|---|---|
| `ACK\|N` | Pacote N recebido e íntegro |
| `NACK\|N` | Checksum incorreto ou pacote malformado |

### 🔹 Modos de Operação

**Go-Back-N (`1`)**
- Envia uma mensagem por vez, digitada pelo usuário
- Aguarda ACK antes de encerrar

**Repetição Seletiva (`2`)**
- Envia N pacotes sequenciais (gerados automaticamente como `"Pacote 1"`, `"Pacote 2"`, ...)
- Aguarda ACK individualmente para cada pacote
- Valida o tamanho máximo antes de cada envio

---

## 📂 Estrutura do Projeto

```
.
├── Servidor.py   # Lógica do servidor: handshake, recebimento e validação de pacotes
├── Cliente.py    # Lógica do cliente: handshake, envio e modos de operação
└── README.md
```

---

## 🛠️ Como Executar

### Pré-requisitos
- Python 3.x instalado
- Nenhuma dependência externa necessária

### ▶️ Passo 1 — Iniciar o Servidor
```bash
python3 Servidor.py
```
O servidor ficará aguardando conexões em `localhost:12345`.

### ▶️ Passo 2 — Iniciar o Cliente
Em outro terminal:
```bash
python3 Cliente.py
```

### ▶️ Passo 3 — Handshake
O cliente solicitará dois dados antes de enviar qualquer mensagem:

```
Digite o tamanho máximo da mensagem em caracteres: 50

Escolha o modo de envio:
  1 - Go-Back-N
  2 - Repetição Seletiva
Opção: 1
```

### ▶️ Passo 4 — Envio de Mensagens

**Modo Go-Back-N:**
```
Digite a mensagem a ser enviada: Olá, mundo!
  [ENVIO] Pacote 1 enviado: 'Olá, mundo!'
  [SERVIDOR] ACK|1
[✓] Mensagem entregue com sucesso (canal confiável — ACK na 1ª tentativa).
```

**Modo Repetição Seletiva:**
```
Quantos pacotes deseja enviar? 3

[*] Enviando 3 pacote(s) — canal confiável, sem perdas/erros.

  [ENVIO] Pacote 1 enviado: 'Pacote 1'
  [SERVIDOR] ACK|1
  [✓] Pacote 1 confirmado.

  [ENVIO] Pacote 2 enviado: 'Pacote 2'
  [SERVIDOR] ACK|2
  [✓] Pacote 2 confirmado.
  ...
```

---

## 🔧 Configurações

| Parâmetro | Valor padrão | Onde alterar |
|---|---|---|
| Host | `localhost` | `HOST` em `Cliente.py` e `Servidor.py` |
| Porta | `12345` | `PORT` em `Cliente.py` e `Servidor.py` |
| Buffer de recepção | `1024` bytes | `recv(1024)` nas duas classes |

---

## 📋 Escopo e Limitações (Entrega 1 e 2)

- ✅ Canal confiável (TCP) — sem perdas ou corrupção simuladas
- ✅ Handshake com tamanho máximo e modo de operação
- ✅ Checksum para detecção de erros
- ✅ ACK/NACK por pacote