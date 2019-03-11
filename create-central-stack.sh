#!/bin/bash

usage(){
    echo "Usage: $0 <profile> <environment>" 
    echo "profile : aws profile to use for deployment" 
    echo "environment : environment suffix when using Hypnos twice in the same account" 
}

if [ $# -eq 2 ]; then
   profile=$1
   environment=$2
else
   usage;
   exit 1;
fi

echo "Zipping sources"
zip hypnos-wrapper.py.zip hypnos-wrapper.py
zip hypnos-central.py.zip hypnos-central.py

echo "Copying sources"
HYPNOS_BUCKET=hypnos-460863991257
aws --profile=${profile} s3 cp . s3://${HYPNOS_BUCKET}/sources/ --recursive --exclude "*" --include "hypnos-*.py.zip"

echo "Copying accounts file"
aws --profile=${profile} s3 cp ./accounts.list s3://${HYPNOS_BUCKET}/config/ 

echo "Creating stack"
aws --profile=${profile} cloudformation create-stack \
    --stack-name hypnos-central \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://cf-hypnos-central.yml \
    --parameters ParameterKey=Environment,ParameterValue=${environment} \
    --parameters ParameterKey=LambdaS3Bucket,ParameterValue=${HYPNOS_BUCKET}

