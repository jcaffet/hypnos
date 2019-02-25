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

echo "Zipping source"
zip hypnos-terminate.py.zip hypnos-terminate.py
echo "Copying source"
HYPNOS_BUCKET=hypnos-543476789297
aws --profile=${profile} s3 cp hypnos-terminate.py.zip s3://${HYPNOS_BUCKET}/source/
echo "Creating stack"
aws --profile=${profile} cloudformation create-stack \
    --stack-name hypnos-central \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://cf-hypnos-central.yml \
    --parameters ParameterKey=Environment,ParameterValue=${environment} \
    --parameters ParameterKey=LambdaS3Bucket,ParameterValue=${HYPNOS_BUCKET}

