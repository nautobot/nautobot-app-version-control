# Nautobot + Dolt

This is a work in progress and NOT officially released or supported.

## Local Dev & Test Environment

A local environment based on Docker Compose is available for development and testing as well as a sample dataset to help get started faster with Nautobot & Dolt integration.

### Start the Local environment with a sample database
```
invoke build
invoke migrate
invoke load-data
```
Run the following commands to Reset the Local environment and load the sample dataset again
```
invoke build
invoke destroy
invoke migrate
invoke load-data
```
### Start the Local environment with an empty database
```
invoke migrate
invoke createsuperuser
invoke start
```



