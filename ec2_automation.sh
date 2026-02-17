#!/bin/bash
set -euo pipefail

# ------------------------------------------------------------
# Script Name: create-ec2-mac.sh
# Purpose:
#   Create an EC2 instance using AWS CLI (macOS version).
#
# Priority:
#   CLI argument > ENV variable > Default value
# ------------------------------------------------------------

check_brew() {
    command -v brew >/dev/null 2>&1
}

check_awscli() {
    command -v aws >/dev/null 2>&1
}

install_awscli_mac() {
    echo "Installing AWS CLI using Homebrew..."
    brew update
    brew install awscli
    echo "AWS CLI installed:"
    aws --version
}

wait_for_instance_running() {
    local instance_id="$1"
    echo "Waiting for instance $instance_id to reach running state..."

    while true; do
        state=$(aws ec2 describe-instances \
            --instance-ids "$instance_id" \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text)

        if [[ "$state" == "running" ]]; then
            echo "Instance $instance_id is now running."
            break
        fi

        echo "Current state: $state ... retrying in 10 seconds"
        sleep 10
    done
}

create_ec2_instance() {
    local ami_id="$1"
    local instance_type="$2"
    local key_name="$3"
    local subnet_id="$4"
    local security_group_ids="$5"
    local instance_name="$6"

    if [[ -z "$ami_id" || -z "$key_name" || -z "$subnet_id" || -z "$security_group_ids" ]]; then
        echo "Required parameters missing." >&2
        exit 1
    fi

    echo "Creating EC2 instance..."

    instance_id=$(aws ec2 run-instances \
        --image-id "$ami_id" \
        --instance-type "$instance_type" \
        --key-name "$key_name" \
        --subnet-id "$subnet_id" \
        --security-group-ids $security_group_ids \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$instance_name}]" \
        --query 'Instances[0].InstanceId' \
        --output text
    )

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        echo "Instance creation failed." >&2
        exit 1
    fi

    echo "Instance created: $instance_id"

    wait_for_instance_running "$instance_id"
}

Main() {

    # Check Homebrew
    if ! check_brew; then
        echo "Homebrew is not installed. Install it first: https://brew.sh" >&2
        exit 1
    fi

    # Install AWS CLI if missing
    if ! check_awscli; then
        install_awscli_mac
    fi

    # CLI > ENV > Default
    AMI_ID="${1:-${AMI_ID:-ami-123456}}"
    INSTANCE_TYPE="${2:-${INSTANCE_TYPE:-t2.micro}}"
    KEY_NAME="${3:-${KEY_NAME:-my-key}}"
    SUBNET_ID="${4:-${SUBNET_ID:-}}"
    SECURITY_GROUP_IDS="${5:-${SECURITY_GROUP_IDS:-}}"
    INSTANCE_NAME="${6:-${INSTANCE_NAME:-Shell-Script-EC2-Demo}}"

    create_ec2_instance "$AMI_ID" "$INSTANCE_TYPE" "$KEY_NAME" "$SUBNET_ID" "$SECURITY_GROUP_IDS" "$INSTANCE_NAME"

    echo "EC2 creation completed successfully."
}

Main "$@"