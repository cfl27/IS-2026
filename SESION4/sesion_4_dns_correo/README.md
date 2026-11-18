# Sesión 4 – DNS y correo electrónico

**Parte 1, DNS:** herramientas `host`/`dig`/`nslookup`, resolución recursiva e
iterativa, dnspython y las API POSIX (`gethostbyname`, `getaddrinfo`).
**Parte 2, correo:** SMTP para enviar y POP3 para leer, primero con sockets en
crudo y después con `smtplib`/`poplib` y la biblioteca `email`.

No hay que instalar ningún servidor de correo ni usar `sudo`. Para probar el
correo sin Internet ni cuentas reales están los **simuladores** (`simuladores/`):
un servidor SMTP y otro POP3 de juguete, con TLS de verdad, que también sirven
para estudiar el protocolo desde el lado del servidor.

Para la defensa: [CHULETA_DEFENSA.md](CHULETA_DEFENSA.md) (teoría y preguntas tipo examen).

## Ficheros

```
sesion_4_dns_correo/
├── README.md                    este fichero
├── CHULETA_DEFENSA.md           teoría resumida + preguntas tipo examen
├── comun.py                     servidor/puerto/direcciones/credenciales desde variables de entorno
├── probar_sesion4.sh            batería automática (52 comprobaciones)
├── dns/
│   ├── dns_herramientas.sh        ej. 1-2: host, dig y nslookup contra 3 servidores
│   ├── dns_iterativo.sh           ej. 3: dig +norecurse paso a paso (raíz -> org -> wikipedia.org)
│   ├── dns_iterativo.py           ej. 3: el mismo recorrido con dnspython (glue, CNAME, reintentos)
│   ├── dns_ej1.py                 ej. 4: resolve(), respuesta en texto y en binario (to_wire)
│   ├── dns_ips_apple.py           ej. 5: todas las IP de apple.com
│   ├── dns_gethostbyname.py       experimento: la tupla de gethostbyname_ex()
│   ├── dns_getaddrinfo_experimento.py  experimento: los 5 campos de cada elemento de getaddrinfo()
│   ├── dns_getaddrinfo_wikipedia.py    ej. 6 (opcional): HTTP por IPv4 con getaddrinfo, intento por IPv6
│   ├── dns_mx_gmail.py            ej. 10: MX de gmail.com por prioridad, con su IP
│   └── dns_mx_spf_uniovi.py       experimentos MX/SPF/TXT/DMARC de uniovi.es
├── correo/
│   ├── smtp/
│   │   ├── email_envia_crudo.py         ej. 7: HELO/MAIL/RCPT/DATA/QUIT con la plantilla del guion
│   │   ├── email_envia_crudo_rfc5322.py ej. 8 y 9: mismo diálogo, mensaje con EmailMessage (+ adjunto)
│   │   ├── email_envia_crudo_ssl.py     ej. 11: EHLO, STARTTLS, wrap_socket, AUTH LOGIN (Gmail)
│   │   └── email_smtplib.py             ej. 12: smtplib (starttls, login, sendmail)
│   ├── pop3/
│   │   ├── email_pop3_recibe_crudo.py   ej. 13: USER/PASS/STAT/RETR 1 con TLS implícito
│   │   ├── email_pop3_recibe_crudo2.py  ej. 14: Subject y From de todos
│   │   ├── email_pop3_poplib.py         ej. 15: poplib.POP3_SSL, retr() tal cual
│   │   └── email_pop3_poplib2.py        ej. 16: imprime_resumen_mensaje() del guion (+ --mejorada)
│   └── mensajes/
│       ├── email_crear_mensaje_prueba.py  3.1.2: el código del guion, --tildes, --adjunto (ej. 9)
│       ├── mensajes.py                    construir_mensaje(), CRLF, dot-stuffing, logo del ej. 9
│       └── email_decodificar.py           analiza un .eml: cabeceras codificadas/decodificadas y árbol MIME
└── simuladores/
    ├── servidor_smtp_falso.py     SMTP: modo relay (sin AUTH) o de envío (STARTTLS + AUTH LOGIN)
    ├── servidor_pop3_falso.py     POP3 con TLS implícito: USER PASS STAT LIST RETR TOP DELE RSET UIDL QUIT
    ├── generar_certificado.sh     certificado autofirmado para localhost (openssl)
    └── lanzar_simuladores.sh      lanza los tres servidores y escribe entorno.sh para los clientes
```

