#!/bin/bash

usage(){
    echo "Usage: $0 <profile>" 
    echo "profile : aws profile to use for deployment" 
    echo "bucket  : S3 bucket name (without s3://) to use" 
}

if [ $# -eq 2 ]; then
   profile=$1
   HYPNOS_BUCKET=$2
else
   usage;
   exit 1;
fi

echo "Zipping sources"
zip hypnos-wrapper.py.zip hypnos-wrapper.py
zip hypnos-central.py.zip hypnos-central.py

echo "Copying sources"
aws --profile=${profile} s3 cp . s3://${HYPNOS_BUCKET}/sources/ --recursive --exclude "*" --include "hypnos-*.py.zip"

echo "Creating stack"
aws --profile=${profile} cloudformation create-stack \
    --stack-name hypnos-central \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://cf-hypnos-central.yml \
    --parameters ParameterKey=LambdaS3Bucket,ParameterValue=${HYPNOS_BUCKET}

