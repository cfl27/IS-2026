
import socket
import sys
import time

RETARDO_PRUEBA = 1  # segundos

puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", puerto))
s.listen(5)
print(f"Servidor OCHE (readline, ejercicio 5) escuchando en el puerto {puerto}...")

while True:
    sd, origen = s.accept()
    print(f"Nuevo cliente conectado desde {origen}")
    time.sleep(RETARDO_PRUEBA)

    # Modo texto: readline() devuelve str ya decodificado. newline="\r\n"
    # hace que solo "\r\n" cuente como fin de línea (y se conserva).
    f = sd.makefile(mode="r", encoding="utf8", newline="\r\n")

    try:
        while True:
            mensaje = f.readline()
            if not mensaje:          # "" = el cliente cerró la conexión
                print("El cliente ha cerrado la conexión.")
                break

            linea = mensaje[:-2]     # quitar el "\r\n"
            # Se responde por el socket (el fichero es solo de lectura)
            sd.sendall((linea[::-1] + "\r\n").encode("utf8"))
    except OSError as e:
        print(f"Error con el cliente {origen}: {e}")
    finally:
        f.close()
        sd.close()
