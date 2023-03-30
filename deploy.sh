#!/bin/bash
# Deployment script for sdt-validation-server-api
# Purpose: copies the correct docker-compose, requirements.txt, and .env file to
#          the correct locations and then runs the docker commands and initialization
#          scripts.
# Command: ./deploy.sh [environment]] -[destroy] -[restart]  > deployment.log
# Options: environment = development, staging, or production
#          -destroy = delete all containers and images before Building
#          -restart = restart docker-machine before building Containers
#          > deployment.log = write starttup messages to a file 'deployment.log'
#

echo "-----------------------------------------------------"
echo "Starting build:  $(date)"
echo "-----------------------------------------------------"
SECONDS=0

while getopts "e:m:r:d:i:c:o:" option; do
  case $option in
    e ) env=$OPTARG
    ;;
    d ) destroy=$OPTARG
    ;;
    i ) import=$OPTARG
    ;;
    c ) check=$OPTARG
    ;;
    o ) options=$OPTARG
    ;;
  esac
done


if [[ "$destroy" == "destroy" ]]
then
  destroy=1
else
  destroy=0
fi

if [[ "$restart" == "restart" ]]
then
  restart=1
else
  restart=0
fi

if [[ "$import" == "import" ]]
then
  import=1
else
  import=0
fi

if [[ "$check" == "check" ]]
then
  check=1
else
  check=0
fi

if [[ "$options" == "interactive" ]]
then
  interactive=1
else
  interactive=0
fi


if [[ "$env" == "prod" ]]
then
  environment="production"
elif [[ "$env" == "stg" ]]
then
  environment="staging"
elif [[ "$env" == "dev" ]]
then
  environment="development"
else
  environment=$env
fi


echo "-----------------------------------------------------"
echo "Inputs from command"
echo "-----------------------------------------------------"
echo "env: $env"
echo "environment: $environment"
echo "destroy: $destroy"
echo "import: $import"
echo "check: $check"

#else
#  echo "-----------------------------------------------------"
#  echo "Docker not installed - no restart is possible"
#  echo "-----------------------------------------------------"
#fi
#Open Docker, only if is not running
if (! docker stats --no-stream ); then
  sudo service docker start;
#Wait until Docker daemon is running and has completed initialisation
while (! docker stats --no-stream ); do
  # Docker takes a few seconds to initialize
  echo "Waiting for Docker to launch..."
  sleep 1
done
fi



echo "-----------------------------------------------------"
echo "Checking if destroy command was passed"
echo "-----------------------------------------------------"
if (($destroy != 0 ))
then
    echo "-------------------------------------------------------------------"
    echo "Destroy was passed -- clearing out existing containers and images."
    echo "-------------------------------------------------------------------"
    eval $(docker stop $(docker ps -a -q)  && docker rm $(docker ps -a -q) --force && docker rmi $(docker images -a -q) --force)
else
echo "-----------------------------------------------------"
echo "Destroy was not passed -- using containers."
echo "-----------------------------------------------------"
fi


echo "-----------------------------------------------------"
echo "Set env vars."
echo "-----------------------------------------------------"
# set .env vars
if (($environment == "staging"))
  then
  export $(grep -v '^#' .env.stg | xargs)
else (($environment == "production"))
  export $(grep -v '^#' .env.prod | xargs)
fi

if (($import != 0 ))
  then
  # Create DB Structure
  echo "-----------------------------------------------------"
  echo "Copy database dump to ./django-rest-app/scripts/mysql-dump"
  echo "Data will be imported when container is created"
  echo "-----------------------------------------------------"
  cp -fr ./$APP_DIR/scripts/$MYSQL_DATABASE_CREATE_SQL ./django-rest-app/scripts/mysql-dump/$MYSQL_DATABASE_CREATE_SQL
else
  echo "-----------------------------------------------------"
  echo "Database dump was removed from ./django-rest-app/scripts/mysql-dump"
  echo "No database created or updated because 'I' flag not passed"
  echo "-----------------------------------------------------"
  rm -rf ./$APP_DIR/scripts/mysql-dump/$MYSQL_DATABASE_CREATE_SQL

fi

echo "-----------------------------------------------------"
echo "Export mysql data"
echo "-----------------------------------------------------"
#docker exec app python manage.py dumpdata users authtoken v1 --output mydata.json
#docker exec mysql bash ./scripts/export_mysql_backup.sh


#exit 1 # terminate and indicate error


