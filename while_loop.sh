#!/bin/bash

#Process status checker with while loop 
# Check if process name was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <process_name>"
    exit 1
fi

process="$1"

# Try maximum 5 times
for i in {1..5}
do
    if pgrep "$process" >/dev/null 2>&1; then
        echo "Process '$process' is running"
        exit 0
    else
        echo "Attempt $i: Process '$process' is down"
        sleep 5
    fi
done

# If loop completes, process never started
echo "Process '$process' is still down after 5 checks"
exit 1
