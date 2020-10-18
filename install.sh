#!/usr/bin/env bash

if [ "$EUID" -ne 0 ]; then
    echo "Please run the installer as root"
    exit
fi

chmod +x main.py
install main.py /bin/cnormitek

echo "cnormitek is now installed thank you !"
echo "Please use it as shown : cnormitek [folder]"
