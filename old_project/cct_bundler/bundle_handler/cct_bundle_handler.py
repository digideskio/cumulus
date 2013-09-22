#!/usr/bin/env python

""" Script downloading and unpacking CCT bundles for the host """

import os
import sys
import tarfile
import tempfile

from boto import s3
from subprocess import call
from datetime import datetime
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError


def main():
    """ Main function """
    config = SafeConfigParser()
    config.read('/etc/cumulus-cloud-tools/metadata.conf')

    #
    # Connect to AWS S3
    #
    log("Connecting to AWS S3")
    try:
        con = s3.connect_to_region(
            config.get('metadata', 'region'),
            aws_access_key_id=config.get('metadata', 'aws-access-key-id'),
            aws_secret_access_key=config.get(
                'metadata', 'aws-secret-access-key'))
    except NoSectionError, error:
        log('Missing config section: {}'.format(error))
        sys.exit(1)
    except NoOptionError, error:
        log('Missing config option: {}'.format(error))
        sys.exit(1)
    except AttributeError:
        log(
            'It seems like boto is outdated. Please upgrade '
            'by running \"pip install --upgrade boto\"')
        sys.exit(1)
    except:
        log('Unhandled exception when connecting to S3.')
        sys.exit(1)

    #
    # Download the bundle
    #
    bucket = con.get_bucket(config.get('metadata', 's3_bundles_bucket'))
    key = bucket.get_key('{}/cct-bundle-{}-{}-{}.tar.bz2'.format(
        config.get('metadata', 'environment'),
        config.get('metadata', 'environment'),
        config.get('metadata', 'version'),
        config.get('metadata', 'instance_type')))
    bundle = tempfile.NamedTemporaryFile(suffix='.tar.bz2', delete=False)
    bundle.close()
    log("Downloading s3://{}/{} to {}".format(
        config.get('metadata', 's3_bundles_bucket'),
        key.name,
        bundle.name))
    key.get_contents_to_filename(bundle.name)

    # Unpack the bundle
    log("Unpacking {}".format(bundle.name))
    tar = tarfile.open(bundle.name, 'r:bz2')
    tar.extractall()
    tar.close()

    # Remove the downloaded package
    log("Removing temporary file {}".format(bundle.name))
    os.remove(bundle.name)

    # Run the post install scripts provided by the bundle
    log("Run all post script scripts")
    call(
        'run-parts -v --regex .*\\.sh /etc/cumulus-cloud-tools-init.d',
        shell=True)

    log("Done updating host")


def log(message):
    """ Print a message with a timestamp

    :type message: str
    :param message: Log message to print
    """
    print '{} - {}'.format(datetime.utcnow().isoformat(), message)


if __name__ == '__main__':
    main()
    sys.exit(0)

sys.exit(1)
