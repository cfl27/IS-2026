# Chuleta para la defensa – Sesión 4: DNS y correo electrónico

Resumen de la teoría que hay detrás de cada ejercicio, con el fichero donde se ve.
Al final, preguntas tipo examen con respuesta breve.

---

## 1. DNS

### Jerarquía

```
                         .  (raíz: 13 nombres a..m.root-servers.net, cientos de réplicas anycast)
             ┌───────────┼────────────┐
            org         es           com          <- TLD (dominios de primer nivel)
             │           │
        wikipedia     uniovi                       <- zonas de segundo nivel (delegadas)
             │           │
            en          www                        <- nombres dentro de la zona
```

- Cada **zona** tiene sus servidores **autoritativos** (registros NS). La zona padre
  **delega** en la hija publicando los NS de la hija y, si hace falta, sus IP (glue).
- Ningún servidor lo sabe todo: la raíz solo sabe quién lleva cada TLD y el TLD solo
  sabe quién lleva cada dominio.

### Recursiva vs iterativa (`dns/dns_iterativo.*`)

| | Recursiva | Iterativa |
|---|---|---|
| Flag en la consulta | `rd` = 1 (recursion desired) | `rd` = 0 (`dig +norecurse`) |
| Quién trabaja | el **servidor** (resolvedor) persigue la respuesta | el **cliente** sigue las referencias |
| Qué devuelve | la respuesta final (o error) | lo que sabe: respuesta si es autoridad, si no una **referencia** (NS en AUTHORITY) |
| Quién la usa | tu PC → el DNS de tu red / 8.8.8.8 | el resolvedor recursivo → raíz, TLD, autoritativos |

Lo normal es una mezcla. El *stub resolver* del PC pregunta en **recursivo** a un
resolvedor, y el resolvedor pregunta en **iterativo** a raíz → TLD → autoritativo.

### Registros

| Tipo | Contiene | Ejemplo |
|---|---|---|
| A | IPv4 | `dyna.wikimedia.org A 185.15.58.224` |
| AAAA | IPv6 | `dyna.wikimedia.org AAAA 2a02:ec80:600:ed1a::1` |
| CNAME | alias → nombre canónico | `en.wikipedia.org CNAME dyna.wikimedia.org` |
| NS | servidor autoritativo de una zona | `wikipedia.org NS ns0.wikimedia.org` |
| MX | servidor de correo + prioridad | `gmail.com MX 5 gmail-smtp-in.l.google.com` |
| TXT | texto libre: SPF, DKIM, DMARC, verificaciones | `uniovi.es TXT "v=spf1 ... -all"` |
| PTR | inversa: IP → nombre (en `in-addr.arpa`) | `dig -x 156.35.233.101` |
| SOA | datos de la zona (serie, TTL negativo...) | |

