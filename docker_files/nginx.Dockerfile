FROM nginx:1.23.3
WORKDIR /certs
RUN mkdir /var/wwww

COPY ./misc/nginx.conf /etc/nginx/nginx.conf
COPY ./misc/nginx.htpasswd /etc/nginx/conf.d/nginx.htpasswd

RUN mkdir -p /var/www/fm/html
COPY ./fm_dashboard/ /var/www/fm/html
COPY ./misc/fm.conf /etc/nginx/sites-available/fm.conf

RUN mkdir -p /var/wwww/map_editor/html/map_editor
COPY ./map_editor_dashboard/ /var/www/map_editor/html/map_editor
