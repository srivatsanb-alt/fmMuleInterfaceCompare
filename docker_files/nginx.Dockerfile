FROM nginx:1.23.3
WORKDIR /certs
COPY ./misc/nginx.conf /etc/nginx/nginx.conf
COPY ./misc/nginx.htpasswd /etc/nginx/conf.d/nginx.htpasswd
COPY ./dashboard/ /etc/nginx/html/