Los scripts de las subcarpetas importan `comun.py` (y `correo/mensajes/mensajes.py`)
añadiendo su carpeta a `sys.path`, así que funcionan desde cualquier directorio.
Los comandos de abajo se escriben desde `PL4/sesion_4_dns_correo/`.

## Requisitos y preparación

- `dig`, `host` y `nslookup` (paquete `dnsutils`), `openssl` y Python 3 (probado con 3.12).
- **dnspython** en un entorno virtual (como en el guion; `probar_sesion4.sh` lo crea si falta):

  ```bash
  python3 -m venv ~/dnsenv
  ~/dnsenv/bin/pip install dnspython        # probado con dnspython 2.9
  ```

  Los scripts de DNS con dnspython se lanzan con `~/dnsenv/bin/python` (o `source ~/dnsenv/bin/activate`).
  Todos los de correo y los de las API POSIX usan solo la biblioteca estándar (`python3`).

## Cómo ejecutar

### Pruebas automáticas

```bash
bash ./probar_sesion4.sh      # unos 35 s; termina con "Resultado: N correctas, 0 con fallo, M omitidas"
```

Lanza los simuladores en puertos de prueba con una clave aleatoria, ejecuta **todos**
los clientes de correo contra ellos y mira lo que llega al buzón: sobre y cabeceras,
tildes codificadas, adjunto, TLS y AUTH, STAT/LIST/TOP/DELE/RSET/UPDATE y bloqueo
del buzón. Prueba también los errores: clave mala, falta de AUTH, certificado que no
es de confianza y puerto cerrado. En todos debe salir un mensaje claro y ningún traceback.
Al terminar los para y borra sus temporales. Las pruebas de DNS necesitan Internet:
si no hay red, o si 156.35.41.4 no responde, salen como **OMITIDO** y no cuentan como fallo.

### DNS

```bash
bash dns/dns_herramientas.sh | less             # ej. 1 y 2
bash dns/dns_iterativo.sh                       # ej. 3 a mano (dig +norecurse)
~/dnsenv/bin/python dns/dns_iterativo.py        # ej. 3 automático (prueba también: www.uniovi.es)
~/dnsenv/bin/python dns/dns_ej1.py              # ej. 4
~/dnsenv/bin/python dns/dns_ips_apple.py        # ej. 5
python3 dns/dns_gethostbyname.py                # gethostbyname_ex
python3 dns/dns_getaddrinfo_experimento.py      # getaddrinfo
python3 dns/dns_getaddrinfo_wikipedia.py        # ej. 6
~/dnsenv/bin/python dns/dns_mx_gmail.py         # ej. 10
~/dnsenv/bin/python dns/dns_mx_spf_uniovi.py    # MX, SPF y DMARC de uniovi.es
dig uniovi.es MX ; dig uniovi.es TXT            # los experimentos del guion con dig
```

### Correo contra los simuladores (sin Internet)

```bash
# Terminal 1: deja los servidores en marcha (Ctrl+C para pararlos)
bash simuladores/lanzar_simuladores.sh            # usa /tmp/is_s4_sim

# Terminal 2
source /tmp/is_s4_sim/entorno.sh                  # SSL_CERT_FILE, IS_SMTP_*, IS_POP_*, IS_USER/IS_PASS...
IS_SMTP_PORT=2525 python3 correo/smtp/email_envia_crudo.py             # ej. 7 (relay sin AUTH)
IS_SMTP_PORT=2525 python3 correo/smtp/email_envia_crudo_rfc5322.py --tildes --adjunto   # ej. 8-9
python3 correo/smtp/email_envia_crudo_ssl.py                           # ej. 11 (puerto 5587)
python3 correo/smtp/email_smtplib.py                                   # ej. 12
python3 correo/pop3/email_pop3_recibe_crudo2.py                        # ej. 14 (puerto 5995)
python3 correo/pop3/email_pop3_poplib2.py                              # ej. 16
python3 correo/mensajes/email_decodificar.py /tmp/is_s4_sim/buzon/*.eml | less
tail -f /tmp/is_s4_sim/smtp_submission.log       # el diálogo visto desde el servidor
```

