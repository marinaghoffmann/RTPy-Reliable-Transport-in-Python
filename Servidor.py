import socket
import threading

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


def processar_pacote(conexao, dados, modo_operacao):

    partes = dados.split('|', 2)

    if len(partes) != 3:
        print("[!] Pacote malformado recebido. Ignorando.")
        conexao.send("NACK|MALFORMADO".encode())
        return True

    sequencia_str, checksum_recebido, mensagem = partes

    try:
        sequencia = int(sequencia_str)
    except ValueError:
        print(f"[!] Número de sequência inválido: '{sequencia_str}'. Ignorando.")
        conexao.send("NACK|SEQ_INV".encode())
        return True

    checksum_calculado = calcular_checksum(mensagem)

    if checksum_recebido != checksum_calculado:
        print(f"  [!] Erro de integridade no pacote {sequencia}. Enviando NACK.")
        conexao.send(f"NACK|{sequencia}".encode())
    else:

        print(f"  [✓] Pacote {sequencia} recebido corretamente: '{mensagem}'")
        conexao.send(f"ACK|{sequencia}".encode())

    return True


def processar_cliente(conexao, endereco):
    print(f"\n[+] Conexão estabelecida com {endereco}")

    tamanho_maximo = int(conexao.recv(1024).decode())
    print(f"[*] Tamanho máximo da mensagem: {tamanho_maximo} caracteres")

    modo_operacao = conexao.recv(1024).decode()
    nome_modo = MODOS.get(modo_operacao, f"Desconhecido ({modo_operacao})")
    print(f"[*] Handshake concluído! Modo: {nome_modo}")
    print(f"[*] Canal confiável ativo — sem simulação de erros ou perdas.\n")


    while True:
        try:
            dados = conexao.recv(1024).decode()
            if not dados:
                break

            continuar = processar_pacote(conexao, dados, modo_operacao)
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


def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen()
    print(f"[*] Servidor aguardando conexões em {HOST}:{PORT}\n")

    while True:
        conexao, endereco = servidor.accept()
        thread = threading.Thread(target=processar_cliente, args=(conexao, endereco))
        thread.daemon = True
        thread.start()


if __name__ == "__main__":
    iniciar_servidor()