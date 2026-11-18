import socket
import sys


def recibe_mensaje(sock):
    buffer = []

    while True:
        byte = sock.recv(1)

        if byte == b"":
            return b""

        buffer.append(byte)

        if len(buffer) >= 2 and buffer[-2] == b"\r" and buffer[-1] == b"\n":
            return b"".join(buffer)


if len(sys.argv) > 1:
    puerto = int(sys.argv[1])
else:
    puerto = 9999


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind(("", puerto))

s.listen(5)

print("Servidor OCHE esperando clientes...")


while True:
    print("Esperando cliente...")

    sd, origen = s.accept()

    print("Nuevo cliente conectado desde:", origen)

    while True:

        mensaje = recibe_mensaje(sd)

        if mensaje == b"":
            print("Conexion cerrada por el cliente")
            break

        mensaje = mensaje.decode("utf-8")

        # Quitamos \r\n
        linea = mensaje[:-2]

        # Invertimos el mensaje
        linea = linea[::-1]

        respuesta = linea + "\r\n"

        sd.sendall(respuesta.encode("utf-8"))

    sd.close()