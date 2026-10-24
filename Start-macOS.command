#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
python3 patcher.py --gui
result=$?
if [ "$result" -ne 0 ]; then
    echo "Python 3.10+ mit Tkinter wird benoetigt. Siehe docs/ANLEITUNG.md."
    printf 'Enter zum Schliessen: '
    read -r reply
fi
exit "$result"
