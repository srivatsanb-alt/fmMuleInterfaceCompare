FROM nginx:1.14.0

COPY ./static/certs/nginx.conf /etc/nginx/nginx.conf
COPY ./static/certs/cert.pem /etc/ssl/certs/cert.pem
COPY ./static/certs/key.pem /etc/ssl/private/key.pem
COPY ./static/dashboard/ /etc/nginx/html/
