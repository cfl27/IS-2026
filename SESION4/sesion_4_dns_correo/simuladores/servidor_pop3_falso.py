"""Simulador: servidor POP3 de juguete (TLS implícito) sobre el buzón del SMTP falso.

Qué hace: escucha en 127.0.0.1 (por defecto puerto 5995, el "995" de
pop.gmail.com pero sin necesitar root) y sirve por POP3 (RFC 1939) los .eml
que ha ido guardando servidor_smtp_falso.py en el directorio buzón.
Órdenes: USER PASS STAT LIST RETR TOP DELE RSET NOOP UIDL CAPA QUIT.

Ejecución (normalmente lo lanza simuladores/lanzar_simuladores.sh):
    IS_SIM_USER=alumno@example.com IS_SIM_PASS=secreto \\
      python3 simuladores/servidor_pop3_falso.py --puerto 5995 --buzon /tmp/buzon \\
      --cert cert.pem --clave clave.pem
  Sin --cert habla POP3 en claro (como el puerto 110).

Concepto: la MÁQUINA DE ESTADOS de POP3 vista desde el servidor:
  AUTHORIZATION  solo USER, PASS y QUIT. Con PASS correcto se "abre" el
                 buzón: se toma una FOTO de los mensajes que hay (los que
                 lleguen después no se ven hasta la próxima sesión) y se
                 BLOQUEA, para que dos clientes no lo manipulen a la vez.
  TRANSACTION    STAT/LIST/RETR/TOP leen; DELE solo MARCA; RSET desmarca.
                 Los números de mensaje no cambian durante la sesión.
  UPDATE         al recibir QUIT en TRANSACTION se borran DE VERDAD los
                 marcados. Si la conexión se corta sin QUIT, no se borra
                 nada: así un fallo de red no hace perder correo.
Respuestas: "+OK ..." o "-ERR ..."; las multilínea acaban en "." con
dot-stuffing (al revés que el SMTP: aquí el servidor AÑADE los puntos).
TLS implícito: wrap_socket() justo después de accept(), antes del saludo.
"""
import argparse
import os
import socket
import ssl
import sys
import threading

bloqueo_buzon = threading.Lock()     # un único cliente en TRANSACTION


