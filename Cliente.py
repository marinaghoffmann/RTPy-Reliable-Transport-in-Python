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


def fragmentar_mensagem(mensagem: str, tamanho_chunk: int = 4) -> list:
    """Quebra a mensagem em lista de fragmentos de até tamanho_chunk caracteres."""
    return [mensagem[i:i + tamanho_chunk] for i in range(0, len(mensagem), tamanho_chunk)]


def enviar_pacote(socket_cliente, sequencia, mensagem):
    checksum = calcular_checksum(mensagem)
    pacote = f"{sequencia}|{checksum}|{mensagem}"
    socket_cliente.send(pacote.encode())
    print(f"  [ENVIO] Pacote {sequencia} enviado: '{mensagem}' (checksum: {checksum})")


def enviar_fim(socket_cliente, sequencia):
    """Envia pacote especial de fim de transmissão."""
    checksum = calcular_checksum("END")
    pacote = f"{sequencia}|{checksum}|END"
    socket_cliente.send(pacote.encode())
    print(f"  [ENVIO] Pacote de fim enviado (seq={sequencia})")


def aguardar_ack(socket_cliente, sequencia_esperada):
    resposta = socket_cliente.recv(1024).decode()
    print(f"  [SERVIDOR] {resposta}")
    if resposta.startswith(f"ACK|{sequencia_esperada}"):
        return True
    return False


def modo_go_back_n(socket_cliente, tamanho_max_msg):
    print("\n[*] Modo: Go-Back-N")

    mensagem = input("Digite a mensagem a ser enviada: ").strip()

    if len(mensagem) < 30:
        print(f"[!] Erro: mensagem deve ter no mínimo 30 caracteres (atual: {len(mensagem)}).")
        return

    if len(mensagem) > tamanho_max_msg:
        print(f"[!] Erro: mensagem excede o tamanho máximo ({tamanho_max_msg} caracteres).")
        return

    fragmentos = fragmentar_mensagem(mensagem)
    print(f"\n[*] Mensagem fragmentada em {len(fragmentos)} pacote(s) de até 4 caracteres.\n")

    for seq, fragmento in enumerate(fragmentos, start=1):
        enviar_pacote(socket_cliente, seq, fragmento)
        if not aguardar_ack(socket_cliente, seq):
            print(f"  [!] Resposta inesperada para pacote {seq}. Abortando.")
            return

    seq_fim = len(fragmentos) + 1
    enviar_fim(socket_cliente, seq_fim)
    if aguardar_ack(socket_cliente, seq_fim):
        print("\n[✓] Mensagem entregue com sucesso.")
    else:
        print("\n[!] Servidor não confirmou o fim da transmissão.")


def modo_repeticao_seletiva(socket_cliente, tamanho_max_msg):
    print("\n[*] Modo: Repetição Seletiva")

    mensagem = input("Digite a mensagem a ser enviada: ").strip()

    if len(mensagem) < 30:
        print(f"[!] Erro: mensagem deve ter no mínimo 30 caracteres (atual: {len(mensagem)}).")
        return

    if len(mensagem) > tamanho_max_msg:
        print(f"[!] Erro: mensagem excede o tamanho máximo ({tamanho_max_msg} caracteres).")
        return

    fragmentos = fragmentar_mensagem(mensagem)
    print(f"\n[*] Mensagem fragmentada em {len(fragmentos)} pacote(s) de até 4 caracteres.\n")

    for seq, fragmento in enumerate(fragmentos, start=1):
        enviar_pacote(socket_cliente, seq, fragmento)
        if aguardar_ack(socket_cliente, seq):
            print(f"  [✓] Pacote {seq} confirmado.\n")
        else:
            print(f"  [!] Resposta inesperada para pacote {seq}.\n")

    seq_fim = len(fragmentos) + 1
    enviar_fim(socket_cliente, seq_fim)
    if aguardar_ack(socket_cliente, seq_fim):
        print("\n[✓] Mensagem entregue com sucesso.")
    else:
        print("\n[!] Servidor não confirmou o fim da transmissão.")


def iniciar_cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_cliente:
        socket_cliente.connect((HOST, PORT))
        print("[*] Conectado ao servidor.")

        tamanho_max_msg = int(input("Digite o tamanho máximo da mensagem em caracteres (mínimo 30): ").strip())
        if tamanho_max_msg < 30:
            print("[!] Tamanho máximo deve ser pelo menos 30. Encerrando.")
            return
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