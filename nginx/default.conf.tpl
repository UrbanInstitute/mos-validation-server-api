server {
    listen ${LISTEN_PORT};

    server_name _;
    return 301 https://$host$request_uri;
}


server {
    listen ${LISTEN_PORT_SSL};

    ssl_certificate     /etc/nginx/ssl/sdt-validation-server.urban.org.pem;
    ssl_certificate_key /etc/nginx/ssl/sdt-validation-server.urban.org.key;

    ssl_protocols             TLSv1.2 TLSv1.3;
    ssl_ciphers               HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_verify_client         off;
    ssl_session_cache         shared:SSL:10m;
    ssl_session_timeout       10m;
          
    charset utf-8;


    access_log  /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log;
    server_name sdt-validation-server.urban.org;

    ssl_dhparam /vol/proxy/ssl-dhparams.pem;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location ~* \.(eot|ttf|woff|woff2)$ {
        add_header Access-Control-Allow-Origin *;
    }


    location /static {
        alias /vol/static;
    }

    location /api {
        uwsgi_pass           ${APP_HOST}:${APP_PORT};
        include              /etc/nginx/uwsgi_params;
        include              /etc/nginx/mime.types;
        client_max_body_size 10M;
        proxy_redirect          off;
        proxy_set_header        Host $host;
        proxy_set_header        X-Real-IP $remote_addr;
        proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Ssl on;
        proxy_set_header        X-Forwarded-Proto https;
    }
}