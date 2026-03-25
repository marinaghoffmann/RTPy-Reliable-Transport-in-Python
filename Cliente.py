import socket
import hashlib

HOST = 'localhost'
PORT = 12345

def calcular_checksum(mensagem: str) -> str:
    dados = mensagem.encode()
    if len(dados) % 2 != 0:
        dados += b'\x00'

    soma = 0
    for i in range(0, len(dados), 2):
        palavra = (dados[i] << 8) + dados[i + 1]
        soma += palavra
        soma = (soma & 0xFFFF) + (soma >> 16)  

    checksum = ~soma & 0xFFFF
    return format(checksum, '04x')

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

        tamanho_max_msg = int(input("Digite o tamanho máximo da mensagem em caracteres: ").strip())
        socket_cliente.send(str(tamanho_max_msg).encode())
        print(f"[*] Tamanho máximo da mensagem definido: {tamanho_max_msg} caracteres")

        print("\nEscolha o modo de envio:")
        print("  1 - Go-Back-N")
        print("  2 - Repetição Seletiva")
        modo_envio = input("Opção: ").strip()
        socket_cliente.send(modo_envio.encode())

        if modo_envio == '1':
            print("\n[*] Modo: Go-Back-N")
            mensagem = input("Digite a mensagem a ser enviada: ").strip()
            if len(mensagem) > tamanho_max_msg:
                print(f"[!] Erro: mensagem excede o tamanho máximo permitido ({tamanho_max_msg} caracteres).")
                return
            enviar_pacote(socket_cliente, 1, mensagem)
            resposta = socket_cliente.recv(1024).decode()
            print(f"[Servidor] {resposta}")

        elif modo_envio == '2':
            print("\n[*] Modo: Repetição Seletiva")
            total_pacotes = int(input("Quantos pacotes deseja enviar em rajada? ").strip())
            corromper_pacote = input("Deseja corromper algum pacote? (s/n): ").strip().lower() == 's'
            pacote_corrompido = int(input(f"Qual número do pacote deseja corromper (1-{total_pacotes})? ").strip()) if corromper_pacote else -1

            for i in range(1, total_pacotes + 1):
                mensagem = f"Pacote {i}"
                corromper = (i == pacote_corrompido)

                if len(mensagem) > tamanho_max_msg:
                    print(f"[!] Erro: o pacote {i} excede o tamanho permitido ({tamanho_max_msg} caracteres).")
                    continue

                enviar_pacote(socket_cliente, i, mensagem, corromper)
                resposta = socket_cliente.recv(1024).decode()
                print(f"[Servidor] {resposta}")

        else:
            print("[!] Opção inválida. Encerrando cliente.")

if __name__ == "__main__":
    iniciar_cliente()