#!/bin/bash

echo "Starting app ..."

# repeat the next line for as many workers you need to start!
python3 run_worker.py &
python3 run_worker.py &
python3 run_worker.py &
python3 run_worker.py &

while true
do
    sleep 1
done

