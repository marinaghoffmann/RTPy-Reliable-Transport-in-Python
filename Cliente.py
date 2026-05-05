import socket

HOST = 'localhost'
PORT = 12345
TIMEOUT = 3   
MAX_TENTATIVAS = 3  


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
    return [mensagem[i:i + tamanho_chunk] for i in range(0, len(mensagem), tamanho_chunk)]


def enviar_linha(sock, texto):
    sock.send((texto + '\n').encode())


def receber_linha(sock):
    buffer = b''
    while True:
        byte = sock.recv(1)
        if not byte or byte == b'\n':
            break
        buffer += byte
    return buffer.decode()


def montar_pacote(sequencia, mensagem):
    checksum = calcular_checksum(mensagem)
    return f"{sequencia}|{checksum}|{mensagem}", checksum


def enviar_pacote(socket_cliente, sequencia, mensagem):
    pacote, checksum = montar_pacote(sequencia, mensagem)
    enviar_linha(socket_cliente, pacote)
    print(f"  [ENVIO] Pacote {sequencia} enviado: '{mensagem}' (checksum: {checksum})")


def enviar_fim(socket_cliente, sequencia):
    checksum = calcular_checksum("END")
    enviar_linha(socket_cliente, f"{sequencia}|{checksum}|END")
    print(f"  [ENVIO] Pacote de fim enviado (seq={sequencia})")


def aguardar_ack_com_timeout(socket_cliente, sequencia_esperada):
    socket_cliente.settimeout(TIMEOUT)
    try:
        resposta = receber_linha(socket_cliente)
        print(f"  [SERVIDOR] {resposta}")
        return resposta.startswith(f"ACK|{sequencia_esperada}")
    except socket.timeout:
        print(f"  [TIMEOUT] Sem resposta para pacote {sequencia_esperada} após {TIMEOUT}s.")
        return False
    finally:
        socket_cliente.settimeout(None)


def enviar_com_retransmissao(socket_cliente, sequencia, mensagem):
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        if tentativa > 1:
            print(f"  [RETRANSMISSÃO] Pacote {sequencia}, tentativa {tentativa}/{MAX_TENTATIVAS}")
        enviar_pacote(socket_cliente, sequencia, mensagem)
        if aguardar_ack_com_timeout(socket_cliente, sequencia):
            return True

    print(f"  [FALHA] Pacote {sequencia} não confirmado após {MAX_TENTATIVAS} tentativas.")
    return False


def enviar_fim_com_retransmissao(socket_cliente, sequencia):
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        if tentativa > 1:
            print(f"  [RETRANSMISSÃO] Pacote de fim, tentativa {tentativa}/{MAX_TENTATIVAS}")
        enviar_fim(socket_cliente, sequencia)
        if aguardar_ack_com_timeout(socket_cliente, sequencia):
            return True

    print(f"  [FALHA] Pacote de fim não confirmado após {MAX_TENTATIVAS} tentativas.")
    return False


def enviar_com_janela(socket_cliente, fragmentos, tamanho_janela):
    total = len(fragmentos)
    base = 0

    while base < total:
        fim_janela = min(base + tamanho_janela, total)
        janela_atual = list(range(base, fim_janela))

        print(f"\n  [JANELA] Enviando pacotes {base+1} a {fim_janela} (janela={tamanho_janela})")

        for idx in janela_atual:
            enviar_pacote(socket_cliente, idx + 1, fragmentos[idx])

        for idx in janela_atual:
            seq = idx + 1
            socket_cliente.settimeout(TIMEOUT)
            try:
                resposta = receber_linha(socket_cliente)
                print(f"  [SERVIDOR] {resposta}")
                if resposta.startswith(f"ACK|{seq}"):
                    continue
                print(f"  [NACK] Pacote {seq} rejeitado. Retransmitindo...")
                if not enviar_com_retransmissao(socket_cliente, seq, fragmentos[idx]):
                    print(f"  [ABORTANDO] Não foi possível confirmar pacote {seq}.")
                    return False
            except socket.timeout:
                print(f"  [TIMEOUT] Sem resposta para pacote {seq}. Retransmitindo...")
                socket_cliente.settimeout(None)
                if not enviar_com_retransmissao(socket_cliente, seq, fragmentos[idx]):
                    print(f"  [ABORTANDO] Não foi possível confirmar pacote {seq}.")
                    return False
            finally:
                socket_cliente.settimeout(None)

        base = fim_janela

    return True


