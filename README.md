# Validation Server (v2) API

This repository contains the Django REST API for the Validation Server Prototype (v2). The API will be integrated into the AJAX architecture, which will connect the front-end of the system to the MOS backend engine.
The Template use 2 differents docker-compose file:

## Related repositories
- https://github.com/UrbanInstitute/mos-validation-server-engine: MOS backend engine of the Validation Server
- https://github.com/UrbanInstitute/mos-validation-server-r-package: R package for user-submitted analyses
- https://github.com/UrbanInstitute/mos-validation-server-infra: Cloud formation stack for the Validation Server infrastructure


## Build and deployment instructions
#### docker-compose.yml
This docker-compose file is for local testing only.
When you are coding your web app and testing your code along with the database, you will run the usual command: docker-compose up

- The local URL for testing 
  the template webapp is: http://127.0.0.1:8000/ (http://0.0.0.0:8000 on Mac)
- The local URl for the sample api endpoint that I created is:
  http://127.0.0.1:8000/api/v1/samples (http://0.0.0.0:8000/api/v1/samples on Mac)
- The local URl for testing the sample api endpoint with drf-spectacular and swagger API is: http://localhost/api/v1/docs/ (http://0.0.0.0/api/v1/docs)
  With these urls, you can test the different requests that your endpints are allowed to.

#### docker-compose-deploy.yml
This docker-compose-deploy.yml file if the docker-compose that will be used for the deployment (staging and production) using NGINX. it can be tested locally too, which can be seen as a sandbox or pre-staging.
the command that can be used to test the docker-compose-deploy.yml file is: "docker-compose -f docker-compose-deploy.yml up"
the -f flag means file.
- The local URL for testing 
  the template webapp via nginx: http://localhost/
- The local URl for testing the sample api endpoint that I created is:
  http://localhost//api/v1/samples

#### Build and Run the Container.
If you're using the template for the first time, or your building up the container, you can buil and run the container all at once.

If you're building and runing the local docker-compose file, run the following command:

```bash
docker-compose up --build
```

If you're trying to build and run the docker-compose for deployment, run the following command:

```bash
docker-compose -f docker-compose-deploy.yml up --build
```

#### Backup SQL data
to export your SQL data into a local file, run this command:
```bash
docker exec -it db sh ./scripts/export_mysql_backup.sh
```
You'll be prompted for the mysql password of user 'dev' in the console.

#### NGINX
The local testing with docker-compose.yml does not use nginx, the static files, along with the other URLS are served by UWSGI, which is already came implemnted with Django.


#### Create user groups if starting DB from scratch
Call
```bash
docker-compose run --rm app sh -c "python manage.py createusergroups"
```

#### Running and testing locally
Build images with
```bash
docker-compose build
```

Start up development server and containers with
```bash
docker-compose up
```
Open 127.0.0.1:8000/api/admin to get to the admin panel.
Open 127.0.0.1:8000/api/docs to get to the SwaggerUI.
Open 127.0.0.1:8000/api/schemas to download API schemas.

Run unit tests with
```bash
docker-compose run --rm app sh -c "python manage.py test"
```
To run a specific test case, e.g. the PublicUserApiTests in the user app, use
```bash
docker-compose run --rm app sh -c "python manage.py test <app>.tests.<module>.<class>"
docker-compose run --rm app sh -c "python manage.py test users.tests.test_user_api.PublicUserApiTests"
```
To run a specific test method within a test case, e.g. the PublicUserApiTests in the user app, use
```bash
docker-compose run --rm app sh -c "python manage.py test <app>.tests.<module>.<class>.<method>"
docker-compose run --rm app sh -c "python manage.py test users.tests.test_user_api.PublicUserApiTests.test_create_token_for_user"
```

If you get the error message "Access denied for user 'dev'@'%' to database 'test_db'", then the DB user "dev" does not have permission to create a database. Add the permission:
```bash
docker-compose run --rm db sh -c "mysql -uroot -p"
```
Enter root password.
```bash
GRANT ALL ON *.* TO 'dev'@'%';
```
If you get the message "Got an error creating the test database: database 'test_db' already exists.", enter "yes" and continue.

See all implemented urls/patterns:
```bash
docker-compose  run --rm app sh -c "python manage.py show_urls"
```

