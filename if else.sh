#!/bin/bash

# ------------------------------------------------------------
# Purpose:
#   Check whether Docker and kubectl are installed on the system.
#   Each tool is checked independently.
#
# Why we use `command -v` instead of `docker --version`:
#   - `command -v` checks if the executable exists in the system PATH.
#   - It does NOT execute the actual program (faster and safer).
#   - It avoids printing unnecessary version output.
#   - It provides a reliable exit status for scripting.
#
# Why we redirect output to /dev/null:
#   - We only care about the exit code (success/failure).
#   - We suppress normal output (stdout) and error output (stderr).
#   - This keeps the script output clean and professional.
#
# How exit codes work:
#   - Exit code 0     → success
#   - Non-zero code   → failure
# ------------------------------------------------------------


# Flags to track whether tools are missing
docker_missing=false
kubectl_missing=false


# ------------------------------------------------------------
# Check if Docker exists in the system PATH
#
# command -v returns:
#   0         → if command exists
#   non-zero  → if command does not exist
#
# >/dev/null 2>&1
#   - Redirects stdout to /dev/null
#   - Redirects stderr to wherever stdout is going
#   - Effectively silences all output
# ------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
    echo "Docker is installed"
else
    echo "Docker is NOT installed"
    docker_missing=true
fi


# ------------------------------------------------------------
# Check if kubectl exists in the system PATH
# Same logic as Docker check above.
# ------------------------------------------------------------
if command -v kubectl >/dev/null 2>&1; then
    echo "kubectl is installed"
else
    echo "kubectl is NOT installed"
    kubectl_missing=true
fi


# ------------------------------------------------------------
# Final combined check:
# If both Docker and kubectl are missing,
# print a summary message.
#
# The ! operator means logical NOT.
# ------------------------------------------------------------
if $docker_missing && $kubectl_missing; then
    echo "Neither Docker nor kubectl is installed"
fi
