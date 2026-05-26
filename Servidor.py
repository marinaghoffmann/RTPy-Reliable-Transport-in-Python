import socket

HOST = 'localhost'
PORT = 8001
JANELA_INICIAL = 5
# Chave compartilhada para criptografia simétrica XOR
# deve ser igual à do cliente para que a decriptação funcione
CHAVE = "chave123"

# Checksum: mesma lógica do cliente — recalcula e compara para verificar integridade
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

# Decriptação XOR: mesma função da encriptação — XOR aplicado duas vezes volta ao original
def decriptar(texto):
    return ''.join(chr(ord(c) ^ ord(CHAVE[i % len(CHAVE)])) for i, c in enumerate(texto))

def processar_pacote(dados, esperado, modo, buffer_sr):
    partes = dados.split('|', 2)
    if len(partes) != 3:
        print("  [!] Pacote malformado.")
        return None, False

    seq_str, cs_recebido, payload_cripto = partes
    seq = int(seq_str)
    # Decripta o payload antes de verificar o checksum
    payload = decriptar(payload_cripto)
    cs_calc = calcular_checksum(payload)
    ok = cs_recebido == cs_calc

    print(f"  [PKT] seq={seq} payload='{payload}' cs={'OK' if ok else 'ERRO'} esperado={esperado}")

    if not ok:
        return seq, False

    if modo == 'go-back-n':
        if seq == esperado:
            return seq, True
        return seq, False

    else:
        buffer_sr[seq] = payload
        return seq, True

def iniciar_servidor():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"[*] Servidor em {HOST}:{PORT}\n")

    while True:
        conn, addr = srv.accept()
        print(f"[+] Conexão de {addr}")

        conn.send(str(JANELA_INICIAL).encode())
        modo = conn.recv(1024).decode()
        print(f"[*] Modo: {modo} | Janela: {JANELA_INICIAL}\n")

        while True:
            try:
                raw = conn.recv(1024).decode()
                if not raw:
                    break

                if raw.isdigit():
                    total = int(raw)
                    conn.send(b"OK")
                    print(f"[*] Esperando {total} fragmento(s)...")

                    recebidos = {}
                    buffer_sr = {}
                    esperado = 0

                    while esperado < total or len(recebidos) < total:
                        try:
                            conn.settimeout(5)
                            pkt = conn.recv(1024).decode()
                            if not pkt:
                                break

                            seq, ok = processar_pacote(pkt, esperado, modo, buffer_sr)

                            if ok:
                                if modo == 'go-back-n':
                                    recebidos[seq] = pkt.split('|', 2)[2]
                                    recebidos[seq] = decriptar(recebidos[seq])
                                    esperado = seq + 1
                                    conn.send(f"ACK|{seq}".encode())
                                else:
                                    recebidos[seq] = buffer_sr.get(seq, '')
                                    conn.send(f"ACK|{seq}".encode())
                                    while esperado in recebidos:
                                        esperado += 1

                                if len(recebidos) == total:
                                    break
                            else:
                                conn.send(f"NACK|{seq}".encode())

                        except socket.timeout:
                            print("  [!] Timeout aguardando pacote.")
                            break

                    mensagem_final = ''.join(recebidos[i] for i in sorted(recebidos))
                    print(f"\n[✓] Mensagem completa: '{mensagem_final}'\n")

            except ConnectionResetError:
                break

        conn.close()
        print(f"[-] Conexão encerrada com {addr}\n")

if __name__ == "__main__":
    iniciar_servidor()