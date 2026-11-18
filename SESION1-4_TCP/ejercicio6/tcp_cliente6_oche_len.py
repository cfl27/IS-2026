
import socket
import sys


def recvall(sock, count):
    buf = b""
    while len(buf) < count:
        nuevo = sock.recv(count - len(buf))
        if not nuevo:
            return None
        buf += nuevo
    return buf


def recibe_longitud(sock):
    buffer = []
    while True:
        byte = sock.recv(1)
        if not byte:
            return None
        if byte == b"\n":
            return int(b"".join(buffer).decode("ascii"))
        buffer.append(byte)


ip = sys.argv[1] if len(sys.argv) > 1 else "localhost"
puerto = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, puerto))

# Ya no hace falta terminar los mensajes en \r\n
mensajes = ["HOLA", "GUILLERMO", "REDES"]

for msg in mensajes:
    print(f"Enviando: {msg}")
    msg_bytes = msg.encode("utf-8")
    # La longitud se mide en BYTES (no en caracteres): importa con tildes/eñes
    cabecera = f"{len(msg_bytes)}\n".encode("ascii")
    s.sendall(cabecera + msg_bytes)

for _ in range(len(mensajes)):
    longitud = recibe_longitud(s)
    respuesta = recvall(s, longitud) if longitud is not None else None
    if respuesta is None:
        print("El servidor cerró la conexión antes de tiempo.")
        break
    print(f"Respuesta recibida (longitud {longitud}): {respuesta.decode('utf-8')}")

s.close()
