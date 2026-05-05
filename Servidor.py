import socket

HOST = 'localhost'
PORT = 12345

MODOS = {
    '1': 'Go-Back-N',
    '2': 'Repetição Seletiva',
}


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


def processar_pacote(conexao, dados, fragmentos_recebidos):
    partes = dados.split('|', 2)

    if len(partes) != 3:
        print("[!] Pacote malformado recebido.")
        enviar_linha(conexao, "NACK|MALFORMADO")
        return True, False

    sequencia_str, checksum_recebido, mensagem = partes

    try:
        sequencia = int(sequencia_str)
    except ValueError:
        print(f"[!] Número de sequência inválido: '{sequencia_str}'.")
        enviar_linha(conexao, "NACK|SEQ_INV")
        return True, False

    checksum_calculado = calcular_checksum(mensagem)
    if checksum_recebido != checksum_calculado:
        print(f"  [!] Erro de integridade no pacote {sequencia}. Enviando NACK.")
        enviar_linha(conexao, f"NACK|{sequencia}")
        return True, False

    if mensagem == "END":
        print(f"\n  [✓] Pacote de fim recebido (seq={sequencia}).")
        enviar_linha(conexao, f"ACK|{sequencia}")
        return True, True

    print(f"  [✓] Pacote {sequencia} | checksum: {checksum_recebido} | conteúdo: '{mensagem}'")
    fragmentos_recebidos[sequencia] = mensagem
    enviar_linha(conexao, f"ACK|{sequencia}")
    return True, False


def iniciar_servidor():
    while True:
        try:
            tamanho_janela = int(input("Digite o tamanho da janela (1 a 5): ").strip())
            if 1 <= tamanho_janela <= 5:
                break
            print("[!] Valor inválido. Digite um número entre 1 e 5.")
        except ValueError:
            print("[!] Entrada inválida. Digite um número inteiro.")

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen()
    print(f"\n[*] Servidor aguardando conexões em {HOST}:{PORT}")
    print(f"[*] Tamanho de janela configurado: {tamanho_janela}\n")

    while True:
        conexao, endereco = servidor.accept()
        print(f"\n[+] Conexão estabelecida com {endereco}")

        tamanho_maximo = int(receber_linha(conexao))
        print(f"[*] Tamanho máximo da mensagem: {tamanho_maximo} caracteres")

        modo_operacao = receber_linha(conexao)
        nome_modo = MODOS.get(modo_operacao, f"Desconhecido ({modo_operacao})")
        print(f"[*] Modo de operação: {nome_modo}")

        pedido = receber_linha(conexao)
        if pedido == "WINDOW?":
            enviar_linha(conexao, f"WINDOW|{tamanho_janela}")
            print(f"[*] Janela negociada: {tamanho_janela}\n")

        fragmentos_recebidos = {}

        while True:
            try:
                dados = receber_linha(conexao)
                if not dados:
                    break

                continuar, fim = processar_pacote(conexao, dados, fragmentos_recebidos)

                if fim:
                    mensagem_completa = ''.join(
                        fragmentos_recebidos[k] for k in sorted(fragmentos_recebidos)
                    )
                    print(f"\n[✓] Mensagem completa recebida: '{mensagem_completa}'")
                    fragmentos_recebidos = {}

                if not continuar:
                    break

            except ConnectionResetError:
                print(f"[!] Conexão com {endereco} encerrada abruptamente.")
                break
            except Exception as e:
                print(f"[!] Erro inesperado com {endereco}: {e}")
                break

        conexao.close()
        print(f"\n[-] Conexão encerrada com {endereco}")
        print("[*] Aguardando próxima conexão...\n")


if __name__ == "__main__":
    iniciar_servidor()