| Simulador | Puerto | Imita a | Qué exige |
|---|---|---|---|
| SMTP relay | 2525 | `relay.uniovi.es:25` | nada (HELO y a enviar) |
| SMTP envío | 5587 | `smtp.gmail.com:587` | STARTTLS y AUTH LOGIN antes de MAIL FROM |
| POP3 | 5995 | `pop.gmail.com:995` | TLS implícito, USER/PASS |

Los puertos son mayores que 1024 para no necesitar root. Los tres comparten un buzón
(`/tmp/is_s4_sim/buzon/*.eml`): lo que se envía por SMTP se lee luego por POP3.

**El truco del certificado.** Los simuladores usan un certificado autofirmado para
`localhost` (`generar_certificado.sh`). Un cliente bien hecho lo rechaza:
`CERTIFICATE_VERIFY_FAILED`, y eso es lo correcto. En lugar de desactivar la
verificación en los clientes, `entorno.sh` exporta `SSL_CERT_FILE=/tmp/is_s4_sim/cert.pem`.
`ssl.create_default_context()` carga las CA "por defecto" y OpenSSL toma esa variable
como el fichero de CA de confianza. Así los mismos clientes, **sin cambiar ni una línea**,
verifican el nombre y la firma de verdad y aceptan solo ese certificado.

### Variables de entorno de los clientes de correo (ver `comun.py`)

| Variable | Para qué | Si no está |
|---|---|---|
| `IS_SMTP_SERVER`, `IS_SMTP_PORT` | servidor SMTP | el del guion: `relay.uniovi.es:25` (ej. 7-9) o `smtp.gmail.com:587` (ej. 11-12) |
| `IS_POP_SERVER`, `IS_POP_PORT` | servidor POP3 | `pop.gmail.com:995` |
| `IS_FROM`, `IS_TO` | remitente y destinatario(s) del sobre (`IS_TO` admite varios separados por comas) | se preguntan |
| `IS_USER`, `IS_PASS` | usuario y contraseña | se preguntan (la clave con `getpass`, sin eco) |

En el código no hay ni contraseñas ni direcciones reales: los ejemplos usan `example.com`.

## Ejercicios, ficheros y conceptos

