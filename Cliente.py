import socket

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


def enviar_pacote(socket_cliente, sequencia, mensagem):

    checksum = calcular_checksum(mensagem)
    pacote = f"{sequencia}|{checksum}|{mensagem}"
    socket_cliente.send(pacote.encode())
    print(f"  [ENVIO] Pacote {sequencia} enviado: '{mensagem}'")


def aguardar_ack(socket_cliente, sequencia_esperada):

    resposta = socket_cliente.recv(1024).decode()
    print(f"  [SERVIDOR] {resposta}")

    if resposta.startswith(f"ACK|{sequencia_esperada}"):
        return True
    return False


def modo_go_back_n(socket_cliente, tamanho_max_msg):

    print("\n[*] Modo: Go-Back-N")

    mensagem = input("Digite a mensagem a ser enviada: ").strip()

    if len(mensagem) > tamanho_max_msg:
        print(f"[!] Erro: mensagem excede o tamanho máximo ({tamanho_max_msg} caracteres).")
        return

    enviar_pacote(socket_cliente, 1, mensagem)

    if aguardar_ack(socket_cliente, 1):
        print("[✓] Mensagem entregue com sucesso (canal confiável — ACK na 1ª tentativa).")
    else:
        print("[!] Resposta inesperada do servidor.")


def modo_repeticao_seletiva(socket_cliente, tamanho_max_msg):

    print("\n[*] Modo: Repetição Seletiva")

    total_pacotes = int(input("Quantos pacotes deseja enviar? ").strip())

    print(f"\n[*] Enviando {total_pacotes} pacote(s) — canal confiável, sem perdas/erros.\n")

    for i in range(1, total_pacotes + 1):
        mensagem = f"Pacote {i}"

        if len(mensagem) > tamanho_max_msg:
            print(f"[!] Pacote {i} excede o tamanho permitido ({tamanho_max_msg} caracteres). Pulando.")
            continue

        enviar_pacote(socket_cliente, i, mensagem)

        if aguardar_ack(socket_cliente, i):
            print(f"  [✓] Pacote {i} confirmado.\n")
        else:
            print(f"  [!] Resposta inesperada para pacote {i}.\n")

    print(f"[✓] Todos os {total_pacotes} pacote(s) entregues com sucesso.")


def iniciar_cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_cliente:
        socket_cliente.connect((HOST, PORT))
        print("[*] Conectado ao servidor.")

        tamanho_max_msg = int(input("Digite o tamanho máximo da mensagem em caracteres: ").strip())
        socket_cliente.send(str(tamanho_max_msg).encode())
        print(f"[*] Tamanho máximo definido: {tamanho_max_msg} caracteres")


        print("\nEscolha o modo de envio:")
        print("  1 - Go-Back-N")
        print("  2 - Repetição Seletiva")
        modo_envio = input("Opção: ").strip()
        socket_cliente.send(modo_envio.encode())

        if modo_envio == '1':
            modo_go_back_n(socket_cliente, tamanho_max_msg)

        elif modo_envio == '2':
            modo_repeticao_seletiva(socket_cliente, tamanho_max_msg)

        else:
            print("[!] Opção inválida. Encerrando cliente.")

if __name__ == "__main__":
    iniciar_cliente()