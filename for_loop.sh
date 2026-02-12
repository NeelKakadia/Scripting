#!/bin/bash

# Counter for missing services
missing_count=0

# Loop through each service
for service in "$@"
do
    if command -v "$service" >/dev/null 2>&1; then
        echo "$service is installed"
    else
        echo "$service is NOT installed"
        missing_count=$((missing_count + 1))
    fi
done

# Print total missing services
echo "--------------------------------"
echo "Total services missing: $missing_count"