| Ej. | Fichero | Concepto |
|---|---|---|
| 1, 2 | `dns/dns_herramientas.sh` | host (concisa) / dig (secciones del mensaje) / nslookup; elegir el servidor (`@8.8.8.8`) |
| 3 | `dns/dns_iterativo.sh`, `dns/dns_iterativo.py` | recursivo vs iterativo (`rd`), referencias en AUTHORITY, glue en ADDITIONAL, `aa` |
| 4 | `dns/dns_ej1.py` | dnspython: `resolve()` (`query()` está obsoleto), mensaje binario `to_wire()` |
| 5 | `dns/dns_ips_apple.py` | RRset: varios A para un nombre |
| (2.3.2) | `dns/dns_gethostbyname.py` | API POSIX clásica: (canónico, alias, IPs) |
| (2.4) | `dns/dns_getaddrinfo_experimento.py` | getaddrinfo: (familia, tipo, proto, canonname, sockaddr) |
| 6 | `dns/dns_getaddrinfo_wikipedia.py` | conectar sin IP ni puerto en el código; cabecera Host; 301 a HTTPS; IPv6 |
| 7 | `correo/smtp/email_envia_crudo.py` | diálogo SMTP y códigos 220/250/354/221; `\r\n\r\n` y `\r\n.\r\n` |
| (3.1.2) | `correo/mensajes/email_crear_mensaje_prueba.py` | RFC 5322 + MIME; tildes: RFC 2047, quoted-printable, base64 |
| 8 | `correo/smtp/email_envia_crudo_rfc5322.py` | `as_bytes()` con CRLF + dot-stuffing + punto final |
| 9 | `email_crear_mensaje_prueba.py --adjunto`, `email_envia_crudo_rfc5322.py --adjunto` | multipart/mixed, boundary, adjunto en base64 |
| 10 | `dns/dns_mx_gmail.py` | MX: `preference` y `exchange` |
| (3.1.4) | `dns/dns_mx_spf_uniovi.py` | SPF (`mx`, `a:`, `include:`, `ip4:`, `-all`), DKIM, DMARC |
| 11 | `correo/smtp/email_envia_crudo_ssl.py` | EHLO, STARTTLS, `wrap_socket`, AUTH LOGIN 334/334/235; base64 no cifra |
| 12 | `correo/smtp/email_smtplib.py` | smtplib; sobre vs mensaje en `sendmail()` |
| 13 | `correo/pop3/email_pop3_recibe_crudo.py` | POP3 en crudo, TLS implícito, `+OK`/`-ERR`, lectura hasta `\r\n.\r\n` |
| 14 | `correo/pop3/email_pop3_recibe_crudo2.py` | numeración 1..N de la sesión |
| 15 | `correo/pop3/email_pop3_poplib.py` | `retr()` = (respuesta, líneas, octetos) |
| 16 | `correo/pop3/email_pop3_poplib2.py` | `decode_header`/`make_header`, multipart |
| – | `simuladores/*` | el lado servidor: máquinas de estados SMTP y POP3, STARTTLS, UPDATE |

## Respuestas a las preguntas del guion

Los valores son de una ejecución de noviembre de 2026 desde WSL. Las IP cambian
según el momento y el lugar desde el que se pregunta.

**Ej. 1. ¿Cuál es más concisa?** `host`: una línea por registro
(`www.uniovi.es is an alias for crisb101.sic233.uniovi.es.` / `... has address 156.35.233.101`).
**¿Cuál está más próxima al protocolo?** `dig`. Enseña el mensaje DNS tal como es:
la cabecera con `id`, `opcode`, `status` y los flags `qr rd ra aa`, y las secciones
QUESTION, ANSWER, AUTHORITY y ADDITIONAL con TTL, clase y tipo de cada registro.
Por eso `dig` es la herramienta de diagnóstico. `nslookup` (obsoleta) queda en medio.

**en.wikipedia.org frente a es.wikipedia.org.** Los dos son **alias (CNAME) del mismo
nombre canónico**, `dyna.wikimedia.org`, y por tanto dan la misma IP (185.15.58.224 en esta
prueba). Conclusión: todas las Wikipedias las sirven las mismas máquinas, y el idioma no
se distingue por la IP sino por el nombre que pide el navegador.

**¿Qué sale si en el navegador se pone la IP?** No sale Wikipedia:
- `http://185.15.58.224/` devuelve **301** a `https://185.15.58.224/`, porque Wikipedia solo sirve por HTTPS.
- Por HTTPS el navegador avisa de que el **certificado no es válido**: es de `*.wikipedia.org`
  y no de esa IP (`curl` da el error 60). Si se acepta igualmente, el servidor responde **400 Bad Request**.

El motivo es el **virtual hosting**: una IP atiende miles de sitios. En HTTP el sitio se
elige con la cabecera `Host:` y en TLS con el **SNI**, el nombre que el cliente manda en el
saludo TLS para que el servidor elija el certificado. Con una IP no hay ni Host ni SNI con
nombre de sitio, y el servidor no sabe qué sitio servir.

**Ej. 2. Otros servidores.** El de `/etc/resolv.conf` en WSL es 10.255.255.254: un
reenviador de Windows. Responde igual que 8.8.8.8, salvo los TTL, que van bajando en cada
caché por separado. 156.35.41.4 respondió en esta prueba para `www.uniovi.es` con
flags `qr aa rd` **sin `ra`**: contesta como **autoridad** de uniovi.es, pero no ofrece
recursión desde fuera. Para `en.wikipedia.org` da `status: REFUSED`. Desde fuera de la
red de Uniovi puede no responder nada: es normal y el script lo indica.