### Cómo leer `dig`

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 11066
;; flags: qr aa rd; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1
```

- `id`: casa cada respuesta con su pregunta. Hace falta porque va por **UDP**, que no
  tiene conexiones. Si el id es predecible, un atacante puede colar respuestas falsas
  (envenenamiento de caché).
- `status`: `NOERROR`; `NXDOMAIN` (el nombre no existe); `REFUSED` (no te quiere
  responder, p. ej. 156.35.41.4 para nombres ajenos); `SERVFAIL`.
- Flags: `qr` = es una respuesta; `aa` = respuesta **autoritativa**; `rd` = se pidió
  recursión; `ra` = el servidor la ofrece; `tc` = respuesta truncada (se repite por TCP).
- Secciones: QUESTION (lo preguntado), ANSWER (la respuesta), AUTHORITY (NS de la zona:
  las referencias), ADDITIONAL (IP de esos NS = glue, y el pseudo-registro OPT de EDNS).
- Cada registro: `nombre TTL clase tipo dato`. El **TTL** son los segundos que puede
  guardarse en caché.
- Epílogo: tiempo de consulta, SERVER (IP#53), fecha y tamaño del mensaje.

### Caché y TTL

Cada resolvedor guarda las respuestas durante su TTL. Por eso 8.8.8.8 puede contestar a
un `+norecurse` (lo tiene en caché, con `ra` y sin `aa`) y por eso un cambio de DNS tarda
en "propagarse" (hay que esperar a que caduquen las cachés). También se guardan las
respuestas negativas (NXDOMAIN), con el TTL que marca el SOA.

### Glue records

La zona `org` delega `wikipedia.org` en `ns0.wikimedia.org`. Si el NS de una zona está
*dentro* de esa misma zona (p. ej. `ns.ejemplo.org` para `ejemplo.org`), para saber su IP
habría que preguntarle a él: un círculo. La zona padre lo rompe publicando también su
A/AAAA en ADDITIONAL: eso es el **glue**. Si el NS está en otra zona
(`a2.org.afilias-nst.info`), no hay glue y se resuelve aparte (`dns_iterativo.py` lo hace).

### UDP y TCP, puerto 53

Las consultas van por UDP: un datagrama de ida y otro de vuelta, sin conexión. Sin EDNS
caben 512 bytes; con EDNS, unos 1232. Si la respuesta no cabe, el servidor marca `tc` y
el cliente repite la consulta por **TCP**. Las transferencias de zona también van por TCP.

### API de programación

| API | Qué hace | Limitación |
|---|---|---|
| `gethostbyname(n)` | una IPv4 | solo una, solo IPv4 |
| `gethostbyname_ex(n)` | (canónico, alias, IPs) | solo IPv4 |
| `getaddrinfo(n, servicio)` | lista de (familia, tipo, proto, canonname, sockaddr) | ninguna: es la moderna, IPv4/IPv6 |
| dnspython | cualquier tipo de registro (MX, TXT, NS...), elegir servidor, flags | dependencia externa |

Las tres primeras usan el resolvedor de libc: `/etc/hosts`, luego el DNS de
`/etc/resolv.conf`, en el orden que marca `/etc/nsswitch.conf`.

### Virtual hosting (ej. 1)

Una IP aloja muchos sitios. HTTP elige el sitio por la cabecera `Host:` y TLS por el
**SNI** (el nombre que va en el ClientHello). Entrando por IP no hay ni una cosa ni la otra:
Wikipedia contesta con un 301, luego da un error de certificado y al final un 400.

---

## 2. SMTP (envío)

### Arquitectura

```
 MUA (cliente)  --SMTP 587 + AUTH-->  MSA/MTA de tu proveedor  --SMTP 25-->  MTA destino --> buzón
 (Thunderbird,                        (smtp.gmail.com,             (busca el MX     (gmail-smtp-in...)   |
  email_smtplib.py)                    relay.uniovi.es)             del dominio)                         |
                                                                                    MUA <--POP3 995 / IMAP 993--+
```

SMTP solo **envía** (y entre servidores también **retransmite**). Para leer el buzón
están POP3 e IMAP.

### Diálogo completo (`correo/smtp/email_envia_crudo.py`)

```
C: (conecta TCP al 25 / 587)
S: 220 smtp.ejemplo.org ESMTP listo                 <- saludo
C: EHLO mipc                                          (HELO en el SMTP clásico)
S: 250-smtp.ejemplo.org hola
S: 250-8BITMIME
S: 250-STARTTLS                                     <- multilínea: "250-" ... "250 "
S: 250 SIZE 35882577
C: STARTTLS                                       ┐
S: 220 Adelante                                   │ solo en 587/25 con TLS
   ====== negociación TLS (wrap_socket) ======    │
