#!/bin/bash

# ------------------------------------------------------------
# Function: monitor_errors
# Purpose:
#   - Reads a file line by line
#   - Prints lines containing "ERROR"
#   - Returns number of error lines found
# ------------------------------------------------------------

monitor_errors() {

    local logfile="$1"
    local error_count=0

    # Check if file exists
    if [ ! -f "$logfile" ]; then
        echo "File does not exist"
        return 1
    fi

    # Read file line by line
    while read -r line
    do
        if [[ "$line" == *ERROR* ]]; then
            echo "$line"
            error_count=$((error_count + 1))
        fi
    done < "$logfile"

    return $error_count
}

# Example usage
monitor_errors "$1"

# Capture returned value
count=$?

echo "--------------------------------"
echo "Total ERROR lines: $count"
