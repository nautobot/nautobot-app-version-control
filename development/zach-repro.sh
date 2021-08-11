#!/bin/bash

set -eo pipefail

# verify python 3+
python --version

# run dolt sql-server in the background
cp dolt-config.yaml nautobot/
pushd nautobot
dolt init
dolt sql-server --config dolt-config.yaml &
popd

# install poetry package manager
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
`source $HOME/.poetry/env`

# setup poetry environment
pushd ../
poetry install

# enter poetry environment
poetry shell

# run the inital django db migrations
nautobot-server migrate


