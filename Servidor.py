import socket
import hashlib

HOST = 'localhost'
PORT = 8001
JANELA_INICIAL = 5

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

def processar_pacote(dados, esperado, modo, buffer_sr):
    partes = dados.split('|', 2)
    if len(partes) != 3:
        print("  [!] Pacote malformado.")
        return None, False

    seq_str, cs_recebido, payload = partes
    seq = int(seq_str)
    cs_calc = calcular_checksum(payload)
    ok = cs_recebido == cs_calc

    print(f"  [PKT] seq={seq} payload='{payload}' cs={'OK' if ok else 'ERRO'} esperado={esperado}")

    if not ok:
        return seq, False  # checksum invalido -> NACK

    if modo == 'go-back-n':
        if seq == esperado:
            return seq, True   # em ordem e valido -> ACK
        # fora de ordem no GBN: descarta silenciosamente (sem NACK)
        return seq, None

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
        print(f"[+] Conexao de {addr}")

        # Handshake: envia janela, recebe max_chars, recebe modo
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
                                print("  [!] Cliente abortou a transmissão por excesso de erros. Resetando buffer.")
                                recebidos.clear()
                                break

                            if '|' not in pkt:
                                print(f"  [!] Pacote inválido ignorado: '{pkt}'")
                                continue

                            seq, ok = processar_pacote(pkt, esperado, modo, buffer_sr)

                            if ok is True:
                                if modo == 'go-back-n':
                                    recebidos[seq] = pkt.split('|', 2)[2]
                                    esperado = seq + 1
                                    conn.send(f"ACK|{seq}".encode())
                                else:
                                    recebidos[seq] = buffer_sr.get(seq, '')
                                    conn.send(f"ACK|{seq}".encode())
                                    while esperado in recebidos:
                                        esperado += 1

                                if len(recebidos) == total:
                                    mensagem_final = ''.join(recebidos[i] for i in sorted(recebidos))
                                    print(f"\n[*] Mensagem completa: '{mensagem_final}'\n")

                            elif ok is None:
                                # GBN: pacote fora de ordem — descarta silenciosamente
                                print(f"  [GBN] seq={seq} fora de ordem (esperado={esperado}), descartado.")

                            else:
                                # checksum invalido -> NACK (corrupcao)
                                conn.send(f"NACK|{seq}".encode())

                        except socket.timeout:
                            print("  [!] Timeout aguardando pacote.")
                            break

                    mensagem_final = ''.join(recebidos[i] for i in sorted(recebidos))
                    print(f"\n[*] Mensagem completa: '{mensagem_final}'\n")

            except ConnectionResetError:
                break

        conn.close()
        print(f"[-] Conexao encerrada com {addr}\n")

if __name__ == "__main__":
    iniciar_servidor()