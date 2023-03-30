#!/bin/bash
# Deployment script for changing out SSLs
# Purpose: copies the SSLs from place where the DevOps team puts them to the
#          correct directory in project.
# Command: ./deploy_ssl.sh
# Options: none
#

echo "-----------------------------------------------------"
echo "Remove old certificates"
echo "-----------------------------------------------------"
if [ ! -d /home/docker1/validation-server.urban.org/nginx/ssl ]; then
  mkdir -p /home/docker1/validation-server.urban.org/nginx/ssl/;
else
  rm -rf nginx/ssl/*.*
fi


echo "-----------------------------------------------------"
echo "Copy new SSl certificates to project directory"
echo "-----------------------------------------------------"
cp /home/docker1/certs/*.* /home/docker1/validation-server.urban.org/nginx/ssl/