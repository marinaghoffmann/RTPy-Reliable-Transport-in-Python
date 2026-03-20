import socket
import hashlib

HOST = 'localhost'
PORT = 12345

def calcular_checksum(mensagem):
    return hashlib.md5(mensagem.encode()).hexdigest()

def enviar_pacote(socket_cliente, sequencia, mensagem, corromper=False):
    checksum = calcular_checksum(mensagem)
    if corromper:
        checksum = "checksum_invalido"
    pacote = f"{sequencia}|{checksum}|{mensagem}"
    socket_cliente.send(pacote.encode())

def iniciar_cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_cliente:
        socket_cliente.connect((HOST, PORT))
        print("[*] Conectado ao servidor.")

        tamanho_max_msg = int(socket_cliente.recv(1024).decode())
        print(f"[*] Tamanho máximo da mensagem: {tamanho_max_msg} bytes")

        modo_envio = input("Escolha o modo de envio (1 - Único, 2 - Rajada): ").strip()
        socket_cliente.send(modo_envio.encode())

        if modo_envio == '1':
            mensagem = input("Digite a mensagem a ser enviada: ").strip()
            if len(mensagem.encode()) > tamanho_max_msg:
                print("[!] Erro: mensagem excede o tamanho máximo permitido.")
                return
            enviar_pacote(socket_cliente, 1, mensagem)
            resposta = socket_cliente.recv(1024).decode()
            print(f"[Servidor] {resposta}")

        elif modo_envio == '2':
            total_pacotes = int(input("Quantos pacotes deseja enviar em rajada? ").strip())
            corromper_pacote = input("Deseja corromper algum pacote? (s/n): ").strip().lower() == 's'
            pacote_corrompido = int(input(f"Qual número do pacote deseja corromper (1-{total_pacotes})? ").strip()) if corromper_pacote else -1

            for i in range(1, total_pacotes + 1):
                mensagem = f"Pacote {i}"
                corromper = (i == pacote_corrompido)

                if len(mensagem.encode()) > tamanho_max_msg:
                    print(f"[!] Erro: o pacote {i} excede o tamanho permitido ({tamanho_max_msg} bytes).")
                    continue

                enviar_pacote(socket_cliente, i, mensagem, corromper)
                resposta = socket_cliente.recv(1024).decode()
                print(f"[Servidor] {resposta}")

        else:
            print("[!] Opção inválida. Encerrando cliente.")

if __name__ == "_main_":
    iniciar_cliente()