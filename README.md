# Cumulus

Cumulus is a deployment tool used to deploy and maintain environments built with AWS CloudFormation. Cumulus will help you bundle your code and configuration and unpack the bundle to new instances on CloudFormation.

## Basic concepts

Cumulus is built around three main concepts:

- An **environment** references a whole environment and all it's CF stacks. It holds together information about the AWS account, which stacks to deploy and in which version.
- A **stack** is simply a CloudFormation stack.
- And a **bundle** is a `tar.bz2` file with code and configuration to unpack to instances.

## Requirements

Cumulus requires Python 2.7 and `boto`. Please install requirements with

    sudo pip install -r cumulus/requirements.txt

## Configuration

### Cumulus configuration

All configuration is read form `/etc/cumulus.conf`, `~/.cumulus.conf` and , `./cumulus.conf` in order. This is an example configuration:

    [environment: stage]
    access-key-id: <AWS ACCESS KEY>
    secret-access-key: <AWS SECRET KEY>
    bucket: se.skymill.bundles
    region: eu-west-1
    stacks: full
    bundles: webserver, database
    version: 1.0.0-SNAPSHOT

    [stack: full]
    template: /Users/sebastian/tmp/hosts/webserver.json
    disable-rollback: true

    [bundle: webserver]
    paths:
        /Users/sebastian/tmp/hosts/webserver,
        /Users/sebastian/tmp/code/wordpress

    [bundle: database]
    paths: /Users/sebastian/tmp/hosts/database

All configuration options are required to be set.

### CloudFormation configuration

To save some space in this document, please find the example AWS CloudFormation template [here](https://github.com/skymill/cumulus/blob/master/cumulus/docs/cloudformation-template-example.json)

## Deployment workflow

First off you need to create a bundle. Run

    cumulus --environment production --bundle

This will bundle and upload all your software to AWS S3. The next step is to update CloudFormation. That is done with the `--deploy` command:

    cumulus --environment production --deploy

Cumulus will create or update the CloudFormation stacks as needed.
