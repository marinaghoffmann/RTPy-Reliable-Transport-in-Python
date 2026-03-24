# 📡 Entrega 1: Comunicação Cliente-Servidor via Socket

## 📌 Sobre o Projeto
Este projeto consiste na implementação de uma aplicação Cliente-Servidor utilizando a biblioteca `socket` do Python. O objetivo desta primeira etapa é estabelecer a comunicação básica, realizar um handshake inicial de configuração e garantir a integridade dos dados trafegados através da verificação de checksum.

---

## 🚀 Funcionalidades Implementadas (Escopo 1)

### 🔹 Handshake Inicial
Assim que a conexão é estabelecida:
- O **Servidor** informa ao **Cliente** o tamanho máximo permitido para as mensagens (**1024 bytes**).
- O **Cliente** informa o modo de operação escolhido:
  - **Único**
  - **Rajada**

---

### 🔹 Validação de Integridade (Checksum)
- Cada pacote enviado contém um **hash MD5** da mensagem.
- O **Servidor** recalcula esse hash ao receber os dados.
- Isso garante que não houve corrupção durante o transporte.

---

### 🔹 Respostas do Servidor (ACK/NACK)
- **ACK** → Enviado quando o pacote chega intacto.
- **NACK** → Enviado quando:
  - O checksum não confere
  - O pacote está malformado

---

### 🔹 Simulação de Corrupção
- O **Cliente**, no modo **rajada**, possui uma função para:
  - Forçar o envio de um pacote com checksum incorreto
- Isso permite testar a resposta do servidor (**NACK**)

---

## 🛠️ Como Executar

### Pré-requisitos
- Python 3.x instalado

### ▶️ Passo 1: Iniciar o Servidor
```bash
python servidor.py
### ▶️ Passo 2: Iniciar o Cliente
Em outro terminal, execute:

```bash
python cliente.py
```

### ▶️ Passo 3: Escolher o modo de operação
Ao iniciar, o cliente solicitará que você escolha o modo de envio:

- `1` → **Modo Único** (envia uma mensagem por vez)
- `2` → **Modo Rajada** (envia múltiplas mensagens em sequência)

### ▶️ Passo 4: Enviar mensagens
- Digite a mensagem que deseja enviar
- O cliente calculará o **checksum (MD5)** automaticamente
- O servidor responderá com:
  - `ACK` → mensagem recebida corretamente
  - `NACK` → erro na integridade ou formato

---

## 🧪 Testando a Simulação de Erro
No modo **rajada**, o cliente pode enviar propositalmente um pacote com erro:

- Isso simula corrupção de dados
- O servidor deverá responder com `NACK`

---

## 📂 Estrutura do Projeto
```
.
├── servidor.py
├── cliente.py
└── README.md
```
