""" Cumulus init """
import config_handler
import logging.config

import bundler
import stack_manager

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format':
            '%(asctime)s - cumulus - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        },
        'lib.bundler': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
        'lib.config_handler': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
        'lib.connection_handler': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
        'lib.stack_manager': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
})


def main():
    """ Main function """
    config_handler.configure()

    if config_handler.args.bundle:
        bundler.build_bundles()

    if config_handler.args.deploy:
        for stack in config_handler.get_stacks():
            stack_manager.ensure_stack(
                stack,
                config_handler.get_environment(),
                config_handler.get_stack_template(stack),
                disable_rollback=config_handler.get_stack_disable_rollback(
                    stack),
                parameters=config_handler.get_stack_parameters(stack))

    if config_handler.args.undeploy:
        message = (
            'This will DELETE all stacks in the environment. '
            'This action cannot be undone. '
            'Are you sure you want to do continue? [N/y] ')
        choice = raw_input(message).lower()
        if choice in ['yes', 'y']:
            for stack in config_handler.get_stacks():
                stack_manager.delete_stack(stack)
        else:
            print('Skipping undeployment.')

    if config_handler.args.validate_templates:
        stack_manager.validate_templates()
