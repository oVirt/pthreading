#!/bin/bash -e

# make sure there's no previous runs
rm -rf .tox
tox
