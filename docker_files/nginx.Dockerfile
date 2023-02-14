FROM nginx:1.23.3
WORKDIR /certs
COPY ./misc/nginx.conf /etc/nginx/nginx.conf
COPY ./dashboard/ /etc/nginx/html/
