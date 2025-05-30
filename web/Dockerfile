#FROM centos:latest
FROM rockylinux:8

# Install apache, PHP, and supplimentary programs. openssh-server, curl, and lynx-cur are for debugging the container.
RUN yum update -y
RUN yum install -y httpd
RUN yum install -y php php-fpm php-json php-devel curl wget openssh-server net-tools procps

# Create dir for php-fpm
RUN mkdir /run/php-fpm; mkdir /startup

# To expose env variables to php
RUN sed -i "s|;*clear_env\s*=\s*yes|clear_env = no|g" /etc/php-fpm.d/www.conf
RUN sed -i "s|;*clear_env\s*=\s*no|clear_env = no|g" /etc/php-fpm.d/www.conf

# Copy PHP page and delete index.html
COPY index.php /var/www/html/index.php
COPY styles.css /var/www/html/styles.css
COPY favicon.ico /var/www/html/favicon.ico

# Expose apache.
EXPOSE 80

# Create healthcheck pages
RUN echo '{"health": "OK"}' >/var/www/html/healthcheck.html
RUN echo "<?php phpinfo() ?>" > /var/www/html/healthcheck.php

# By default start up apache in the foreground, override with /bin/bash for interactive.
CMD ["/bin/sh", "-c", "/usr/sbin/php-fpm -D && /usr/sbin/httpd -D FOREGROUND"]