class SesionPOP3:
    def __init__(self, sock, id_cliente, buzon):
        self.sock, self.id, self.dir_buzon = sock, id_cliente, buzon
        self.buffer = b""
        self.estado = "AUTHORIZATION"
        self.usuario = None
        self.mensajes = []      # [(ruta, bytes)] foto del buzón; índice = nº - 1
        self.borrados = set()   # números marcados con DELE

    # ------------------------------------------------------------ E/S
    def leer_linea(self):
        while b"\n" not in self.buffer:
            trozo = self.sock.recv(4096)
            if not trozo or len(self.buffer) > 8192:
                return None
            self.buffer += trozo
        linea, self.buffer = self.buffer.split(b"\n", 1)
        return linea.rstrip(b"\r").decode("utf-8", "replace")

    def ok(self, texto="", datos=None):
        """+OK de una línea, o multilínea si se dan `datos` (lista de líneas bytes)."""
        print(f"[{self.id}] S: +OK {texto}", flush=True)
        salida = f"+OK {texto}\r\n".encode()
        if datos is not None:
            # Dot-stuffing: una línea de datos que empiece por "." se dobla,
            # para no confundirla con el terminador
            salida += b"".join((b"." + l if l.startswith(b".") else l) + b"\r\n" for l in datos)
            salida += b".\r\n"
            print(f"[{self.id}] S: [{len(datos)} líneas] + .", flush=True)
        self.sock.sendall(salida)

    def err(self, texto):
        print(f"[{self.id}] S: -ERR {texto}", flush=True)
        self.sock.sendall(f"-ERR {texto}\r\n".encode())

    # ------------------------------------------------------------ buzón
    def abrir_buzon(self):
        nombres = sorted(n for n in os.listdir(self.dir_buzon)
                         if n.endswith(".eml") and not n.startswith("."))
        for n in nombres:
            ruta = os.path.join(self.dir_buzon, n)
            with open(ruta, "rb") as f:
                # Normalizar a CRLF: el tamaño que da POP3 es el del mensaje
                # TAL COMO SE TRANSMITE (RFC 1939: con CRLF)
                datos = f.read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            self.mensajes.append((ruta, datos))

    def mensaje(self, argumento):
        """Valida 'n' y devuelve (n, bytes), o None tras responder -ERR."""
        try:
            n = int(argumento)
        except ValueError:
            return self.err("Falta el número de mensaje")
        if not 1 <= n <= len(self.mensajes):
            return self.err(f"No existe el mensaje {n}")
        if n in self.borrados:
            return self.err(f"El mensaje {n} ya está marcado para borrar")
        return n, self.mensajes[n - 1][1]

    def vivos(self):
        return [(n, m) for n, (_, m) in enumerate(self.mensajes, 1) if n not in self.borrados]

    # ------------------------------------------------------------ órdenes
    def autorizacion(self, verbo, arg):
        if verbo == "USER":
            self.usuario = arg
            return self.ok("Usuario recibido, ahora PASS")
        if verbo == "PASS":
            if self.usuario is None:
                return self.err("Primero USER")
            if self.usuario != os.getenv("IS_SIM_USER") or arg != os.getenv("IS_SIM_PASS"):
                self.usuario = None
                return self.err("[AUTH] Usuario o contraseña incorrectos")
            if not bloqueo_buzon.acquire(blocking=False):
                return self.err("[IN-USE] El buzón está abierto en otra sesión")
            self.abrir_buzon()
            self.estado = "TRANSACTION"
            return self.ok(f"Bienvenido, {len(self.mensajes)} mensajes")
        if verbo == "CAPA":
            return self.ok("Capacidades", [b"USER", b"TOP", b"UIDL"])
        self.err("En AUTHORIZATION solo vale USER, PASS o QUIT")

    def transaccion(self, verbo, arg):
        if verbo == "STAT":
            # "+OK <nº mensajes> <octetos>", sin contar los marcados
            vivos = self.vivos()
            return self.ok(f"{len(vivos)} {sum(len(m) for _, m in vivos)}")
        if verbo == "LIST":
            if arg:
                r = self.mensaje(arg)
                return r and self.ok(f"{r[0]} {len(r[1])}")
            vivos = self.vivos()
            return self.ok(f"{len(vivos)} mensajes",
                           [f"{n} {len(m)}".encode() for n, m in vivos])
        if verbo == "UIDL":
            # Identificador ÚNICO y estable (aquí, el nombre del fichero): el
            # cliente lo usa para saber qué mensajes ya se había bajado
            return self.ok("Identificadores", [
                f"{n} {os.path.basename(self.mensajes[n - 1][0])}".encode() for n, _ in self.vivos()])
        if verbo == "RETR":
            r = self.mensaje(arg)
            if r:
                # Se quita SOLO el último CRLF: el terminador "." va en su línea
                cuerpo = r[1][:-2] if r[1].endswith(b"\r\n") else r[1]
                self.ok(f"{len(r[1])} octetos", cuerpo.split(b"\r\n"))
            return
        if verbo == "TOP":
            # TOP n k: cabeceras + línea en blanco + k primeras líneas del cuerpo
            partes = arg.split()
            if len(partes) != 2 or not partes[1].isdigit():
                return self.err("Sintaxis: TOP <mensaje> <líneas>")
            r = self.mensaje(partes[0])
            if r:
                cab, _, cuerpo = r[1].partition(b"\r\n\r\n")
                lineas = cab.split(b"\r\n") + [b""] + cuerpo.split(b"\r\n")[:int(partes[1])]
                self.ok("Cabeceras a continuación", lineas)
            return
        if verbo == "DELE":
            r = self.mensaje(arg)
            if r:
                self.borrados.add(r[0])
                self.ok(f"Mensaje {r[0]} marcado (se borrará al hacer QUIT)")
            return
        if verbo == "RSET":
            self.borrados.clear()
            return self.ok(f"Desmarcados; {len(self.mensajes)} mensajes")
        if verbo == "NOOP":
            return self.ok()
        if verbo == "CAPA":
            return self.ok("Capacidades", [b"USER", b"TOP", b"UIDL"])
        self.err("Orden no reconocida")

    def actualizar(self):
        """Estado UPDATE: ahora sí se borran los marcados."""
        for n in sorted(self.borrados):
            os.remove(self.mensajes[n - 1][0])
        return len(self.borrados)

    def atender(self):
        self.ok("POP3 simulador de prácticas listo")
        try:
            while True:
                linea = self.leer_linea()
                if linea is None:
                    print(f"[{self.id}] -- cortado sin QUIT: no se borra nada", flush=True)
                    break
                verbo, _, arg = linea.partition(" ")
                verbo = verbo.upper()
                visible = "PASS ********" if verbo == "PASS" else linea
                print(f"[{self.id}] C: {visible}  (estado {self.estado})", flush=True)
                if verbo == "QUIT":
                    if self.estado == "TRANSACTION":
                        self.estado = "UPDATE"
                        borrados = self.actualizar()
                        self.ok(f"Adiós ({borrados} mensajes borrados)")
                    else:
                        self.ok("Adiós")
                    break
                if self.estado == "AUTHORIZATION":
                    self.autorizacion(verbo, arg)
                else:
                    self.transaccion(verbo, arg)
        finally:
            if self.estado != "AUTHORIZATION":
                bloqueo_buzon.release()


def atender_cliente(sock, direccion, args, contexto_tls, id_cliente):
    print(f"[{id_cliente}] -- conexión de {direccion[0]}:{direccion[1]}", flush=True)
    try:
        sock.settimeout(60)
        if contexto_tls:
            # TLS IMPLÍCITO: el apretón de manos TLS es lo primero
            sock = contexto_tls.wrap_socket(sock, server_side=True)
            print(f"[{id_cliente}] -- canal cifrado: {sock.version()}", flush=True)
        SesionPOP3(sock, id_cliente, args.buzon).atender()
    except (OSError, ssl.SSLError) as e:
        print(f"[{id_cliente}] -- error: {e}", flush=True)
    finally:
        sock.close()


def main():
    p = argparse.ArgumentParser(description="Servidor POP3 de prácticas")
    p.add_argument("--puerto", type=int, default=5995)
    p.add_argument("--buzon", required=True)
    p.add_argument("--cert")
    p.add_argument("--clave")
    args = p.parse_args()
    os.makedirs(args.buzon, exist_ok=True)

    contexto_tls = None
    if args.cert:
        contexto_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto_tls.load_cert_chain(args.cert, args.clave)

    servidor = socket.socket()
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("127.0.0.1", args.puerto))
    servidor.listen()
    print(f"POP3 falso escuchando en 127.0.0.1:{args.puerto}"
          f"{' con TLS implícito' if contexto_tls else ' EN CLARO'} - buzón {args.buzon}",
          flush=True)
    n = 0
    try:
        while True:
            sock, direccion = servidor.accept()
            n += 1
            threading.Thread(target=atender_cliente, daemon=True,
                             args=(sock, direccion, args, contexto_tls, f"pop{n}")).start()
    except KeyboardInterrupt:
        print("\nParado.")
    finally:
        servidor.close()


if __name__ == "__main__":
    sys.exit(main())
