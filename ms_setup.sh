#!/bin/env bash

cat << 'EOF'
-----------------------------
 Needed software for Neo Browser
-----------------------------

Debian Linux
sudo apt update
sudo apt install python3-gi python3-gi-cairo libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1

EOF

echo __________________________________
echo Begin installing needed packages
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

sudo apt update
sudo apt install python3-gi python3-gi-cairo libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1
sudo apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good
sudo apt install gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav


cat << 'EOF'
__________________________________
use python3 neo.py
to start the browser
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
EOF
