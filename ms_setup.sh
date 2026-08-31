#!/bin/env bash

cat << 'EOF'
OPEN THIS SCRIPT IN YOUR "APPS" DIRECTORY
SCRIPT WILL CREATE "Acme" DIRECTORY

-----------------------------
 Will install the following:
-----------------------------

Debian Linux
sudo apt update
sudo apt install python3-gi python3-gi-cairo libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1

HIT CTRL-C TO QUIT OR ENTER TO CONTINUE
EOF
read -n 1

echo __________________________________
echo Begin installing needed packages
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

sudo apt update
sudo apt update
sudo apt install python3-gi python3-gi-cairo libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1
sudo apt install python3-gi python3-gi-cairo libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1
sudo apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good
sudo apt install gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav

sleep 2

python3 lsetup.py

cat << 'EOF'
__________________________________
VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
There should be a new icon on
your desktop.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
EOF
