FROM nginx:1.17.3

COPY --from=opbeans/opbeans-frontend:latest /app/build /usr/share/nginx/html

COPY default.template /etc/nginx/conf.d/default.template
COPY rum-config.template /usr/share/nginx/html/rum-config.template
COPY entrypoint.sh /

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
