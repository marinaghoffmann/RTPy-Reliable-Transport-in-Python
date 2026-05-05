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


def montar_pacote(sequencia, mensagem, corromper=False):
    checksum = calcular_checksum(mensagem)
    if corromper:
        checksum_corrompido = format(int(checksum, 16) ^ 0xFFFF, '04x')
        print(f"  [ERRO SIMULADO] Pacote {sequencia}: checksum original={checksum}, corrompido={checksum_corrompido}")
        return f"{sequencia}|{checksum_corrompido}|{mensagem}", checksum_corrompido
    return f"{sequencia}|{checksum}|{mensagem}", checksum


def enviar_pacote(socket_cliente, sequencia, mensagem, corromper=False):
    pacote, checksum = montar_pacote(sequencia, mensagem, corromper)
    enviar_linha(socket_cliente, pacote)
    if not corromper:
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


def coletar_acks_janela(socket_cliente, janela_atual, pacotes_enviados):
    respostas = {}
    for i, idx in enumerate(janela_atual):
        if not pacotes_enviados[i]:
            continue 
        socket_cliente.settimeout(TIMEOUT)
        try:
            resposta = receber_linha(socket_cliente)
            print(f"  [SERVIDOR] {resposta}")
            partes = resposta.split('|')
            if len(partes) == 2:
                tipo, seq_str = partes
                try:
                    respostas[int(seq_str)] = tipo
                except ValueError:
                    pass
        except socket.timeout:
            print(f"  [TIMEOUT] Sem resposta para pacote {idx+1}.")
        finally:
            socket_cliente.settimeout(None)
    return respostas


def enviar_janela_go_back_n(socket_cliente, fragmentos, tamanho_janela, tipo_falha=None, pacote_falha=None):
    total = len(fragmentos)
    base = 0

    while base < total:
        fim_janela = min(base + tamanho_janela, total)
        janela_atual = list(range(base, fim_janela))

        print(f"\n  [JANELA] Enviando pacotes {base+1} a {fim_janela} (janela={tamanho_janela})")

        pacotes_enviados = []
        for idx in janela_atual:
            seq = idx + 1
            corromper = (tipo_falha == 'erro' and seq == pacote_falha)
            perder = (tipo_falha == 'perda' and seq == pacote_falha)
            if perder:
                print(f"  [PERDA SIMULADA] Pacote {seq} não enviado (simulando perda no canal).")
                pacotes_enviados.append(False)
            else:
                enviar_pacote(socket_cliente, seq, fragmentos[idx], corromper=corromper)
                pacotes_enviados.append(True)

        respostas = coletar_acks_janela(socket_cliente, janela_atual, pacotes_enviados)

        falha_idx = None
        for idx in janela_atual:
            seq = idx + 1
            tipo = respostas.get(seq)
            if tipo != 'ACK':
                falha_idx = idx
                if tipo == 'NACK':
                    print(f"  [NACK] Pacote {seq} rejeitado.")
                else:
                    print(f"  [TIMEOUT] Pacote {seq} sem resposta.")
                break

        if falha_idx is not None:
            retransmitir = list(range(falha_idx, fim_janela))
            print(f"  [GO-BACK-N] Retransmitindo pacotes {falha_idx+1} a {fim_janela}...")
            for idx in retransmitir:
                seq = idx + 1
                if not enviar_com_retransmissao(socket_cliente, seq, fragmentos[idx]):
                    print(f"  [ABORTANDO] Não foi possível confirmar pacote {seq}.")
                    return False

        base = fim_janela

    return True


def enviar_janela_repeticao_seletiva(socket_cliente, fragmentos, tamanho_janela, tipo_falha=None, pacote_falha=None):
    total = len(fragmentos)
    base = 0

    while base < total:
        fim_janela = min(base + tamanho_janela, total)
        janela_atual = list(range(base, fim_janela))

        print(f"\n  [JANELA] Enviando pacotes {base+1} a {fim_janela} (janela={tamanho_janela})")

        pacotes_enviados = []
        for idx in janela_atual:
            seq = idx + 1
            corromper = (tipo_falha == 'erro' and seq == pacote_falha)
            perder = (tipo_falha == 'perda' and seq == pacote_falha)
            if perder:
                print(f"  [PERDA SIMULADA] Pacote {seq} não enviado (simulando perda no canal).")
                pacotes_enviados.append(False)
            else:
                enviar_pacote(socket_cliente, seq, fragmentos[idx], corromper=corromper)
                pacotes_enviados.append(True)

        respostas = coletar_acks_janela(socket_cliente, janela_atual, pacotes_enviados)

        for idx in janela_atual:
            seq = idx + 1
            tipo = respostas.get(seq)
            if tipo == 'ACK':
                continue
            elif tipo == 'NACK':
                print(f"  [NACK] Pacote {seq} rejeitado. Retransmitindo apenas este...")
            else:
                print(f"  [TIMEOUT] Pacote {seq} sem resposta. Retransmitindo apenas este...")
            if not enviar_com_retransmissao(socket_cliente, seq, fragmentos[idx]):
                print(f"  [ABORTANDO] Não foi possível confirmar pacote {seq}.")
                return False

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


def perguntar_simulacao(total_fragmentos):
    print(f"\n[*] A mensagem será enviada em {total_fragmentos} pacote(s).")
    print("Deseja simular algum problema?")
    print("  1 - Erro de integridade (checksum corrompido)")
    print("  2 - Perda de pacote (pacote não enviado)")
    print("  n - Não simular")
    escolha = input("Opção: ").strip().lower()

    if escolha not in ('1', '2'):
        return None, None

    tipo = 'erro' if escolha == '1' else 'perda'
    descricao = 'corromper' if tipo == 'erro' else 'perder'

    while True:
        try:
            numero = int(input(f"Digite o número do pacote a {descricao} (1 a {total_fragmentos}): ").strip())
            if 1 <= numero <= total_fragmentos:
                return tipo, numero
            print(f"[!] Número inválido. Digite entre 1 e {total_fragmentos}.")
        except ValueError:
            print("[!] Entrada inválida. Digite um número inteiro.")


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
    tipo_falha, pacote_falha = perguntar_simulacao(len(fragmentos))

    if tipo_falha:
        label = 'corrompido' if tipo_falha == 'erro' else 'perdido'
        print(f"[*] Pacote {pacote_falha} será {label}.")

    print(f"\n[*] Mensagem fragmentada em {len(fragmentos)} pacote(s) de até 4 caracteres.")

    if not enviar_janela_go_back_n(socket_cliente, fragmentos, tamanho_janela, tipo_falha, pacote_falha):
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
    tipo_falha, pacote_falha = perguntar_simulacao(len(fragmentos))

    if tipo_falha:
        label = 'corrompido' if tipo_falha == 'erro' else 'perdido'
        print(f"[*] Pacote {pacote_falha} será {label}.")

    print(f"\n[*] Mensagem fragmentada em {len(fragmentos)} pacote(s) de até 4 caracteres.")

    if not enviar_janela_repeticao_seletiva(socket_cliente, fragmentos, tamanho_janela, tipo_falha, pacote_falha):
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