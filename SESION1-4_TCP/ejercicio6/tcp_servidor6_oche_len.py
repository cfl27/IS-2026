
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


puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", puerto))
s.listen(5)
print(f"Servidor OCHE (ejercicio 6 - longitud ASCII) escuchando en el puerto {puerto}...")

while True:
    sd, origen = s.accept()
    print(f"Nuevo cliente conectado desde {origen}")

    try:
        while True:
            # Paso 1: cuánto ocupa el mensaje
            longitud = recibe_longitud(sd)
            if longitud is None:
                print("El cliente ha cerrado la conexión.")
                break

            # Paso 2: leer exactamente esos bytes
            datos = recvall(sd, longitud)
            if datos is None:
                print("El cliente cerró la conexión a mitad de un mensaje.")
                break

            # Paso 3: dar la vuelta al texto (ya no hay que quitar "\r\n")
            respuesta = datos.decode("utf-8")[::-1].encode("utf-8")

            # Paso 4: responder con el mismo formato "<longitud>\n<bytes>"
            sd.sendall(f"{len(respuesta)}\n".encode("ascii") + respuesta)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        # Cabecera inválida o cliente caído: se descarta ese cliente, no el servidor
        print(f"Error con el cliente {origen}: {e}")
    finally:
        sd.close()
