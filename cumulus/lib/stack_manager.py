""" Manager """
import json
import logging
import os.path
import sys

import boto

import connection_handler

logger = logging.getLogger(__name__)


def _get_json_from_template(template):
    """ Returns a JSON string given a template file path

    :type template: str
    :param template: Template path to use
    :returns: JSON object
    """
    file_handle = open(template)
    json_data = json.dumps(json.loads(file_handle.read()))
    file_handle.close()
    return json_data


def ensure_stack(stack, environment, template, disable_rollback=False):
    """ Ensure stack is up and running (create or update it)

    :type stack: str
    :param stack: Stack name
    :type environment: str
    :param environment: Environment name
    :type template: str
    :param template: Template path to use
    :type disable_rollback: bool
    :param disable_rollback: Should rollbacks be disabled?
    """
    connection = connection_handler.connect_cloudformation()
    logger.info('Creating stack {} with template {}'.format(
        stack, os.path.basename(template)))

    try:
        if stack in connection.list_stacks():
            connection.update_stack(
                stack,
                template_body=_get_json_from_template(template),
                disable_rollback=disable_rollback,
                capabilities=['CAPABILITY_IAM'])
        else:
            connection.create_stack(
                stack,
                template_body=_get_json_from_template(template),
                disable_rollback=disable_rollback,
                capabilities=['CAPABILITY_IAM'])

        logger.info(
            'CloudFormation is now ensuring your stack. '
            'Please see the AWS Console for mode details.')
    except ValueError, error:
        logger.error('Malformatted template: {}'.format(error))
        sys.exit(1)
    except boto.exception.BotoServerError, error:
        logger.error("ERROR - Boto exception: {}".format(error))
        logger.error("Enable debug in manage.py to see more details")


#def delete_stack(stack, environment):
#    """ Delete an existing stack
#
#    :type stack: str
#    :param stack: Stack name
#    :type environment: str
#    :param environment: Environment name
#    """
#    connection = connection_handler.connect_cloudformation()
#    logger.info('Deleting stack {}'.format(stack))
#    connection.delete_stack()
#
#
#def list_stacks(environment):
#    """ List stacks in the environment
#
#    :type environment: str
#    :param environment: Environment name
#    """
#    connection = connection_handler.connect_cloudformation()
#    logger.info('Current stacks: {}'.format(
#        ', '.join(connection.list_stacks())))
#
#
#def validate_template(environment, template):
#    """ Validate the template
#
#    :type environment: str
#    :param environment: Environment name
#    :type template: str
#    :param template: Template path to use
#    """
#    connection = connection_handler.connect_cloudformation()
#    result = connection.validate_template(_get_json_from_template(template))
#    if result:
#        logger.info('Template {} is valid'.format(os.path.basename(template)))
