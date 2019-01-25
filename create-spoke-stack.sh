#!/bin/bash

usage(){
    echo "Usage: $0 <profile>" 
    echo "profile : aws profile to use for deployment" 
}

if [ $# -eq 1 ]; then
   profile=$1
else
   usage;
   exit 1;
fi

echo "Creating stack"
aws --profile=${profile} cloudformation create-stack \
    --stack-name hypnos-spoke \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://cf-hypnos-spoke.yml

