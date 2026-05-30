import socket
import hashlib

HOST = 'localhost'
PORT = 8001
JANELA_INICIAL = 5

# chave usada pra decriptar — tem que ser igual a do cliente
CHAVE = "chave123"

# checksum de 16 bits estilo complemento de 1
# mesma logica do cliente — recalcula e compara pra verificar integridade
def calcular_checksum(msg: str) -> str:
    dados = msg.encode()
    if len(dados) % 2 != 0:
        dados += b'\x00'
    soma = 0
    for i in range(0, len(dados), 2):
        palavra = (dados[i] << 8) + dados[i + 1]
        soma += palavra
        soma = (soma & 0xFFFF) + (soma >> 16)
    return format(~soma & 0xFFFF, '04x')

# XOR com a chave — mesma operacao do encriptar, aplicar duas vezes volta ao original
def decriptar(texto):
    return ''.join(chr(ord(c) ^ ord(CHAVE[i % len(CHAVE)])) for i, c in enumerate(texto))

def processar_pacote(dados, esperado, modo, buffer_sr):
    partes = dados.split('|', 2)
    if len(partes) != 3:
        print("  [!] Pacote malformado.")
        return None, False

    seq_str, cs_recebido, payload_cripto = partes
    seq = int(seq_str)

    # decripta antes de verificar o checksum — cliente calculou o checksum sobre o original
    payload = decriptar(payload_cripto)
    cs_calc = calcular_checksum(payload)
    ok = cs_recebido == cs_calc

    print(f"  [PKT] seq={seq} payload='{payload}' cs={'OK' if ok else 'ERRO'} esperado={esperado}")

    if not ok:
        return seq, False  # checksum errado -> NACK

    if modo == 'go-back-n':
        if seq == esperado:
            return seq, True  # em ordem e integro -> ACK
        # fora de ordem no GBN: descarta sem mandar NACK
        # o cliente vai reenviar por timeout ou pelo NACK do pacote anterior
        return seq, None

    else:
        buffer_sr[seq] = payload  # SR aceita fora de ordem, guarda no buffer ja decriptado
        return seq, True

def iniciar_servidor():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"[*] Servidor em {HOST}:{PORT}\n")

    while True:
        conn, addr = srv.accept()
        print(f"[+] Conexao de {addr}")

        # handshake: servidor define a janela, recebe limite de chars e modo do cliente
        janela_str = input(f"Tamanho da janela para {addr} (1-5, Enter=5): ").strip()
        janela = int(janela_str) if janela_str.isdigit() and 1 <= int(janela_str) <= 5 else JANELA_INICIAL
        conn.send(str(janela).encode())

        max_chars = int(conn.recv(1024).decode())
        conn.send(b"OK")
        print(f"[*] Limite de caracteres: {max_chars}")

        modo = conn.recv(1024).decode()
        print(f"[*] Modo: {modo} | Janela: {janela}\n")

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

                            if pkt == "RESET":
                                # cliente desistiu por excesso de erros
                                print("  [!] Cliente abortou a transmissao por excesso de erros. Resetando buffer.")
                                recebidos.clear()
                                break

                            if '|' not in pkt:
                                print(f"  [!] Pacote invalido ignorado: '{pkt}'")
                                continue

                            seq, ok = processar_pacote(pkt, esperado, modo, buffer_sr)

                            if ok is True:
                                if modo == 'go-back-n':
                                    # decripta de novo aqui pq o processar_pacote nao devolve o payload
                                    payload_original = pkt.split('|', 2)[2]
                                    recebidos[seq] = decriptar(payload_original)
                                    esperado = seq + 1
                                    conn.send(f"ACK|{seq}".encode())
                                else:
                                    # SR: payload ja foi decriptado e guardado no buffer_sr dentro do processar_pacote
                                    recebidos[seq] = buffer_sr.get(seq, '')
                                    conn.send(f"ACK|{seq}".encode())
                                    while esperado in recebidos:
                                        esperado += 1

                                if len(recebidos) == total:
                                    mensagem_final = ''.join(recebidos[i] for i in sorted(recebidos))
                                    print(f"\n[*] Mensagem completa: '{mensagem_final}'\n")

                            elif ok is None:
                                # GBN: fora de ordem — descarta sem responder nada
                                print(f"  [GBN] seq={seq} fora de ordem (esperado={esperado}), descartado.")

                            else:
                                # checksum invalido -> NACK
                                conn.send(f"NACK|{seq}".encode())

                        except socket.timeout:
                            print("  [!] Timeout aguardando pacote.")
                            break

                    mensagem_final = ''.join(recebidos[i] for i in sorted(recebidos))
                    print(f"\n[*] Mensagem completa: '{mensagem_final}'\n")

            except (ConnectionResetError, TimeoutError):
                # cliente desconectou ou conexao expirou — encerra esse loop
                break

        conn.close()
        print(f"[-] Conexao encerrada com {addr}\n")

if __name__ == "__main__":
    iniciar_servidor()