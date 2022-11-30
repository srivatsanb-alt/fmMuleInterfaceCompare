FROM nginx:1.14.0

COPY ./misc/nginx.conf /etc/nginx/nginx.conf
COPY ./static/certs/all_server_ips_cert.pem  /etc/ssl/certs/all_server_ips_cert.pem
COPY ./static/certs/all_server_ips_key.pem /etc/ssl/private/all_server_ips_key.pem

COPY ./dashboard/ /etc/nginx/html/
