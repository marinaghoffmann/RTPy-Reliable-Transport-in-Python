import socket
import threading
import hashlib

HOST = 'localhost'
PORT = 12345
WINDOW_SIZE = 5

MODOS = {
    '1': 'Go-Back-N',
    '2': 'Repetição Seletiva',
}

def calcular_checksum(mensagem):
    return hashlib.md5(mensagem.encode()).hexdigest()

def processar_cliente(conexao, endereco):
    print(f"[+] Conexão estabelecida com {endereco}")

    tamanho_maximo = int(conexao.recv(1024).decode())
    print(f"[*] Tamanho máximo da mensagem definido pelo cliente: {tamanho_maximo} caracteres")

    modo_operacao = conexao.recv(1024).decode()
    nome_modo = MODOS.get(modo_operacao, f"Desconhecido ({modo_operacao})")
    print(f"[*] Handshake concluído! Modo de operação: {nome_modo}")

    while True:
        try:
            dados = conexao.recv(1024).decode()
            if not dados:
                break

            partes = dados.split('|', 2)
            if len(partes) != 3:
                print("[!] Pacote malformado recebido. Ignorando.")
                conexao.send("NACK|MALFORMADO".encode())
                continue

            sequencia, checksum_recebido, mensagem = partes
            sequencia = int(sequencia)

            checksum_calculado = calcular_checksum(mensagem)

            if checksum_recebido != checksum_calculado:
                print(f"[!] Erro de integridade detectado no pacote {sequencia}. Enviando NACK.")
                conexao.send(f"NACK|{sequencia}".encode())
            else:
                print(f"[✓] Pacote {sequencia} recebido com sucesso: {mensagem}")
                conexao.send(f"ACK|{sequencia}".encode())

        except ConnectionResetError:
            print(f"[!] Conexão com {endereco} foi encerrada abruptamente.")
            break

    conexao.close()
    print(f"[-] Conexão encerrada com {endereco}")

def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind((HOST, PORT))
    servidor.listen()
    print(f"[*] Servidor aguardando conexões em {HOST}:{PORT}")

    while True:
        conexao, endereco = servidor.accept()
        cliente_thread = threading.Thread(target=processar_cliente, args=(conexao, endereco))
        cliente_thread.start()

if __name__ == "__main__":
    iniciar_servidor()