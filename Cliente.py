import socket

HOST = 'localhost'
PORT = 8001
TIMEOUT = 2
PAYLOAD_MAX = 4
# Chave compartilhada para criptografia simétrica XOR
# deve ser igual no servidor para que a decriptação funcione
CHAVE = "chave123"

# Checksum: soma de verificação de 16 bits (sem bibliotecas externas)
# percorre os bytes da mensagem de 2 em 2, somando palavras de 16 bits
# ao final inverte os bits para gerar o valor de verificação
def calcular_checksum(mensagem: str) -> str:
    dados = mensagem.encode()
    if len(dados) % 2 != 0:
        dados += b'\x00'
    soma = 0
    for i in range(0, len(dados), 2):
        palavra = (dados[i] << 8) + dados[i + 1]
        soma += palavra
        soma = (soma & 0xFFFF) + (soma >> 16)
    return format(~soma & 0xFFFF, '04x')

# Criptografia simétrica XOR: cada caractere do payload é combinado
# com um caractere da chave usando XOR — aplicar duas vezes volta ao original
def encriptar(texto):
    return ''.join(chr(ord(c) ^ ord(CHAVE[i % len(CHAVE)])) for i, c in enumerate(texto))

# Fragmentação: quebra o texto em pedaços de até PAYLOAD_MAX (4) caracteres
def fragmentar(texto):
    return [texto[i:i+PAYLOAD_MAX] for i in range(0, len(texto), PAYLOAD_MAX)]

def montar_pacote(seq, payload, corrompido=False):
    # Checksum calculado sobre o payload original (antes de encriptar)
    cs = "0000" if corrompido else calcular_checksum(payload)
    # Payload encriptado antes de enviar pelo socket
    payload_cripto = encriptar(payload)
    return f"{seq}|{cs}|{payload_cripto}"

MAX_RETRIES = 3

def enviar_com_janela(sock, fragmentos, janela, modo, pacotes_errar=set()):
    total = len(fragmentos)
    base = 0
    enviados = {}
    tentativas = {}

    while base < total:
        fim = min(base + janela, total)

        for seq in range(base, fim):
            if seq not in enviados:
                t = tentativas.get(seq, 0)
                corrompido = (seq in pacotes_errar) and (t == 0)
                pkt = montar_pacote(seq, fragmentos[seq], corrompido)
                sock.send(pkt.encode())
                enviados[seq] = fragmentos[seq]
                tentativas[seq] = t + 1
                flag = " [CORROMPIDO]" if corrompido else f" (tentativa {t+1})" if t > 0 else ""
                print(f"  [ENVIO] seq={seq} payload='{fragmentos[seq]}'{flag}")

        try:
            sock.settimeout(TIMEOUT)
            resposta = sock.recv(1024).decode()
            print(f"  [SERVIDOR] {resposta}")

            if resposta.startswith("ACK"):
                ack_seq = int(resposta.split("|")[1])
                if modo == 'go-back-n':
                    base = ack_seq + 1
                else:
                    enviados.pop(ack_seq, None)
                    while base not in enviados and base < total:
                        base += 1

            elif resposta.startswith("NACK"):
                nack_seq = int(resposta.split("|")[1])
                t_atual = tentativas.get(nack_seq, 0)
                print(f"  [!] NACK seq={nack_seq} (tentativa {t_atual}/{MAX_RETRIES})")

                if t_atual >= MAX_RETRIES:
                    print(f"  [✗] Pacote {nack_seq} falhou {MAX_RETRIES}x. Abortando.")
                    return

                if modo == 'go-back-n':
                    for s in range(nack_seq, fim):
                        enviados.pop(s, None)
                    base = nack_seq
                else:
                    enviados.pop(nack_seq, None)

        except socket.timeout:
            print(f"  [!] Timeout — reenviando a partir de {base}")
            for s in range(base, fim):
                enviados.pop(s, None)

    print("[✓] Todos os fragmentos entregues.")

def iniciar_cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print("[*] Conectado ao servidor.")

        janela = int(sock.recv(1024).decode())
        print(f"[*] Janela recebida do servidor: {janela}")

        print("Modo: 1-Go-Back-N  2-Repetição Seletiva")
        modo_op = input("Opção: ").strip()
        modo = 'go-back-n' if modo_op == '1' else 'selective-repeat'
        sock.send(modo.encode())

        while True:
            print("\n1-Enviar mensagem  2-Sair")
            op = input("Opção: ").strip()
            if op == '2':
                break
            if op != '1':
                continue

            texto = input("Mensagem (max 30 chars): ").strip()[:30]
            fragmentos = fragmentar(texto)
            print(f"[*] {len(fragmentos)} fragmento(s) de até {PAYLOAD_MAX} chars")

            errar = input("Simular erro em quais seqs? (ex: 0,2 ou Enter pra nenhum): ").strip()
            pacotes_errar = set(int(x) for x in errar.split(',') if x.strip().isdigit()) if errar else set()

            sock.send(str(len(fragmentos)).encode())
            sock.recv(1024)

            enviar_com_janela(sock, fragmentos, janela, modo, pacotes_errar)

if __name__ == "__main__":
    iniciar_cliente()