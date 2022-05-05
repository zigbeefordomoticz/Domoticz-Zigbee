#!/bin/bash
#Cleans and resets a git repo and its submodules

git reset --hard
git submodule sync --recursive
git submodule update --init --force --recursive
