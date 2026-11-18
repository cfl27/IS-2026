
import socket
import struct
import sys

MAX_LONGITUD = 0xFFFF  # lo máximo que cabe en 2 bytes


def recvall(sock, count):
    buf = b""
    while len(buf) < count:
        nuevo = sock.recv(count - len(buf))
        if not nuevo:
            return None
        buf += nuevo
    return buf


puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", puerto))
s.listen(5)
print(f"Servidor OCHE (ejercicio 7 - longitud binaria) escuchando en el puerto {puerto}...")

while True:
    sd, origen = s.accept()
    print(f"Nuevo cliente conectado desde {origen}")

    try:
        while True:
            # 1. Cabecera: exactamente 2 bytes
            cabecera = recvall(sd, 2)
            if cabecera is None:
                print("El cliente ha cerrado la conexión.")
                break

            # 2. Recuperar la longitud (unpack devuelve una tupla)
            longitud = struct.unpack(">H", cabecera)[0]

            # 3. Leer el cuerpo
            datos = recvall(sd, longitud)
            if datos is None:
                print("El cliente cerró la conexión a mitad de un mensaje.")
                break

            # 4. Dar la vuelta y responder con el mismo formato
            respuesta = datos.decode("utf-8")[::-1].encode("utf-8")
            if len(respuesta) > MAX_LONGITUD:
                break  # no cabría en la cabecera de 2 bytes
            sd.sendall(struct.pack(">H", len(respuesta)) + respuesta)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error con el cliente {origen}: {e}")
    finally:
        sd.close()
