#!/usr/bin/env bash

echo "Updating packages..."
apt-get update

echo "Installing system dependencies..."
apt-get install -y lua5.1 lua5.2 lua5.3 lua5.4 git make g++ python3-pip

echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Cloning and building Luau..."
git clone https://github.com/Roblox/luau.git
cd luau
make config=release

echo "Adding Luau to PATH..."
cp build/release/luau /usr/local/bin/luau

echo "Build finished successfully!"
