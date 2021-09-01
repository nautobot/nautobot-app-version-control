# Nautobot + Dolt

This is a work in progress and NOT officially released or supported.

## Local Dev & Test Environment

A local environment based on Docker Compose is available for development and testing as well as a sample dataset to help get started faster with Nautobot & Dolt integration.

### Start the Local environment with a sample database
```
invoke build
invoke migrate
invoke load-data
invoke start
```

> `invoke load-data` can take up to 30 min to run and it will generate many Warning messages, these messages can be ignored.

Run the following commands to Reset the Local environment and load the sample dataset again
```
invoke stop
invoke build
invoke destroy
invoke migrate
invoke load-data
invoke start
```
### Start the Local environment with an empty database
```
invoke migrate
invoke createsuperuser
invoke start
```