**Ej. 3.** `dig @8.8.8.8 +norecurse en.wikipedia.org` a veces devuelve la IP sin que
Google sea autoridad: la saca de su **caché**, con flag `ra` y sin `aa`. Otras veces viene
vacía, porque los muchos servidores que hay tras 8.8.8.8 no comparten caché. Contra
156.35.41.4 nunca aparece: no es autoridad de wikipedia.org y no hace recursión para
nosotros. El recorrido a mano (`dns_iterativo.sh`) es:

| Salto | Se pregunta a | Respuesta |
|---|---|---|
| 1 | 8.8.8.8 por `.` NS | `a.root-servers.net.` ... → A: 198.41.0.4 |
| 2 | 198.41.0.4 (raíz) | referencia: zona `org.` → `v0n0.pir-ns.org.` con glue 199.19.56.1 |
| 3 | 199.19.56.1 (org) | referencia: zona `wikipedia.org.` → `ns0/ns1/ns2.wikimedia.org.` con glue (ns0 = 208.80.154.238) |
| 4 | 208.80.154.238 (wikipedia) | `aa`: `en.wikipedia.org CNAME dyna.wikimedia.org`, y su A **185.15.58.224** |

**Comparación con `host`.** Coinciden casi siempre. Si no, no es un error: Wikimedia usa
**GeoDNS** y el autoritativo contesta según quién le pregunta. En la resolución iterativa
pregunta esta máquina; con `host` pregunta el resolvedor del sistema, que sale a Internet
por otro sitio. En una de las pruebas salió 208.80.153.224 con `host` y 185.15.58.224 de
forma iterativa, y los scripts lo explican cuando pasa.

**gethostbyname_ex.** `('apple.com', [], ['17.253.144.10'])` y
`('crisb101.sic233.uniovi.es', ['www.uniovi.es'], ['156.35.233.101'])`. Es decir:
(nombre **canónico**, lista de **alias** seguidos para llegar a él, lista de **IPv4**).
apple.com no tiene alias; www.uniovi.es es un CNAME.

**getaddrinfo("en.wikipedia.org", "www").** Salen **2 elementos**: el primero
`(AF_INET, SOCK_STREAM, 6, '', ('185.15.58.224', 80))` y el segundo, IPv6,
`(AF_INET6, SOCK_STREAM, 6, '', ('2a02:ec80:600:ed1a::1', 80, 0, 0))`. Solo hay TCP porque
el servicio "www" (= http, 80/tcp) solo existe en TCP; con otros servicios salen también
UDP y RAW. `canonname` sale vacío salvo que se pida `AI_CANONNAME`. **Ej. 6:** por IPv4
se recibe `HTTP/1.1 301 Moved Permanently` con `location: https://en.wikipedia.org/`. Por
IPv6, `[Errno 101] Network is unreachable`: el DNS devuelve el AAAA, pero la máquina no
tiene conectividad IPv6.

**3.1.4. ¿Cómo localiza el MTA el destino?** Mira el dominio que va tras la `@` del
destinatario del **sobre** (RCPT TO) y le pide al DNS sus registros **MX**. Prueba los
servidores por orden de `preference`, del número **menor** (más prioritario) al mayor; si
hay empate, elige al azar para repartir carga. Del MX saca un nombre y resuelve su A/AAAA.
Si ningún MX responde, o devuelve un error **4xx** temporal, el mensaje se queda en la
**cola** y se reintenta cada cierto tiempo, unos 5 días. Si no hay MX, se usa el A del
propio dominio. `dig uniovi.es MX` devuelve hoy:

```
uniovi.es.  IN MX  10 mxa-006a4e02.gslb.pphosted.com.
uniovi.es.  IN MX  10 mxb-006a4e02.gslb.pphosted.com.
```

