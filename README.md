RTPy - Reliable Transport in Python
Aplicacao cliente-servidor que implementa transporte confiavel de dados na camada de aplicacao, sobre um canal com perdas e erros simulados.

Estrutura do projeto
.
├── Servidor.py
├── Cliente.py
└── README.md

Protocolo de aplicacao
Cada pacote trocado entre cliente e servidor segue o formato:
<seq>|<checksum>|<payload_encriptado>

seq: numero de sequencia inteiro (0, 1, 2, ...)
checksum: 4 digitos hexadecimais calculados sobre o payload original (antes da criptografia), pelo algoritmo de complemento de 1
payload_encriptado: ate 4 caracteres de conteudo util, encriptados com XOR antes do envio

Respostas do servidor:

ACK|<seq> — pacote recebido, integro e em ordem
NACK|<seq> — pacote com erro de checksum (corrupcao)

Handshake inicial
Ao conectar, a seguinte sequencia ocorre antes de qualquer troca de mensagens:

Servidor envia o tamanho da janela (1 a 5)
Cliente envia o limite maximo de caracteres por mensagem (minimo 30)
Servidor confirma com OK
Cliente envia o modo de operacao: go-back-n ou selective-repeat


Como executar
Pre-requisitos

Python 3.x (sem dependencias externas)

Passo 1 — Iniciar o servidor
bashpython3 Servidor.py
Ao receber uma conexao, o servidor solicitara o tamanho da janela no terminal (1 a 5). Pressionar Enter usa o valor padrao 5.
Passo 2 — Iniciar o cliente
Em outro terminal:
bashpython3 Cliente.py
Passo 3 — Handshake
O cliente exibira a janela recebida e pedira:

Limite maximo de caracteres por mensagem (minimo 30)
Modo de operacao: 1 para Go-Back-N, 2 para Repeticao Seletiva

Passo 4 — Enviar mensagens
O menu principal oferece:

1 Enviar mensagem
2 Sair

Ao escolher enviar, o cliente pedira:

O texto da mensagem (truncado no limite definido no handshake)
Tipo de envio: 1 Lote (usa a janela completa) ou 2 Isolado (um fragmento por vez)
Sequencias a corromper intencionalmente (ex: 0,2 ou Enter para nenhum)
Sequencias a perder intencionalmente (ex: 1,3 ou Enter para nenhum)


Funcionalidades implementadas
Checksum (complemento de 1)
Calculado manualmente sobre os bytes do payload original, agrupados em palavras de 16 bits com carry circular. O resultado e um valor hexadecimal de 4 digitos. O servidor recalcula o checksum sobre o payload ja decriptado e rejeita com NACK caso nao confira.
Criptografia simetrica XOR
Antes de cada envio, o payload e encriptado caractere a caractere com XOR usando uma chave compartilhada (CHAVE = "chave123"). O servidor aplica a mesma operacao para decriptar — XOR e sua propria inversa. O checksum e sempre calculado sobre o payload original, garantindo que corrupcao em transito seja detectada mesmo com criptografia ativa.
Numero de sequencia
Cada fragmento carrega um numero de sequencia inteiro crescente a partir de 0.
Temporizador
O cliente aguarda resposta por TIMEOUT = 2 segundos. Em caso de timeout, os pacotes pendentes da janela atual sao reenviados.
ACK e NACK
O servidor confirma individualmente cada pacote aceito (ACK) ou sinaliza erro de checksum (NACK). Pacotes fora de ordem no modo Go-Back-N sao descartados silenciosamente, sem NACK.
Janela e paralelismo
O tamanho da janela e determinado pelo servidor no handshake, variando de 1 a 5. O cliente pode ainda escolher envio em lote (respeita a janela) ou isolado (janela forcada para 1).
Go-Back-N (GBN)
Em caso de NACK, o cliente retrocede a base da janela ate o pacote com erro e reenvia todos os subsequentes. Pacotes que chegam fora de ordem sao descartados silenciosamente pelo servidor — sem NACK — e o remetente os reenvia por timeout ou por NACK do pacote anterior.
Repeticao Seletiva (SR)
Em caso de NACK, apenas o pacote com erro e reenviado. O servidor aceita pacotes fora de ordem, armazena em buffer e reordena ao montar a mensagem final.
Simulacao de corrupcao
O cliente aceita uma lista de numeros de sequencia a corromper. O checksum desses pacotes e substituido por 0000 na primeira tentativa, forcando um NACK do servidor. Nas retransmissoes o pacote e enviado corretamente.
Simulacao de perda
O cliente aceita uma lista de numeros de sequencia a perder. Esses pacotes simplesmente nao sao transmitidos na primeira tentativa, simulando perda real de pacote em rede. A recuperacao ocorre por timeout.
Limite de retransmissao
Apos MAX_RETRIES = 3 tentativas falhas no mesmo pacote, o cliente aborta o envio.

Uso de IA
Claude (Anthropic) foi utilizado como auxilio na revisao e implementacao do projeto, incluindo: substituicao do checksum MD5 pelo algoritmo de complemento de 1, correcao do comportamento do Go-Back-N para descarte silencioso de pacotes fora de ordem, implementacao da simulacao de perda de pacotes, correcao do rollback de janela no GBN, resolucao de problema de batching de pacotes TCP, e integracao da criptografia XOR.