def negociar_janela(socket_cliente):
    enviar_linha(socket_cliente, "WINDOW?")
    resposta = receber_linha(socket_cliente)
    if resposta.startswith("WINDOW|"):
        tamanho = int(resposta.split("|")[1])
        print(f"[*] Tamanho da janela recebido do servidor: {tamanho}")
        return tamanho
    print("[!] Resposta inválida para WINDOW?. Usando janela=1.")
    return 1


def modo_go_back_n(socket_cliente, tamanho_max_msg, tamanho_janela):
    print("\n[*] Modo: Go-Back-N")
    mensagem = input("Digite a mensagem a ser enviada: ").strip()

    if len(mensagem) < 30:
        print(f"[!] Erro: mensagem deve ter no mínimo 30 caracteres (atual: {len(mensagem)}).")
        return
    if len(mensagem) > tamanho_max_msg:
        print(f"[!] Erro: mensagem excede o tamanho máximo ({tamanho_max_msg} caracteres).")
        return

    fragmentos = fragmentar_mensagem(mensagem)
    print(f"[*] Mensagem fragmentada em {len(fragmentos)} pacote(s) de até 4 caracteres.")

    if not enviar_com_janela(socket_cliente, fragmentos, tamanho_janela):
        print("\n[✗] Transmissão falhou.")
        return

    seq_fim = len(fragmentos) + 1
    if enviar_fim_com_retransmissao(socket_cliente, seq_fim):
        print("\n[✓] Mensagem entregue com sucesso.")
    else:
        print("\n[✗] Transmissão falhou.")


def modo_repeticao_seletiva(socket_cliente, tamanho_max_msg, tamanho_janela):
    print("\n[*] Modo: Repetição Seletiva")
    mensagem = input("Digite a mensagem a ser enviada: ").strip()

    if len(mensagem) < 30:
        print(f"[!] Erro: mensagem deve ter no mínimo 30 caracteres (atual: {len(mensagem)}).")
        return
    if len(mensagem) > tamanho_max_msg:
        print(f"[!] Erro: mensagem excede o tamanho máximo ({tamanho_max_msg} caracteres).")
        return

    fragmentos = fragmentar_mensagem(mensagem)
    print(f"[*] Mensagem fragmentada em {len(fragmentos)} pacote(s) de até 4 caracteres.")

    if not enviar_com_janela(socket_cliente, fragmentos, tamanho_janela):
        print("\n[✗] Transmissão falhou.")
        return

    seq_fim = len(fragmentos) + 1
    if enviar_fim_com_retransmissao(socket_cliente, seq_fim):
        print("\n[✓] Mensagem entregue com sucesso.")
    else:
        print("\n[✗] Transmissão falhou.")


def iniciar_cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_cliente:
        socket_cliente.connect((HOST, PORT))
        print("[*] Conectado ao servidor.")

        while True:
            try:
                tamanho_max_msg = int(input("Digite o tamanho máximo da mensagem em caracteres (mínimo 30): ").strip())
                if tamanho_max_msg >= 30:
                    break
                print("[!] Valor inválido. Digite um número maior ou igual a 30.")
            except ValueError:
                print("[!] Entrada inválida. Digite um número inteiro.")
        enviar_linha(socket_cliente, str(tamanho_max_msg))
        print(f"[*] Tamanho máximo definido: {tamanho_max_msg} caracteres")

        print("\nEscolha o modo de envio:")
        print("  1 - Go-Back-N")
        print("  2 - Repetição Seletiva")
        modo_envio = input("Opção: ").strip()
        enviar_linha(socket_cliente, modo_envio)

        tamanho_janela = negociar_janela(socket_cliente)

        if modo_envio == '1':
            modo_go_back_n(socket_cliente, tamanho_max_msg, tamanho_janela)
        elif modo_envio == '2':
            modo_repeticao_seletiva(socket_cliente, tamanho_max_msg, tamanho_janela)
        else:
            print("[!] Opção inválida. Encerrando.")

if __name__ == "__main__":
    iniciar_cliente()