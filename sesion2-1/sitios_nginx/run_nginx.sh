#!/bin/bash

# Detener y eliminar contenedor anterior si existe
docker stop nginx-sitios 2>/dev/null
docker rm nginx-sitios 2>/dev/null

# Lanzar el nuevo contenedor con múltiples puertos y volúmenes
docker run -d \
  --name nginx-sitios \
  -p 80:80 \
  -p 81:81 \
  -v $(pwd)/sitios_nginx:/etc/nginx/conf.d:ro \
  -v $(pwd)/html:/usr/share/nginx/html:ro \
  -v $(pwd)/html2:/usr/share/nginx/html2:ro \
  nginx:latest

echo "Contenedor Nginx iniciado correctamente."
echo "Sitio 1 disponible en: http://<IP_DE_LINUX>/"
echo "Sitio 2 disponible en: http://<IP_DE_LINUX>:81/"