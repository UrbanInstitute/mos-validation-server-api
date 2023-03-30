FROM nginxinc/nginx-unprivileged:1-alpine
LABEL maintainer="Urban Institute"

COPY ./default-ssl.conf.tpl /etc/nginx/default.conf.tpl
COPY ./uwsgi_params /etc/nginx/uwsgi_params
COPY ./run.sh /run.sh

RUN mkdir /etc/nginx/ssl
COPY ssl/ /etc/nginx/ssl/

ENV LISTEN_PORT=8000
ENV LISTEN_PORT_SSL=443
ENV APP_HOST=app
ENV APP_PORT=9000

USER root

RUN mkdir -p /vol/static && \
    chmod 755 /vol/static && \
    touch /etc/nginx/conf.d/default.conf && \
    chown nginx:nginx /etc/nginx/conf.d/default.conf && \
    chmod +x /run.sh

VOLUME /vol/static

USER nginx

CMD ["/run.sh"]