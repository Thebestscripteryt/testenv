#!/usr/bin/env bash

echo "Installing Lua versions..."
apt-get update
apt-get install -y lua5.1 lua5.2 lua5.3 lua5.4 git make g++

echo "Cloning and building Luau..."
git clone https://github.com/Roblox/luau.git
cd luau
make config=release

echo "Build complete"