Son dos MX de **igual prioridad**, así que se reparten al azar, y los dos son de
**Proofpoint** (pphosted.com), una pasarela antispam que recibe el correo antes de pasarlo
a Microsoft 365. **Ej. 10:** `5 gmail-smtp-in.l.google.com.` y luego `alt1`…`alt4` con
10, 20, 30 y 40, como en el guion (las IP cambian).

**SPF de uniovi.es** (`dig uniovi.es TXT`):
`v=spf1 mx a:relay.uniovi.es include:spf.protection.outlook.com ip4:156.35.11.151 ip4:156.35.11.35 -all`.
IPs autorizadas, por ejemplo: **156.35.11.7** (`a:relay.uniovi.es`), **156.35.11.151**
(`ip4:`) y la red **40.92.0.0/15** de **Microsoft**, que sale al seguir `include:` hasta el
SPF de `spf.protection.outlook.com`. `-all` rechaza todas las demás. uniovi.es **no
publica DMARC** (`_dmarc.uniovi.es` no existe).

**Experimento "Mostrar original" (ej. 8).** Cada MTA añade arriba su cabecera
`Received: from <HELO> (<nombre> [IP]) by <él> with ESMTP(S)(A); fecha`. Leídas de abajo
arriba cuentan el camino del mensaje, y la de más abajo tiene **tu IP de origen**. Gmail
añade además `Authentication-Results:` con el resultado de SPF, DKIM y DMARC.
El simulador hace lo mismo: mira `Return-Path:` y `Received:` en los `.eml` del buzón.

**Experimento del remitente falso (ej. 11), solo documentado.** No se ha ejecutado
contra Gmail en esta sesión; esto es lo que cabe esperar según cómo funciona Gmail. Si con
`smtp.gmail.com` autenticado se pone `MAIL FROM:<anonimo@example.com>` y `From: anonimo@example.com`,
Gmail **no** deja enviar como otra persona. Reescribe el remitente del sobre y la
cabecera `From:` con **tu cuenta**, salvo que esa dirección esté configurada como alias
verificado ("Enviar como"). En el destino llega con tu dirección; el texto falso puede
quedar como nombre visible y en `Return-Path`/`X-Google-Original-From`. Por `relay.uniovi.es`,
que no autentica, la cabecera falsa sí llega tal cual. El MTA de destino puede
detectarlo: el SPF de example.com no autoriza la IP de Uniovi, no hay firma DKIM del
dominio falso y DMARC falla. Por eso suele acabar en spam o rechazado. Por eso
existen SPF, DKIM y DMARC, y por eso Uniovi solo acepta en el relay conexiones internas.

## Pasos manuales (necesitan servidores reales)

Esto no lo ejecuta `probar_sesion4.sh`. Pon tus datos en las variables al ejecutar, no
en los ficheros.

1. **Contraseña de aplicación de Gmail** (sirve para SMTP y POP3):
   1. Activa la verificación en dos pasos en tu cuenta de Google.
   2. Entra en <https://myaccount.google.com/apppasswords>, ponle un nombre
      (p. ej. "Practicas Ingenieria Servicios") y copia la clave de 16 letras. **Solo se muestra una vez.**
   3. Bórrala al acabar el curso.
2. **Activar POP en Gmail:** Ajustes → Ver todos los ajustes → *Reenvío y correo
   POP/IMAP* → Habilitar POP. Envíate antes algunos correos: POP solo ve los mensajes
   que aún no se han descargado.
3. **Ejercicios 7–9, desde la red de Uniovi** (aula, o la VPN si te deja salir al puerto
   25). Fuera de ella, `relay.uniovi.es` no acepta la conexión y el script lo explica:

   ```bash
   read -p "Tu correo uniovi: " U; export IS_FROM=$U IS_TO=$U
   python3 correo/smtp/email_envia_crudo.py
   python3 correo/smtp/email_envia_crudo_rfc5322.py --tildes
   python3 correo/smtp/email_envia_crudo_rfc5322.py --adjunto     # ej. 9 (descarga logoatc.gif con wget)
   ```
