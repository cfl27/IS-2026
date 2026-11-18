"""Simulador: servidor SMTP de juguete para probar los clientes sin Internet.

Qué hace: escucha en 127.0.0.1 y habla SMTP (RFC 5321) con quien se conecte,
guardando cada mensaje aceptado como un fichero .eml en un directorio
"buzón" (que luego sirve servidor_pop3_falso.py). Dos modos, como en el guion:
  - modo RELAY (por defecto): como relay.uniovi.es: HELO y a enviar, sin
    contraseña (ejercicios 7, 8 y 9).
  - modo SUBMISSION (--exigir-auth, con --cert): como smtp.gmail.com:587:
    anuncia STARTTLS, solo ofrece AUTH LOGIN ya cifrado y no deja hacer
    MAIL FROM sin autenticarse (ejercicios 11 y 12).
Imprime el diálogo (C: cliente, S: servidor) para verlo desde el otro lado.

Ejecución (normalmente lo lanza simuladores/lanzar_simuladores.sh):
    python3 simuladores/servidor_smtp_falso.py --puerto 2525 --buzon /tmp/buzon
    IS_SIM_USER=alumno@example.com IS_SIM_PASS=secreto \\
      python3 simuladores/servidor_smtp_falso.py --puerto 5587 --buzon /tmp/buzon \\
      --cert cert.pem --clave clave.pem --exigir-auth
  Las credenciales van por variables de entorno y no por argumentos: los
  argumentos de un proceso los ve cualquier usuario con `ps`.

Concepto: el lado SERVIDOR del protocolo. Lo que hay que notar al leerlo:
  - es una máquina de estados: no se acepta RCPT antes de MAIL, ni DATA
    antes de RCPT (503 "bad sequence of commands");
  - el SOBRE (MAIL FROM / RCPT TO) se guarda aparte del mensaje: un MTA real
    lo usa para entregar y lo apunta en las cabeceras Return-Path: y
    Received: que AÑADE al principio (lo que se ve en "Mostrar original");
  - STARTTLS: tras el 220 se envuelve el MISMO socket con TLS y se olvida
    todo lo anterior (hay que volver a hacer EHLO). Se vacía el buffer de
    lectura: aceptar órdenes que llegaron en claro "pegadas" al STARTTLS fue
    una vulnerabilidad real (CVE-2011-0411, inyección de órdenes STARTTLS);
  - DATA acaba en la línea "." y se deshace el dot-stuffing ("..x" -> ".x").
Simplificación: hay UN solo buzón para todos los destinatarios.
"""
import argparse
import base64
import email.utils
import os
import socket
import ssl
import sys
import threading
import time

NOMBRE = "smtp.simulador.local"
MAX_LINEA = 64 * 1024          # protección: no acumular líneas infinitas


class Conexion:
    """Socket + buffer para leer LÍNEAS (TCP entrega bytes, no líneas)."""

    def __init__(self, sock, id_cliente):
        self.sock, self.id, self.buffer = sock, id_cliente, b""

    def leer_linea(self):
        """Una línea sin el fin de línea, o None si el cliente cerró."""
        while b"\n" not in self.buffer:
            trozo = self.sock.recv(4096)
            if not trozo or len(self.buffer) > MAX_LINEA:
                return None
            self.buffer += trozo
        linea, self.buffer = self.buffer.split(b"\n", 1)
        return linea.rstrip(b"\r")       # admite CRLF y LF suelto

    def responder(self, texto):
        """Envía una respuesta (varias líneas = respuesta multilínea)."""
        lineas = texto.split("\n")
        # Multilínea: "250-..." en todas menos la última, que es "250 ..."
        datos = "".join(f"{l[:3]}-{l[4:]}\r\n" for l in lineas[:-1]) + lineas[-1] + "\r\n"
        for l in datos.rstrip().split("\r\n"):
            print(f"[{self.id}] S: {l}", flush=True)
        self.sock.sendall(datos.encode("utf-8"))


