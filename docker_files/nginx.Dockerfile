FROM nginx:1.14.0
WORKDIR /certs
COPY ./misc/nginx.conf /etc/nginx/nginx.conf
COPY ./dashboard/ /etc/nginx/html/