C: EHLO mipc                                      │ (otra vez: se olvida lo anterior)
S: 250-... 250 AUTH LOGIN PLAIN                   │
C: AUTH LOGIN                                     │
S: 334 VXNlcm5hbWU6          ("Username:")        │
C: dXN1YXJpbw==              (usuario en base64)  │
S: 334 UGFzc3dvcmQ6          ("Password:")        │
C: Y2xhdmU=                  (clave en base64)    │
S: 235 2.7.0 Accepted                             ┘
C: MAIL FROM:<yo@ejemplo.org>                       <- sobre: remitente
S: 250 OK
C: RCPT TO:<tu@ejemplo.com>                         <- sobre: destinatario (se repite)
S: 250 OK
C: DATA
S: 354 End data with <CR><LF>.<CR><LF>
C: From: ... To: ... Subject: ...                   <- cabeceras (RFC 5322)
C:                                                  <- línea en blanco (\r\n\r\n)
C: cuerpo...
C: .                                                <- fin (\r\n.\r\n)
S: 250 OK queued as 12345
C: QUIT
S: 221 Bye
```

### Códigos

| Código | Significado | Código | Significado |
|---|---|---|---|
| 220 | servicio listo (saludo; y respuesta a STARTTLS) | 334 | AUTH: continúa (pide el siguiente dato) |
| 221 | cierro la conexión | 421 | servicio no disponible (temporal) |
| 235 | autenticado | 450/451 | error temporal: reintenta |
| 250 | OK | 530 | autenticación requerida |
| 354 | manda los datos | 535 | credenciales no válidas |
| 500/502 | orden no reconocida / no implementada | 550 | buzón no existe / rechazado |
| 503 | orden en mal orden (RCPT antes de MAIL) | 554 | transacción fallida (spam...) |

Lo que cuenta es la primera cifra: **2** bien, **3** continúa, **4** error temporal
(el MTA reintentará), **5** error permanente (rebote).

### HELO vs EHLO

`HELO` es el SMTP original (RFC 821). `EHLO` es ESMTP: el servidor contesta con la lista
de **extensiones** que admite (`STARTTLS`, `AUTH`, `8BITMIME`, `SIZE`, `PIPELINING`...).
Sin EHLO el cliente no puede saber si hay cifrado.

### STARTTLS vs SSL/TLS implícito

| | STARTTLS ("TLS explícito") | TLS implícito |
|---|---|---|
| Cómo | empieza en claro y se pide `STARTTLS` (en POP3: `STLS`) | TLS desde el primer byte |
| Puertos | SMTP 587 y 25, POP3 110, IMAP 143 | SMTPS 465, POP3S 995, IMAPS 993 |
| Riesgo | si el cliente no **exige** TLS, un MITM puede borrar `STARTTLS` del EHLO (*downgrade*) | ninguno de ese tipo |
| En la práctica | ej. 11, 12 | ej. 13-16 |

En los dos casos `wrap_socket()` devuelve un socket **nuevo**: todo lo demás va por él.
`create_default_context()` verifica el certificado y el nombre (`server_hostname`).

### ¿Por qué `\r\n.\r\n`?

DATA no lleva longitud: el fin del mensaje se marca con una línea que solo tiene un punto.
Si el texto tiene una línea que empieza por `.`, el cliente le **añade otro punto**
(*dot-stuffing*) y el servidor lo quita. Así nunca se confunde con el final. POP3 usa el
mismo mecanismo en sus respuestas multilínea. Y **CRLF** (`\r\n`) es el fin de línea
obligatorio en SMTP y POP3. Los LF sueltos están en la base del ataque "SMTP smuggling".

### Sobre vs cabeceras

| Sobre (envelope, RFC 5321) | Cabeceras (RFC 5322) |
|---|---|
| `MAIL FROM`, `RCPT TO` | `From:`, `To:`, `Cc:`, `Subject:`, `Date:`... |
| Decide **a quién se entrega** y **a quién se devuelven los errores** | Solo es información para el usuario |
| Lo mira SPF | Lo mira DKIM (firma) y DMARC (alineación con el From:) |
| El destino lo deja en `Return-Path:` / `Delivered-To:` | Se puede escribir cualquier cosa |

Por eso funciona `Bcc:`: el destinatario oculto va en un `RCPT TO` pero no en las
cabeceras. Y por eso se puede falsificar el `From:`.

### Cómo se entrega: MX (`dns/dns_mx_gmail.py`)

El MTA pide los MX del dominio del destinatario y los prueba por `preference`, del menor
al mayor (con empate, al azar). Si ninguno responde, guarda el mensaje en **cola** y lo
reintenta durante unos 5 días; luego lo devuelve al remitente (rebote). Si no hay MX, se
usa el registro A del dominio.

### SPF, DKIM y DMARC (`dns/dns_mx_spf_uniovi.py`)

| | Qué protege | Dónde se publica | Cómo se comprueba |
|---|---|---|---|
| **SPF** | qué **IP** pueden enviar con un dominio en el `MAIL FROM` | TXT `v=spf1 ...` del dominio | el MTA destino mira si la IP que le conecta está en la lista (`mx`, `a:`, `ip4:`, `include:`; `-all` = el resto falla) |
| **DKIM** | que cabeceras y cuerpo **no se han alterado** y vienen del dominio `d=` | TXT con la clave pública en `selector._domainkey.dominio` | verifica la firma de la cabecera `DKIM-Signature:` |
| **DMARC** | el `From:` **visible** | TXT en `_dmarc.dominio` (`p=none/quarantine/reject`) | exige que SPF o DKIM pasen **y alineen** con el dominio del From:; manda informes |

SPF no protege el From: y falla con los reenvíos. DKIM sobrevive a los reenvíos. DMARC
une los dos con lo que ve el usuario.

---

## 3. POP3 (lectura)

### Máquina de estados (`simuladores/servidor_pop3_falso.py`)

```
     conexión TCP (+TLS implícito en 995)
                │
           +OK saludo
                ▼
     ┌──────────────────────┐   USER x / PASS y (o APOP)
     │    AUTHORIZATION     │── -ERR: sigue aquí
     └──────────┬───────────┘
                │ +OK (se bloquea el buzón y se "fotografía")
                ▼
     ┌──────────────────────┐   STAT  LIST [n]  RETR n  TOP n k
     │     TRANSACTION      │   DELE n (solo MARCA)  RSET (desmarca)
     └──────────┬───────────┘   NOOP  UIDL
                │ QUIT
                ▼
     ┌──────────────────────┐
     │        UPDATE        │   borra DE VERDAD los marcados, libera y cierra
     └──────────────────────┘
   (si se corta sin QUIT no se pasa por UPDATE: no se borra nada)