4. **Ejercicios 11–16 con Gmail** (desde cualquier red):

   ```bash
   read -p "Tu Gmail: " G; export IS_FROM=$G IS_TO=$G IS_USER=$G
   python3 correo/smtp/email_envia_crudo_ssl.py      # pide la contraseña de aplicación
   python3 correo/smtp/email_smtplib.py
   python3 correo/pop3/email_pop3_recibe_crudo.py
   python3 correo/pop3/email_pop3_recibe_crudo2.py
   python3 correo/pop3/email_pop3_poplib.py
   python3 correo/pop3/email_pop3_poplib2.py
   ```

   Para no teclear la clave cada vez: `read -s IS_PASS; export IS_PASS`. Así no queda en el historial.
   Si el correo llega a spam, es lo esperado para un mensaje generado a mano.

## Decisiones tomadas (no estaban fijadas en el guion)

- **dnspython 2.x:** `dns.resolver.resolve()` en lugar de `query()`, que está obsoleto
  (ver la cabecera de `dns_ej1.py`).
- **Ej. 3:** se pregunta siempre el nombre **completo** (`en.wikipedia.org`) a cada nivel,
  como hace un resolvedor real. La referencia que devuelve la raíz es la misma que si se
  pregunta por `org`. Si 8.8.8.8 no contesta a `. NS` sin recursión, se repite con
  recursión; si tampoco responde, se usa la IP fija de `a.root-servers.net`. La versión en
  Python prueba otra raíz u otro NS cuando uno no responde, usa EDNS y repite por TCP si
  la respuesta llega truncada.
- **`RecvReply`** lee en bloques de 1024 bytes, como dice el guion, pero **hasta tener la
  respuesta completa**: TCP puede partir una respuesta, y la de EHLO es multilínea.
- **Ej. 7:** se deja la plantilla del guion tal cual, con sus `\n` sueltos, y se explica
  en el código. Desde el ej. 8 se usa `as_bytes(policy=email.policy.SMTP)`, que pone
  **CRLF** (`as_bytes()` a secas usa `\n`), y se hace dot-stuffing.
- **Ej. 8:** fichero aparte, `email_envia_crudo_rfc5322.py`, para conservar el 7 intacto.
  El 9 es la opción `--adjunto` de ese fichero y de `email_crear_mensaje_prueba.py`.
- **Ej. 9:** el adjunto es `logoatc.gif`. Si ya existe en `/tmp` se reutiliza; si no, se
  descarga con el `wget` del guion; y si no hay red, se genera un GIF de 1×1 píxel
  (43 bytes). Con `IS_SIN_RED=1` no se intenta la descarga (lo usan las pruebas).
- **Ej. 11:** se repite EHLO tras STARTTLS (lo exige el RFC 3207, aunque el guion no lo
  dice) y el mensaje se construye como en el ej. 8.
- **Ej. 12 y 15:** se pasa `context=ssl.create_default_context()` a `starttls()` y a
  `POP3_SSL`. Sin él, smtplib y poplib **no verifican el certificado**.
- **Ej. 15:** se mantiene `set_debuglevel(2)`, pero se baja a 0 solo durante `pass_()`,
  porque si no poplib imprime la contraseña.
- **Ej. 16:** la función del guion se copia sin cambios, con el `import email.header` que
  le falta. `--mejorada` usa la API moderna, que además decodifica bien cuerpos en base64
  o quoted-printable.
- **`IS_TO`** admite varios destinatarios separados por comas (un `RCPT TO` por cada uno).
- **Simuladores:** escuchan solo en 127.0.0.1 y en puertos altos. Las credenciales
  llegan por variables de entorno, no por argumentos, porque los argumentos se ven con
  `ps`. Hay un solo buzón para todos los destinatarios.

## Seguridad

- En los ficheros no hay ni contraseñas ni direcciones reales (`example.com` en los ejemplos).
- `AUTH LOGIN` usa base64, que **no es cifrado**: solo es seguro dentro de TLS. Por eso
  `email_envia_crudo_ssl.py` se niega a seguir si el servidor no anuncia STARTTLS.
- La contraseña de aplicación da acceso completo al correo: no la compartas y bórrala al acabar.
