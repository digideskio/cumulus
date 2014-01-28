#!/usr/bin/env python

""" Script downloading and unpacking Cumulus bundles for the host """

import logging
import logging.config
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from ConfigParser import SafeConfigParser, NoOptionError

try:
    from boto import s3
except ImportError:
    print('Could not import boto. Try installing it with "pip install boto"')
    sys.exit(1)

CONFIG = SafeConfigParser()
CONFIG.read('/etc/cumulus/metadata.conf')


# Configure logging
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_LOGGERs': False,
    'formatters': {
        'standard': {
            'format': (
                '%(asctime)s - cumulus-bundle-handler - '
                '%(levelname)s - %(message)s'
            )
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': '/var/log/cumulus-bundle-handler.log',
            'mode': 'a',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5
        }
    },
    'LOGGERs': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True
        },
        'cumulus_bundle_handler': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

try:
    LOGGING_CONFIG['handlers']['console']['level'] = CONFIG.get(
        'metadata', 'log-level')
    LOGGING_CONFIG['handlers']['file']['level'] = CONFIG.get(
        'metadata', 'log-level')
except NoOptionError:
    pass

logging.config.dictConfig(LOGGING_CONFIG)
LOGGER = logging.getLogger('cumulus_bundle_handler')


def main():
    """ Main function """
    _run_init_scripts(kill=True, start=False, other=True)

    bundle_types = CONFIG.get('metadata', 'bundle-types').split(',')
    if not bundle_types:
        LOGGER.error('Missing "bundle-types" in metadata.conf')
        sys.exit(1)

    _remove_old_files()

    for bundle_type in bundle_types:
        _download_and_unpack_bundle(bundle_type)

    _run_init_scripts(kill=False, start=True, other=True)

    LOGGER.info("Done updating host")


def _download_and_unpack_bundle(bundle_type):
    """ Download the bundle from AWS S3

    :type bundle_type: str
    :param bundle_type: Bundle type to download
    """
    key, compression = _get_key(bundle_type)

    # If the bundle does not exist
    if not key:
        LOGGER.error('No bundle found. Exiting.')
        sys.exit(1)

    bundle = tempfile.NamedTemporaryFile(
        suffix='.{}'.format(compression),
        delete=False)
    bundle.close()
    LOGGER.info("Downloading s3://{}/{} to {}".format(
        CONFIG.get('metadata', 'bundle-bucket'),
        key.name,
        bundle.name))
    key.get_contents_to_filename(bundle.name)

    # Unpack the bundle
    LOGGER.info("Unpacking {}".format(bundle.name))
    if compression == 'tar.bz2':
        archive = tarfile.open(bundle.name, 'r:bz2')
        _store_bundle_files(archive.getnames())
    elif compression == 'tar.gz':
        archive = tarfile.open(bundle.name, 'r:gz')
        _store_bundle_files(archive.getnames())
    elif compression == 'zip':
        archive = zipfile.ZipFile(bundle.name, 'r')
        _store_bundle_files(archive.namelist())
    else:
        logging.error('Unsupported compression format: "{}"'.format(
            compression))
        sys.exit(1)

    try:
        LOGGER.info('Unpacking {} to /'.format(bundle.name))
        archive.extractall('/')
    finally:
        archive.close()

    # Remove the downloaded package
    LOGGER.info("Removing temporary file {}".format(bundle.name))
    os.remove(bundle.name)


def _get_key(bundle_type):
    """ Returns the bundle key

    :type bundle_type: str
    :param bundle_type: Bundle type to download
    :returns: (boto.s3.key, str) -- (S3 key object, compression type)
    """
    LOGGER.debug("Connecting to AWS S3")
    connection = s3.connect_to_region(
        CONFIG.get('metadata', 'region'),
        aws_access_key_id=CONFIG.get('metadata', 'access-key-id'),
        aws_secret_access_key=CONFIG.get('metadata', 'secret-access-key'))

    # Get the relevant bucket
    bucket_name = CONFIG.get('metadata', 'bundle-bucket')
    LOGGER.debug('Using bucket {}'.format(bucket_name))
    bucket = connection.get_bucket(bucket_name)

    # Download the bundle
    for compression in ['tar.bz2', 'tar.gz', 'zip']:
        key_name = (
            '{env}/{version}/bundle-{env}-{version}-{bundle}.{comp}'.format(
                env=CONFIG.get('metadata', 'environment'),
                version=CONFIG.get('metadata', 'version'),
                bundle=bundle_type,
                comp=compression))
        LOGGER.debug('Looking for bundle {}'.format(key_name))
        key = bucket.get_key(key_name)

        # When we have found a key, don't look any more
        if key:
            LOGGER.debug('Found bundle: {}'.format(key_name))
            return key
        LOGGER.debug('Bundle not found: {}'.format(key_name))

    return (None, None)


