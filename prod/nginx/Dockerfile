# nginx 
#
FROM nginx:1.13.8 

# static content
COPY www/* /usr/share/nginx/html/

# TLS certs
COPY ssl/* /etc/ca-certificates/

RUN if [ -e /etc/nginx/sites-enabled/default ] ;then rm /etc/nginx/sites-enabled/default ; fi 
COPY mydb.conf /etc/nginx/conf.d/

CMD  ["nginx", "-g", "daemon off;"]
