FROM nginx:1.23.3
WORKDIR /certs
RUN mkdir /var/wwww

COPY ./misc/nginx.conf /etc/nginx/nginx.conf
COPY ./misc/nginx.htpasswd /etc/nginx/conf.d/nginx.htpasswd
COPY ./dashboard/ /etc/nginx/html

RUN mkdir /var/wwww/map_editor
COPY ./map_editor_dashboard /var/www/map_editor/