class SesionSMTP:
    """Estado de UNA conversación SMTP con un cliente."""

    def __init__(self, conexion, ip, args, contexto_tls):
        self.c, self.ip, self.args, self.tls = conexion, ip, args, contexto_tls
        self.cifrado = False
        self.autenticado = False
        self.reiniciar(olvidar_helo=True)

    def reiniciar(self, olvidar_helo=False):
        """Vacía el sobre (lo hacen RSET, un nuevo MAIL y el fin de DATA)."""
        if olvidar_helo:
            self.helo = None
        self.remitente, self.destinatarios = None, []

    # ------------------------------------------------------------ órdenes
    def orden_helo(self, verbo, argumento):
        if not argumento:
            return self.c.responder("501 5.5.4 Falta el nombre de la máquina")
        self.helo = argumento
        self.reiniciar()
        if verbo == "HELO":
            return self.c.responder(f"250 {NOMBRE} hola, {argumento}")
        # EHLO: lista de extensiones, una por línea
        lineas = [f"250 {NOMBRE} hola, {argumento} [{self.ip}]",
                  "250 8BITMIME", "250 SIZE 10485760"]
        if self.tls and not self.cifrado:
            lineas.append("250 STARTTLS")
        # AUTH solo por canal cifrado (o si este servidor no tiene TLS)
        if self.cifrado or not self.tls:
            lineas.append("250 AUTH LOGIN")
        lineas.append("250 HELP")
        self.c.responder("\n".join(lineas))

    def orden_starttls(self):
        if not self.tls:
            return self.c.responder("502 5.5.1 STARTTLS no disponible")
        if self.cifrado:
            return self.c.responder("503 5.5.1 Ya estamos en TLS")
        self.c.responder("220 2.0.0 Adelante, negociemos TLS")
        self.c.buffer = b""            # NADA de lo recibido en claro sigue valiendo
        self.c.sock = self.tls.wrap_socket(self.c.sock, server_side=True)
        self.cifrado = True
        self.reiniciar(olvidar_helo=True)   # RFC 3207: volver a empezar
        print(f"[{self.c.id}] -- canal cifrado: {self.c.sock.version()}", flush=True)

    def orden_auth(self, argumento):
        partes = argumento.split()
        if not partes or partes[0].upper() != "LOGIN":
            return self.c.responder("504 5.5.4 Solo AUTH LOGIN")
        if self.tls and not self.cifrado:
            return self.c.responder("530 5.7.0 Primero STARTTLS")
        # El servidor pide los datos en base64: "Username:" y "Password:".
        # smtplib manda el usuario ya en la orden ("respuesta inicial",
        # RFC 4954): AUTH LOGIN <usuario-b64>
        if len(partes) > 1:
            usuario_b64 = partes[1].encode()
        else:
            self.c.responder("334 " + base64.b64encode(b"Username:").decode())
            usuario_b64 = self.c.leer_linea() or b""
            print(f"[{self.c.id}] C: {usuario_b64.decode()}  (usuario en base64)", flush=True)
        self.c.responder("334 " + base64.b64encode(b"Password:").decode())
        clave_b64 = self.c.leer_linea() or b""
        print(f"[{self.c.id}] C: ********  (clave en base64, no se muestra)", flush=True)
        try:
            usuario = base64.b64decode(usuario_b64).decode()
            clave = base64.b64decode(clave_b64).decode()
        except (ValueError, UnicodeDecodeError):
            return self.c.responder("501 5.5.2 Base64 incorrecto")
        if usuario == os.getenv("IS_SIM_USER") and clave == os.getenv("IS_SIM_PASS"):
            self.autenticado = True
            return self.c.responder("235 2.7.0 Autenticado")
        # Mismo código que da Gmail con una clave mala
        self.c.responder("535 5.7.8 Usuario y contraseña no aceptados")

    def orden_mail(self, argumento):
        if not self.helo:
            return self.c.responder("503 5.5.1 Primero HELO/EHLO")
        if self.args.exigir_auth and not self.autenticado:
            return self.c.responder("530 5.7.0 Hace falta autenticarse")
        direccion = extraer_direccion(argumento, "FROM")
        if direccion is None:
            return self.c.responder("501 5.5.4 Sintaxis: MAIL FROM:<direccion>")
        self.reiniciar()
        self.remitente = direccion
        self.c.responder("250 2.1.0 Remitente OK")

    def orden_rcpt(self, argumento):
        if self.remitente is None:
            return self.c.responder("503 5.5.1 Primero MAIL FROM")
        direccion = extraer_direccion(argumento, "TO")
        if not direccion:
            return self.c.responder("501 5.5.4 Sintaxis: RCPT TO:<direccion>")
        self.destinatarios.append(direccion)
        self.c.responder("250 2.1.5 Destinatario OK")

    def orden_data(self):
        if not self.destinatarios:
            return self.c.responder("503 5.5.1 Primero RCPT TO")
        self.c.responder("354 Adelante; termina con <CRLF>.<CRLF>")
        lineas = []
        while True:
            linea = self.c.leer_linea()
            if linea is None:
                return                      # el cliente se fue a medias
            if linea == b".":               # fin de DATA
                break
            if linea.startswith(b".."):     # deshacer el dot-stuffing
                linea = linea[1:]
            lineas.append(linea)
        nombre = guardar(self, b"\r\n".join(lineas) + b"\r\n")
        print(f"[{self.c.id}] -- guardado {nombre} ({len(lineas)} líneas)", flush=True)
        self.reiniciar()
        self.c.responder(f"250 2.0.0 OK: en cola como {nombre}")

    # ------------------------------------------------------------ bucle
    def atender(self):
        self.c.responder(f"220 {NOMBRE} ESMTP simulador de prácticas")
        while True:
            linea = self.c.leer_linea()
            if linea is None:
                break
            texto = linea.decode("utf-8", "replace")
            verbo, _, argumento = texto.partition(" ")
            verbo = verbo.upper()
            print(f"[{self.c.id}] C: {texto}", flush=True)
            if verbo in ("HELO", "EHLO"):
                self.orden_helo(verbo, argumento.strip())
            elif verbo == "STARTTLS":
                self.orden_starttls()
            elif verbo == "AUTH":
                self.orden_auth(argumento)
            elif verbo == "MAIL":
                self.orden_mail(argumento)
            elif verbo == "RCPT":
                self.orden_rcpt(argumento)
            elif verbo == "DATA":
                self.orden_data()
            elif verbo == "RSET":
                self.reiniciar()
                self.c.responder("250 2.0.0 OK")
            elif verbo == "NOOP":
                self.c.responder("250 2.0.0 OK")
            elif verbo == "QUIT":
                self.c.responder(f"221 2.0.0 {NOMBRE} cierra la conexión")
                break
            else:
                self.c.responder("500 5.5.2 Orden no reconocida")