def _remove_old_files():
    """ Remove files from previous bundle """
    cache_file = '/var/local/cumulus-bundle-handler.cache'

    if not os.path.exists(cache_file):
        LOGGER.info('No previous bundle files to clean up')
        return

    LOGGER.info('Removing old files and directories')

    with open(cache_file, 'r') as file_handle:
        for line in file_handle.readlines():
            line = line.replace('\n', '')

            if not os.path.exists(line):
                continue

            if os.path.isdir(line):
                try:
                    os.removedirs(line)
                    LOGGER.debug('Removing directory {}'.format(line))
                except OSError:
                    pass
            elif os.path.isfile(line):
                LOGGER.debug('Removing file {}'.format(line))
                os.remove(line)

                try:
                    os.removedirs(os.path.dirname(line))
                except OSError:
                    pass
            elif os.path.islink(line):
                LOGGER.debug('Removing link {}'.format(line))
                os.remove(line)

                try:
                    os.removedirs(os.path.dirname(line))
                except OSError:
                    pass
            else:
                LOGGER.warning('Unknown file type {}'.format(line))

    # Remove the cache file when done
    os.remove(cache_file)


def _run_command(command):
    """ Run arbitary command

    :type command: str
    :param command: Command to execute
    """
    LOGGER.info('Executing command: {}'.format(command))

    cmd = subprocess.Popen(
        command,
        shell=True,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE)

    stdout, stderr = cmd.communicate()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)

    if cmd.returncode != 0:
        LOGGER.error('Command "{}" returned non-zero exit code {}'.format(
            command,
            cmd.returncode))
        sys.exit(cmd.returncode)


def _run_init_scripts(start=False, kill=False, other=False):
    """ Execute scripts in /etc/cumulus-init.d

    :type start: bool
    :param start: Run scripts starting with S
    :type kill: bool
    :param kill: Run scripts starting with K
    :type others: bool
    :param others: Run scripts not starting with S or K
    """
    init_dir = '/etc/cumulus-init.d'

    # Run the post install scripts provided by the bundle
    if not os.path.exists(init_dir):
        LOGGER.info('No init scripts found in {}'.format(init_dir))
        return

    LOGGER.info('Running init scripts from {}'.format(init_dir))

    filenames = []
    for filename in os.listdir(init_dir):
        if os.path.isfile(os.path.join(init_dir, filename)):
            filenames.append(os.path.join(init_dir, filename))

    if start:
        for filename in filenames:
            if os.path.basename(filename)[0] == 'S':
                _run_command(os.path.abspath(filename))

    if kill:
        for filename in filenames:
            if os.path.basename(filename)[0] == 'K':
                _run_command(os.path.abspath(filename))

    if other:
        for filename in filenames:
            if os.path.basename(filename)[0] not in ['K', 'S']:
                _run_command(os.path.abspath(filename))


def _store_bundle_files(filenames):
    """ Store a list of bundle paths

    :type filenames: list
    :param filenames: List of full paths for all paths in the bundle
    """
    cache_file = '/var/local/cumulus-bundle-handler.cache'

    file_handle = open(cache_file, 'a')
    try:
        for filename in filenames:
            if not filename:
                continue

            if filename[0] != '/':
                filename = '/{}'.format(filename)

            file_handle.write('{}\n'.format(filename))

        LOGGER.debug('Stored bundle information in {}'.format(cache_file))
    finally:
        file_handle.close()


if __name__ == '__main__':
    main()
    sys.exit(0)

sys.exit(1)
