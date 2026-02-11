#!/bin/bash

echo "It is a script for user defined variable"

read -p "Enter Username:" username


<< comment
or other way is echo "Enter the username"
read username
comment

echo "username is $username"

<< cm1
taking input from the arguments
you can use this method to create multiple user accounts without passing it as a user defiend argument
cm1

echo "the username is $1"