def extraer_direccion(argumento, palabra):
    """'FROM:<a@b>' -> 'a@b' (admite 'From: <a@b>' y espacios). '' = <> (rebote)."""
    cabeza, dos_puntos, resto = argumento.partition(":")
    if cabeza.strip().upper() != palabra or not dos_puntos:
        return None
    resto = resto.strip().split(" ")[0]       # ignora parámetros (SIZE=...)
    return resto.strip("<>")


contador_lock = threading.Lock()
contador = 0


def guardar(sesion, mensaje):
    """Guarda el mensaje en el buzón AÑADIENDO las cabeceras de un MTA real."""
    global contador
    with contador_lock:
        contador += 1
        # Milisegundos + contador: los nombres ordenan por llegada (POP3
        # numera los mensajes en ese orden)
        nombre = f"{int(time.time() * 1000)}-{os.getpid()}-{contador:04d}.eml"
    # "with ESMTPSA" = ESMTP + S (TLS) + A (autenticado), como en Gmail
    protocolo = ("ESMTP" if sesion.helo else "SMTP") + ("S" if sesion.cifrado else "") \
        + ("A" if sesion.autenticado else "")
    traza = (f"Return-Path: <{sesion.remitente}>\r\n"
             f"Delivered-To: {', '.join(sesion.destinatarios)}\r\n"
             f"Received: from {sesion.helo} ([{sesion.ip}])\r\n"
             f"\tby {NOMBRE} with {protocolo};\r\n"
             f"\t{email.utils.formatdate(localtime=True)}\r\n").encode()
    temporal = os.path.join(sesion.args.buzon, "." + nombre)
    with open(temporal, "wb") as f:
        f.write(traza + mensaje)
    # Escribir con otro nombre y renombrar es ATÓMICO: el servidor POP nunca
    # verá un mensaje a medio escribir (mismo truco que el formato Maildir)
    os.rename(temporal, os.path.join(sesion.args.buzon, nombre))
    return nombre


def atender_cliente(sock, direccion, args, contexto_tls, id_cliente):
    print(f"[{id_cliente}] -- conexión de {direccion[0]}:{direccion[1]}", flush=True)
    try:
        sock.settimeout(60)
        SesionSMTP(Conexion(sock, id_cliente), direccion[0], args, contexto_tls).atender()
    except (OSError, ssl.SSLError) as e:
        print(f"[{id_cliente}] -- error: {e}", flush=True)
    finally:
        sock.close()
        print(f"[{id_cliente}] -- fin", flush=True)


def main():
    p = argparse.ArgumentParser(description="Servidor SMTP de prácticas")
    p.add_argument("--puerto", type=int, default=2525)
    p.add_argument("--buzon", required=True, help="directorio donde guardar los .eml")
    p.add_argument("--cert", help="certificado PEM (activa STARTTLS)")
    p.add_argument("--clave", help="clave privada PEM del certificado")
    p.add_argument("--exigir-auth", action="store_true",
                   help="no aceptar MAIL FROM sin AUTH (como Gmail)")
    args = p.parse_args()
    os.makedirs(args.buzon, exist_ok=True)

    contexto_tls = None
    if args.cert:
        contexto_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto_tls.load_cert_chain(args.cert, args.clave)

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR: poder relanzarlo enseguida sin "Address already in use"
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Solo 127.0.0.1: un relay abierto a la red sería un regalo para spammers
    servidor.bind(("127.0.0.1", args.puerto))
    servidor.listen()
    modo = "SUBMISSION (STARTTLS + AUTH obligatoria)" if args.exigir_auth else "RELAY (sin AUTH)"
    print(f"SMTP falso escuchando en 127.0.0.1:{args.puerto} - modo {modo}"
          f"{' - STARTTLS disponible' if contexto_tls else ''}", flush=True)
    n = 0
    try:
        while True:
            sock, direccion = servidor.accept()
            n += 1
            # Un hilo por cliente: varios pueden hablar a la vez
            threading.Thread(target=atender_cliente, daemon=True,
                             args=(sock, direccion, args, contexto_tls, f"smtp{n}")).start()
    except KeyboardInterrupt:
        print("\nParado.")
    finally:
        servidor.close()


if __name__ == "__main__":
    sys.exit(main())
