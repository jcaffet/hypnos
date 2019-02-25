#!/bin/bash

usage(){
    echo "Usage: $0 <profile> <central-account>" 
    echo "profile : aws profile to use for deployment" 
    echo "central-account : aws profile where Hypnos is runs" 
}

if [ $# -eq 2 ]; then
   profile=$1
   central_account=$2
else
   usage;
   exit 1;
fi

echo "Creating stack"
aws --profile=${profile} cloudformation create-stack \
    --stack-name hypnos-spoke-account-role \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://cf-hypnos-spoke.yml \
    --parameters ParameterKey=CentralHypnosAccount,ParameterValue=${central_account}