if [ -f "./docker-compose-deploy.yml" ]; then

  # Build Containers
  echo "-----------------------------------------------------"
  echo "Building containers"
  echo "-----------------------------------------------------"
  docker-compose -f docker-compose-deploy.yml build

  # Start Containers
  echo "-----------------------------------------------------"
  echo "Starting containers"
  echo "-----------------------------------------------------"
  if (($interactive != 0 ))
    then
      echo "-----------------------------------------------------"
      echo "Running as interactive so create superuser and checks will not run"
      echo "-----------------------------------------------------"
      docker-compose -f docker-compose-deploy.yml up  --remove-orphans
      echo "-----------------------------------------------------"
      echo "Running as interactive allows changes in code to compile on server"
      echo "-----------------------------------------------------"

  else
      echo "-----------------------------------------------------"
      echo "Running as detached so create superuser and checks will run"
      echo "-----------------------------------------------------"

      docker-compose -f docker-compose-deploy.yml up  -d --remove-orphans
      docker system prune --all --volumes --force
      echo "-----------------------------------------------------"
      echo "Running as detached means rebuilding containers to recompile code"
      echo "-----------------------------------------------------"

      echo "-----------------------------------------------------"
      echo "Pause to allow things to come up"
      echo "-----------------------------------------------------"
      sleep 15

      # Initialize Application
      echo "-----------------------------------------------------"
      echo "Create superuser"
      echo "-----------------------------------------------------"
      docker exec -tt app python manage.py createsuperuser --noinput

      echo "-----------------------------------------------------"
      echo "Create static files"
      echo "-----------------------------------------------------"
      docker exec app python manage.py collectstatic --noinput

      echo "-----------------------------------------------------"
      echo "Import mysql data"
      echo "-----------------------------------------------------"
      docker exec app bash ../scripts/import_mysql_backup.sh



      # Run tests
      echo "-----------------------------------------------------"
      echo "Run tests"
      echo "-----------------------------------------------------"
      docker exec app python manage.py test
    fi

    minutes=$((SECONDS/60))
    seconds=$((SECONDS%60))

    echo "-----------------------------------------------------"
    echo "Ending build:  $(date)"
    echo "Build took $minutes minutes and $seconds seconds."
    echo "-----------------------------------------------------"

    # These are dependency and security checks that should be run on each build.
    # Any security issues should be mitagated or a description of why they are
    #     not relevant should be included below.

    if (($check != 0 ))
      then
      echo "-----------------------------------------------------"
      echo "PEP8 checks"
      echo "-----------------------------------------------------"
      exec -it app pep8 --show-source --show-pep8 testsuite/E40.py
      exec -it app pep8 --statistics -qq Python-3.6/Lib

      echo "-----------------------------------------------------"
      echo "Dependency checks"
      echo "Only works with versioned packages check"
      echo "-----------------------------------------------------"
      echo "Dependency Security check"
      echo "-----------------------------------------------------"
      docker exec -it app safety check --json -r requirements.txt
      echo "-----------------------------------------------------"
      echo "Version check"
      echo "-----------------------------------------------------"
      docker exec -it app pip-check -a -H

      # Any security issues should be mitagated or a description of why they are
      #     not relevant should be inccluded below.
      echo "-----------------------------------------------------"
      echo "Django Security check"
      echo "-----------------------------------------------------"
      docker exec -it app python manage.py check --deploy

      echo "-----------------------------------------------------"
      echo "Bandit Security check"
      echo "-----------------------------------------------------"
      docker exec -it app bandit -r $APP_DIR/

      echo "-----------------------------------------------------"
      echo "License check"
      echo "-----------------------------------------------------"
      docker exec -it app  pip-licenses --with-system --with-urls --order=license
    else
      echo "-----------------------------------------------------"
      echo "No security or version checks were done"
      echo "-----------------------------------------------------"
    fi

    minutes=$((SECONDS/60))
    seconds=$((SECONDS%60))

    echo "-----------------------------------------------------"
    echo "Ending build:  $(date)"
    echo "Build took $minutes minutes and $seconds seconds."
    echo "-----------------------------------------------------"

fi # end running detached

# unset .env vars

if (($environment == "staging"))
  then
  unset $(grep -v '^#' .env.stg | sed -E 's/(.*)=.*/\1/' | xargs)
else (($environment == "production"))
  unset $(grep -v '^#' .env.prod | sed -E 's/(.*)=.*/\1/' | xargs)
fi

