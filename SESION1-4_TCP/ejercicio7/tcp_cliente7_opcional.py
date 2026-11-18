
import socket
import struct
import sys


def recvall(sock, count):
    while len(buf) < count:
        nuevo = sock.recv(count - len(buf))
        if not nuevo:
            return None
        buf += nuevo
    return buf


ip = sys.argv[1] if len(sys.argv) > 1 else "localhost"
puerto = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, puerto))

mensajes = ["HOLA", "GUILLERMO", "REDES"]

for msg in mensajes:
    print(f"Enviando: {msg}")
    msg_bytes = msg.encode("utf-8")
    # ">H" = Big Endian (>) + unsigned short de 2 bytes (H)
    cabecera = struct.pack(">H", len(msg_bytes))
    s.sendall(cabecera + msg_bytes)

for _ in range(len(mensajes)):
    cabecera = recvall(s, 2)
    if cabecera is None:
        print("El servidor cerró la conexión antes de tiempo.")
        break
    # unpack devuelve una tupla; el entero está en la posición 0
    longitud = struct.unpack(">H", cabecera)[0]
    respuesta = recvall(s, longitud)
    if respuesta is None:
        print("El servidor cerró la conexión antes de tiempo.")
        break
    print(f"Respuesta recibida (longitud binaria {longitud}): {respuesta.decode('utf-8')}")

s.close()