```

- Las respuestas no son códigos numéricos: `+OK ...` o `-ERR ...`.
- `STAT` → `+OK <nº de mensajes> <octetos>`. `LIST` → una línea `n tamaño` por mensaje.
  `TOP n 0` → solo las cabeceras.
- Las multilínea (`RETR`, `LIST`, `TOP`, `UIDL`) acaban en `.` con dot-stuffing.
- Los números 1..N no cambian en toda la sesión. Para reconocer un mensaje entre sesiones
  está el identificador único de `UIDL`.

### POP3 vs IMAP vs SMTP

| | SMTP | POP3 | IMAP |
|---|---|---|---|
| Para qué | **enviar**/retransmitir | **descargar** el buzón | **gestionar** el buzón en el servidor |
| Puertos | 25, 587 (STARTTLS), 465 (TLS) | 110, 995 (TLS) | 143, 993 (TLS) |
| Respuestas | código de 3 cifras | `+OK` / `-ERR` | etiquetas `A1 OK` |
| Carpetas / marcas leído / varios dispositivos | – | no (solo la bandeja; "bajar y borrar") | sí, se sincroniza todo |

### poplib (`correo/pop3/email_pop3_poplib*.py`)

`retr(n)` devuelve `(b'+OK ...', [líneas sin \r\n], octetos)`; el mensaje se reconstruye
con `b"\r\n".join(líneas)`. Un `-ERR` se convierte en la excepción `poplib.error_proto`.

---

## 4. Formato de los mensajes: RFC 5322 y MIME

- **Mensaje = cabeceras + línea en blanco + cuerpo.** Cabeceras `Nombre: valor`, que se
  pueden plegar en varias líneas empezando la continuación por un espacio o un tabulador.
  Líneas de 998 bytes como máximo, terminadas en CRLF.
- **Cabeceras solo en ASCII.** Lo que no es ASCII va en **RFC 2047**: `=?utf-8?q?D=C3=A9sti?=`
  (q = parecido a quoted-printable) o `=?utf-8?b?...?=` (base64).
- **MIME** (`MIME-Version: 1.0`):
  - `Content-Type: text/plain; charset="utf-8"` dice qué hay y en qué juego de caracteres.
  - `Content-Transfer-Encoding` dice cómo se ha hecho "seguro" para viajar:
    - `7bit`: ASCII puro.
    - `8bit`: UTF-8 tal cual (solo si el servidor anuncia `8BITMIME`).
    - `quoted-printable`: `canci=C3=B3n`. Legible con pocas tildes; para texto.
    - `base64`: 3 bytes → 4 caracteres (+33 %). Para binarios.
  - `multipart/mixed; boundary="===...=="`: varias partes separadas por `--boundary` y
    cerradas con `--boundary--`. El boundary es aleatorio para que no aparezca en el
    contenido. En los adjuntos va `Content-Disposition: attachment; filename="atc.gif"`.
- **¿Por qué la biblioteca `email` y no una plantilla?** La plantilla del ej. 7 no
  codifica las tildes, no pone `Date`, `Message-ID` ni MIME, usa `\n` en lugar de CRLF, no
  hace dot-stuffing y no sabe adjuntar. Un mensaje mal formado acaba en spam o rechazado.
  `EmailMessage` lo hace todo bien. Detalles: `as_bytes()` no incluye el punto final, y
  con `policy=email.policy.SMTP` pone CRLF.
- **Leer** (ej. 16): `message_from_bytes()` → `decode_header()` + `make_header()` para las
  cabeceras (API antigua); con `policy=email.policy.default` sale ya decodificado, y
  `get_body().get_content()` deshace también base64/QP.

---

## 5. Seguridad

- **Base64 no es cifrado.** Cualquiera lo revierte: `echo Y2xhdmU= | base64 -d` → `clave`.
  AUTH LOGIN solo es seguro **dentro de TLS**, y por eso el servidor solo anuncia AUTH
  tras STARTTLS.
- **Contraseña de aplicación** (Gmail): una clave distinta de la de la cuenta, solo para
  un programa. Se puede revocar sin cambiar la principal y no da acceso a la web de la
  cuenta. Requiere la verificación en dos pasos.
- **OAuth2** (XOAUTH2): lo que usan los clientes modernos. El programa recibe un *token*
  con permisos limitados y caducidad, y nunca ve la contraseña.
- **Verificar el certificado.** `create_default_context()` lo hace; smtplib y poplib sin
  `context` **no** lo hacen. Sin verificación, TLS cifra pero no protege de un MITM.
- **Relay abierto.** Un SMTP que entrega a cualquiera sin autenticar es un regalo para los
  spammers. `relay.uniovi.es` lo evita aceptando solo conexiones de la red de Uniovi, y
  los simuladores escuchan solo en 127.0.0.1.
- **Credenciales fuera del código**: variables de entorno o `getpass` (`comun.py`).

---

## 6. Preguntas tipo examen

1. **¿Qué diferencia hay entre una consulta recursiva y una iterativa?** En la recursiva
   (`rd=1`) el servidor busca la respuesta final por su cuenta. En la iterativa (`rd=0`)
   solo dice lo que sabe: la respuesta si es autoridad, o una referencia (NS) a quién
   preguntar después; sigue el cliente.
2. **¿Qué indica el flag `aa`? ¿Y `ra`?** `aa`: la respuesta viene de un servidor con
   autoridad sobre la zona. `ra`: el servidor ofrece recursión.
3. **¿Por qué la cabecera DNS lleva un `id`?** Porque DNS va sobre UDP, sin conexión: el
   id permite casar cada respuesta con su pregunta (y dificulta colar respuestas falsas).
4. **¿Qué es un glue record y cuándo hace falta?** Es la A/AAAA de un NS que la zona padre
   publica en ADDITIONAL. Hace falta cuando el nombre del NS está dentro de la zona que
   delega; si no, sería imposible averiguar su IP.
5. **¿Qué diferencia hay entre NXDOMAIN y una respuesta vacía (NOERROR sin ANSWER)?**
   NXDOMAIN: el nombre no existe. NOERROR sin respuesta: el nombre existe pero no tiene
   registros de ese tipo (o es una referencia).
6. **¿Qué es un CNAME? ¿Puede un dominio raíz como uniovi.es ser un CNAME?** Un alias que
   apunta a un nombre canónico. No: un CNAME no puede convivir con otros registros, y el
   apex de la zona necesita SOA y NS.
7. **¿Por qué al poner la IP de Wikipedia en el navegador no sale la página?** Por el
   virtual hosting: el servidor elige el sitio por la cabecera `Host`/SNI. Con la IP no
   sabe cuál es; además redirige a HTTPS y el certificado es de `*.wikipedia.org`.
8. **¿Qué devuelve `gethostbyname_ex` y en qué se queda corto frente a `getaddrinfo`?**
   (canónico, alias, IPv4). Solo IPv4 y solo da direcciones, no los parámetros de
   `socket()`; `getaddrinfo` es independiente del protocolo.
9. **¿Cómo sabe un MTA a qué máquina entregar un correo para `x@gmail.com`?** Consulta los
   MX de gmail.com y los prueba de menor a mayor `preference`. Si fallan todos, lo deja en
   cola y reintenta (unos 5 días).
10. **¿Qué significan 220, 250, 354 y 221 en SMTP?** Servicio listo; OK; empieza a enviar
    los datos (termina con `.`); cierro la conexión.
11. **¿Por qué el mensaje termina en `\r\n.\r\n` y qué pasa si una línea empieza por punto?**
    DATA no lleva longitud: el fin es una línea con solo un punto. A las líneas que
    empiezan por `.` el cliente les añade otro punto (dot-stuffing) y el servidor lo quita.
12. **¿Qué diferencia hay entre `MAIL FROM` y la cabecera `From:`?** `MAIL FROM` es el
    sobre: recibe los rebotes y lo mira SPF. `From:` es informativo para el usuario, lo
    mira DMARC y se puede falsificar.
13. **¿HELO o EHLO? ¿Por qué hay que repetir EHLO después de STARTTLS?** EHLO, porque
    devuelve las extensiones (STARTTLS, AUTH...). Tras TLS se repite porque el servidor
    descarta lo negociado en claro, que un atacante pudo alterar, y anuncia de nuevo sus
    extensiones, ahora con AUTH.
14. **¿STARTTLS o TLS implícito?** STARTTLS empieza en claro y sube a TLS en el mismo
    puerto (587, 110); TLS implícito cifra desde el primer byte (465, 995). Con STARTTLS
    hay que exigir TLS para evitar el downgrade.
15. **¿AUTH LOGIN cifra la contraseña?** No. Base64 es una codificación reversible; la
    protección la da la capa TLS de debajo.
16. **¿Para qué sirven SPF, DKIM y DMARC?** SPF: qué IP pueden enviar por un dominio
    (sobre). DKIM: firma digital del mensaje con clave pública en el DNS. DMARC: política
    si fallan y alineación con el From: visible.
17. **Describe la máquina de estados de POP3.** AUTHORIZATION (USER/PASS) → TRANSACTION
    (STAT, LIST, RETR, TOP, DELE, RSET) → con QUIT, UPDATE (borra los marcados). Sin QUIT
    no se borra nada.
18. **¿Qué devuelve `poplib.retr()` y cómo se obtiene un mensaje analizable?** `(respuesta,
    líneas sin CRLF, octetos)`; se hace `email.message_from_bytes(b"\r\n".join(líneas))`.
19. **¿Por qué un asunto con tildes aparece como `=?utf-8?b?...?=`?** Las cabeceras solo
    admiten ASCII; RFC 2047 codifica el texto indicando el charset y la codificación (q o
    b). `decode_header` + `make_header` (o `policy.default`) lo deshace.
20. **¿Qué es multipart/mixed y para qué es el boundary?** Un mensaje de varias partes
    (texto + adjuntos). El boundary es una cadena aleatoria que separa las partes y no
    puede aparecer en su contenido; los adjuntos binarios van en base64.
21. **¿Por qué Gmail pide una contraseña de aplicación?** Porque no acepta la contraseña
    de la cuenta en protocolos "básicos" (SMTP/POP/IMAP sin OAuth2). La de aplicación es
    revocable, específica y exige 2FA. La alternativa moderna es OAuth2.
22. **¿POP3 o IMAP para leer el correo desde el móvil y el portátil?** IMAP: el correo
    se queda en el servidor con sus carpetas y marcas, sincronizado. POP3 está pensado
    para descargar en un solo equipo.
