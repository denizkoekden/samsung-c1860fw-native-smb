#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
python3 configure_smb.py
result=$?
printf 'Enter zum Schliessen: '
read -r reply
exit "$result"
