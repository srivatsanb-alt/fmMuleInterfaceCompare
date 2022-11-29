FROM nginx:1.14.0

COPY ./misc/nginx.conf /etc/nginx/nginx.conf
COPY ./misc/certs/fm_rev_proxy_cert.pem /etc/ssl/certs/fm_rev_proxy_cert.pem
COPY ./misc/certs/fm_rev_proxy_key.pem /etc/ssl/private/fm_rev_proxy_key.pem
COPY ./dashboard/ /etc/nginx/html/
