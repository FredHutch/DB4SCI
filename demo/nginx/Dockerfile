# nginx 
#
FROM nginx:1.13.8 

# static content
COPY www/* /usr/share/nginx/html/

# TLS certs
#COPY ssl/* /etc/ca-certificates/

#RUN if [ -e /etc/nginx/sites-enabled/default ] ;then rm /etc/nginx/sites-enabled/default ; fi 
RUN if [ -e /etc/nginx/conf.d/default.conf ] ;then rm /etc/nginx/conf.d/default.conf ; fi 
COPY demo.conf /etc/nginx/conf.d/

CMD  ["nginx", "-g", "daemon off;"]
