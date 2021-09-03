# Nautobot + Dolt

This is a work in progress and NOT officially released or supported.

## Local Dev & Test Environment

A local environment based on Docker Compose is available for development and testing as well as a sample dataset to help get started faster with Nautobot & Dolt integration.

### Initialize the Local environment

Run the following commmands to initialize the local environment
```
cp development/creds.example.env development/creds.env
invoke build
```

### Start the Local environment with a sample database
```
invoke migrate
invoke load-data
invoke start
```

> `invoke load-data` can take up to 30 min to run and it will generate many Warning messages, these messages can be ignored.

After few min, Nautobot will be available at `http://0.0.0.0:8080` 
You can connect with either of these 2 accounts:
- Login `admin` / Password `admin`
- Login `demo` / Password `nautobot`

Run the following commands to Reset the Local environment and load the sample dataset again
```
invoke stop
invoke destroy
invoke migrate
invoke load-data
invoke start
```

### Start the Local environment with an empty database
```
invoke migrate
invoke start
```
After few min, Nautobot will be available at `http://0.0.0.0:8080` 
You can connect with either of these 2 accounts:
- Login `admin` / Password `admin`

Run the following commands to Reset the Local environment
```
invoke stop
invoke destroy
invoke migrate
invoke start
```