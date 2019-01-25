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

echo "Zipping source"
zip hypnos-terminate.py.zip hypnos-terminate.py
echo "Copying source"
HYPNOS_BUCKET=operations-services-corp
aws s3 cp hypnos-terminate.py.zip s3://${HYPNOS_BUCKET}/hypnos/
echo "Creating stack"
aws cloudformation create-stack \
    --stack-name operations-hypnos-central-${profile} \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://cf-hypnos-central.yml \
    --parameters ParameterKey=Environment,ParameterValue=${profile}

