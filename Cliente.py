import socket
import re
import hashlib

HOST = 'localhost'
PORT = 8001
TIMEOUT = 2
PAYLOAD_MAX = 4

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

def fragmentar(texto):
    return [texto[i:i+PAYLOAD_MAX] for i in range(0, len(texto), PAYLOAD_MAX)]

def montar_pacote(seq, payload, corrompido=False):
    cs = "0000" if corrompido else calcular_checksum(payload)
    return f"{seq}|{cs}|{payload}"

MAX_RETRIES = 3

def enviar_com_janela(sock, fragmentos, janela, modo, pacotes_errar=set()):
    total = len(fragmentos)
    base = 0
    confirmados = set()   # seqs que receberam ACK
    pendentes = set()     # seqs enviados mas sem ACK ainda
    tentativas = {}
    reenviar = False

    while base < total:
        fim = min(base + janela, total)

        for seq in range(base, fim):
            if seq not in confirmados and seq not in pendentes:
                t = tentativas.get(seq, 0)
                corrompido = (seq in pacotes_errar) and (t == 0)
                pkt = montar_pacote(seq, fragmentos[seq], corrompido)
                sock.send(pkt.encode())
                pendentes.add(seq)
                tentativas[seq] = t + 1
                flag = " [CORROMPIDO]" if corrompido else f" (tentativa {t+1})" if t > 0 else ""
                print(f"  [ENVIO] seq={seq} payload='{fragmentos[seq]}'{flag}")

        if reenviar:
            reenviar = False
            continue

        try:
            sock.settimeout(TIMEOUT)
            raw = sock.recv(1024).decode()

            # TCP pode juntar multiplas respostas numa so leitura; separar antes de processar
            respostas = re.findall(r'N?ACK\|\d+', raw)
            if not respostas:
                respostas = [raw]

            for resposta in respostas:
                print(f"  [SERVIDOR] {resposta}")

                if resposta.startswith("ACK"):
                    ack_seq = int(resposta.split("|")[1])
                    confirmados.add(ack_seq)
                    pendentes.discard(ack_seq)
                    if modo == 'go-back-n':
                        base = ack_seq + 1
                    else:
                        # avanca base ate o primeiro nao confirmado
                        while base in confirmados:
                            base += 1

                elif resposta.startswith("NACK"):
                    nack_seq = int(resposta.split("|")[1])
                    t_atual = tentativas.get(nack_seq, 0)
                    print(f"  [!] NACK seq={nack_seq} (tentativa {t_atual}/{MAX_RETRIES})")

                    if t_atual >= MAX_RETRIES:
                        print(f"  [x] Pacote {nack_seq} falhou {MAX_RETRIES}x. Abortando.")
                        return

                    if modo == 'go-back-n':
                        # retrocede base e limpa pendentes a partir de nack_seq
                        pendentes = {s for s in pendentes if s < nack_seq}
                        base = nack_seq
                        reenviar = True
                        break  # descarta respostas posteriores neste recv
                    else:
                        # SR: marca para reenvio removendo dos pendentes
                        pendentes.discard(nack_seq)

        except socket.timeout:
            print(f"  [!] Timeout - reenviando a partir de {base}")
            pendentes.clear()

    print("[*] Todos os fragmentos entregues.")

def iniciar_cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print("[*] Conectado ao servidor.")

        # Handshake: recebe janela, define limite de chars, envia modo
        janela = int(sock.recv(1024).decode())
        print(f"[*] Janela recebida do servidor: {janela}")

        while True:
            try:
                max_chars = int(input("Limite maximo de caracteres por mensagem (min 30): ").strip())
                if max_chars >= 30:
                    break
                print("  [!] O limite deve ser de no minimo 30 caracteres.")
            except ValueError:
                print("  [!] Digite um numero valido.")
        sock.send(str(max_chars).encode())
        sock.recv(1024)  # OK do servidor

        print("Modo: 1-Go-Back-N  2-Repeticao Seletiva")
        modo_op = input("Opcao: ").strip()
        modo = 'go-back-n' if modo_op == '1' else 'selective-repeat'
        sock.send(modo.encode())

        while True:
            print("\n1-Enviar mensagem  2-Sair")
            op = input("Opcao: ").strip()
            if op == '2':
                break
            if op != '1':
                continue

            texto = input(f"Mensagem (max {max_chars} chars): ").strip()[:max_chars]
            fragmentos = fragmentar(texto)
            print(f"[*] {len(fragmentos)} fragmento(s) de ate {PAYLOAD_MAX} chars")

            print("Envio: 1-Lote (usa janela)  2-Isolado (um por vez)")
            envio_op = input("Opcao: ").strip()
            janela_envio = 1 if envio_op == '2' else janela

            errar = input("Simular erro em quais seqs? (ex: 1,3 ou Enter pra nenhum): ").strip()
            pacotes_errar = set(int(x) for x in errar.split(',') if x.strip().isdigit()) if errar else set()

            sock.send(str(len(fragmentos)).encode())
            sock.recv(1024)

            enviar_com_janela(sock, fragmentos, janela_envio, modo, pacotes_errar)

if __name__ == "__main__":
    iniciar_cliente()