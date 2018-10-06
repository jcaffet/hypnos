#!/bin/bash

usage(){
    echo "Usage: $0 <env>" 
    echo "env : env to deploy" 
}

if [ $# -eq 1 ]; then
   env=$1
else
   usage;
   exit 1;
fi


case $env in
  dev|recprod)
  zip hypnos-terminate.py.zip hypnos-terminate.py
  HYPNOS_BUCKET=applications.${env}
  aws s3 cp hypnos-terminate.py.zip s3://${HYPNOS_BUCKET}/hypnos/
  echo "Updating ${env} account ..."
  aws --profile=${env} cloudformation create-stack
      --stack-name operations-hypnos-${env} \
      --capabilities CAPABILITY_NAMED_IAM \
      --template-body file://cf-hypnos.yml
  ;;
*)
  echo "Unknown environment"
  exit 1
  ;;
esac

