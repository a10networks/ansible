#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, A10 Networks Inc.
# GNU General Public License v3.0
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = r'''
---
module: acos_config
short_description: Manage A10 ACOS device configuration
description:
  - A10 ACOS configurations use a simple block indent file syntax
    for segmenting configuration into sections.  This module provides
    an implementation for working with ACOS configuration sections.
notes:
  - Tested against ACOS 4.1.1-P9
  - Abbreviated commands are NOT idempotent, see
    L(Network FAQ,../network/user_guide/faq.html#why-do-the-config-modules-
      always-return-changed-true-with-abbreviated-commands).
options:
  lines:
    description:
      - The ordered set of commands that should be configured in the
        section.  The commands must be the exact same commands as found
        in the device running-config.  Be sure to note the configuration
        command syntax as some commands are automatically modified by the
        device config parser.
    aliases: ['commands']
  intended_config:
    description:
      - The ordered set of commands that is checked with the commands given
        under lines. The intended set is compared with 'lines' set. The
        intended commands that is not part of line commands set are
        returned.
  file_path:
    description:
      - Specifies the source path to the file that contains the configuration
        or configuration template to load.  The path to the source file can
        either be the full path on the Ansible control host or a relative
        path from the playbook or role root directory.
  backup:
    description:
      - This argument will cause the module to create a full backup of
        the current C(running-config) from the remote device before any
        changes are made. If the C(backup_options) value is not given,
        the backup file is written to the C(backup) folder in the playbook
        root directory or role root directory, if playbook is part of an
        ansible role. If the directory does not exist, it is created.
    type: bool
    default: 'no'
  defaults:
    description:
      - This argument specifies whether or not to collect all defaults
        when getting the remote device running config.  When enabled,
        the module will get the current config by issuing the command
        C(show running-config all).
    type: bool
    default: 'no'
  before:
    description:
      - The ordered set of commands to push on to the command stack if
        a change needs to be made.  This allows the playbook designer
        the opportunity to perform configuration commands prior to pushing
        any changes without affecting how the set of commands are matched
        against the system.
  after:
    description:
      - The ordered set of commands to append to the end of the command
        stack if a change needs to be made.  Just like with I(before) this
        allows the playbook designer to append a set of commands to be
        executed after the command set.
  diff_ignore_lines:
    description:
      - Use this argument to specify one or more lines that should be ignored
        while running the check between running config and lines sets. This
        is used for lines in the configuration that are automatically updated
        by the system. This argument takes a list of commands.
  save_when:
    description:
      - When changes are made to the device running-configuration, the
        changes are not copied to non-volatile storage by default.  Using
        this argument will change that before.  If the argument is set to
        I(always), then the running-config will always be copied to the
        startup-config and the I(modified) flag will always be set to
        True.  If the argument is set to I(modified), then the running-config
        will only be copied to the startup-config if it has changed since
        the last save to startup-config.  If the argument is set to
        I(never), the running-config will never be copied to the
        startup-config.  If the argument is set to I(changed), then the
        running-config will only be copied to the startup-config if the task
        has made a change.
    default: never
    choices: ['always', 'never', 'modified', 'changed']
  backup_options:
    description:
      - This is a dict object containing configurable options related to
        backup file path.
        The value of this option is read only when C(backup) is set to I(yes),
        if C(backup) is set to I(no) this option will be silently ignored.
    suboptions:
      filename:
        description:
          - The filename to be used to store the backup configuration. If the
            filename is not given it will be generated based on the hostname,
            current time and date in format defined by
            <hostname>_config.<current-date>@<current-time>
      dir_path:
        description:
          - This option provides the path ending with directory name in which
            the backup configuration file will be stored. If the directory
            does not exist it will be first created and the filename is either
            the value of C(filename) or default filename as described in
            C(filename) options description. If the path value is not given in
            that case a I(backup) directory will be created in the current
            working directory and backup configuration will be copied in
            C(filename) within I(backup) directory.
        type: path
    type: dict
  diff_against:
    description:
      - Possible value is 'startup'. Provides output as difference between
        running config and startup config. Configuration set that is part of
        startup config but not part of running config is returned.
    choices: ['running', 'startup', 'intended']
'''

EXAMPLES = r'''
- name: simple loadbalancer create commands
  acos_config:
    lines:
      - ip dns primary 8.8.4.7
      - slb template http slb-http-test
      - slb server server1-test 6.6.5.6
      - port 80 tcp
      - slb server server2-test 5.5.5.11
      - port 80 tcp
      - slb service-group sgtest-1 tcp
      - member rs1-test 80
      - member rs2-test 80
      - slb virtual-server viptest1 2.2.2.3
      - port 80 http

- name: configure from file
  acos_config:
    file_path: "/root/sampleSlbConfiguration.txt"

- name: save running to startup when modified
  acos_config:
    save_when: modified

- name: configurable backup path
  acos_config:
    default: true
    backup: yes
    backup_options:
      filename: backup.cfg
      dir_path: /home/user

- name: run lines
  acos_config:
    lines:
      - ip dns primary 10.10.10.55
      - slb template http abc-config
  check_mode: yes
'''

RETURN = r'''
commands:
  description: The set of commands that will be pushed to the remote device
  returned: always
  type: list
  sample: ['hostname foo', 'router ospf 1', 'router-id 192.0.2.1']
backup_path:
  description: The full path to the backup file
  returned: when backup is yes
  type: str
  sample: /playbooks/ansible/backup/acos_config.2016-07-16@22:28:34
filename:
  description: The name of the backup file
  returned: when backup is yes and filename is not specified in backup options
  type: str
  sample: acos_config.2016-07-16@22:28:34
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.a10.acos import get_config, run_commands
from ansible.module_utils.network.a10.acos import backup, get_connection
from ansible.module_utils.network.common.config import NetworkConfig, dumps


def check_args(module, warnings):
    if module.params['multiline_delimiter']:
        if len(module.params['multiline_delimiter']) != 2:
            module.fail_json(msg='multiline_delimiter value can only be one'
                                 'or two characters')


def edit_config_or_macro(connection, commands):
    connection.edit_config(candidate=commands)


def get_candidate_config(module):
    candidate = ''
    if module.params['lines']:
        candidate_obj = NetworkConfig(indent=1)
        parents = module.params['parents'] or list()
        candidate_obj.add(module.params['lines'], parents=parents)
        candidate = dumps(candidate_obj, 'raw')
    return candidate


def get_intended_config(module):
    intended_lines = module.params['intended_config']
    intended_obj_list = list()
    for line in intended_lines:
        intended_obj_list.append(str(line.strip()))
    return intended_obj_list


def get_list_from_params(command_lines):
    candidate_obj_list = list()
    if command_lines:
        for line in command_lines:
            candidate_obj_list.append(str(line.strip()))
    return candidate_obj_list


def get_running_config(module, current_config=None, flags=None):
    running = module.params['running_config']
    if not running:
        if not module.params['defaults'] and current_config:
            running = current_config
        else:
            running = get_config(module, flags=flags)

    return running


def save_config(module):
    if not module.check_mode:
        run_commands(module, 'write memory\r')
    else:
        module.warn('Skipping command `write memory` '
                    'due to check_mode.  Configuration not copied to '
                    'non-volatile storage')


def get_diff(intended_config, candidate_config, diff_ignore_lines):
    diff = list()
    ignore_list = [
        '',
        '!',
        'exit-module',
        'Show default startup-config',
        'Building configuration...'
    ]
    for item in intended_config:
        if not item.startswith('!'):
            if item not in candidate_config and item not in ignore_list:
                diff.append(str(item))
    if diff_ignore_lines:
        diff = [x for x in diff if x not in diff_ignore_lines]
    return diff


def configuration_to_list(configuration):
    sanitized_config_list = list()
    config_list = configuration[0].split('\n')
    for line in config_list:
        if not line.startswith('!'):
            sanitized_config_list.append(line.strip())
    return sanitized_config_list


def main():
    """ main entry point for module execution
    """
    backup_spec = dict(
        filename=dict(),
        dir_path=dict(type='path')
    )
    argument_spec = dict(
        src=dict(type='path'),

        lines=dict(aliases=['commands'], type='list'),
        intended_config=dict(aliases=['commands'], type='list'),
        parents=dict(type='list'),

        before=dict(type='list'),
        after=dict(type='list'),

        match=dict(default='line', choices=['line', 'strict',
                                            'exact', 'none']),
        replace=dict(default='line', choices=['line', 'block']),
        multiline_delimiter=dict(default='/n'),

        running_config=dict(aliases=['config']),

        defaults=dict(type='bool', default=False),
        backup=dict(type='bool', default=False),
        backup_options=dict(type='dict', options=backup_spec),
        save_when=dict(choices=['always', 'never', 'modified', 'changed'],
                       default='never'),

        diff_against=dict(choices=['startup']),
        diff_ignore_lines=dict(type='list'),
        file_path=dict(type='path')

    )


    mutually_exclusive = [('lines', 'src'),
                          ('parents', 'src')]

    required_if = [('match', 'strict', ['lines']),
                   ('match', 'exact', ['lines']),
                   ('replace', 'block', ['lines'])]

    module = AnsibleModule(argument_spec=argument_spec,
                           mutually_exclusive=mutually_exclusive,
                           required_if=required_if,
                           supports_check_mode=True)

    result = {'changed': False}

    warnings = list()
    check_args(module, warnings)
    result['warnings'] = warnings

    diff_ignore_lines = module.params['diff_ignore_lines']
    contents = None
    flags = 'with-default' if module.params['defaults'] else []
    connection = get_connection(module)

    before_config_list = configuration_to_list(run_commands(module,
                                               'show running-config'))

    if module.params['file_path']:
        try:
            configuration_file = open(module.params["file_path"], 'r')
            command_lines = configuration_file.readlines()
            configuration_file.close()
            run_commands(module, 'configure')
            for line in command_lines:
                if not line.startswith('!'):
                    run_commands(module, line.strip())
            run_commands(module, 'exit')
        except IOError as e:
            module.fail_json(msg="File Not Found!")

    if module.params['backup'] or (module._diff and
                                   module.params['diff_against'] == 'running'):
        contents = get_config(module, flags=flags)
        if module.params['backup']:
            result['__backup__'] = contents
            backup(module, contents)

    if module.params['lines']:
        candidate = get_candidate_config(module)

        config_diff = candidate

        if config_diff:
            commands = config_diff.split('\n')

            if module.params['before']:
                commands[:0] = module.params['before']

            if module.params['after']:
                commands.extend(module.params['after'])

            result['commands'] = commands
            result['updates'] = commands

            # send the configuration commands to the device and merge
            # them with the current running config
            if not module.check_mode:
                if commands:
                    edit_config_or_macro(connection, commands)
                    result['changed'] = True

    # for comparing running config with candidate config
    running_config_list = configuration_to_list(run_commands(module,
                                                'show running-config'))
    startup_config_list = configuration_to_list(run_commands(module,
                                                'show startup-config'))

    candidate_lines = get_list_from_params(module.params['lines'])
    diff_ignore_lines_list = get_list_from_params(diff_ignore_lines)
    difference = get_diff(intended_config=candidate_lines,
                          candidate_config=running_config_list,
                          diff_ignore_lines=diff_ignore_lines_list)
    if len(difference) != 0:
        module.warn('Could not execute following commands or command does not'
                    ' exist in running config after execution. check'
                    'on ACOS device:' + str(difference))

    # intended_config
    if module.params['intended_config']:
        intended_config_list = get_intended_config(module)
        found_diff = get_diff(intended_config_list, candidate_lines,
                              diff_ignore_lines_list)
        if len(found_diff) != 0:
            result.update({
                'success': False,
                'failed_diff_lines_between_intended_candidate': found_diff
            })
        else:
            result.update({
                'success': True
            })

    running_config = ''
    startup_config = None

    if module.params['save_when'] == 'always':
        save_config(module)
    elif module.params['save_when'] == 'modified':
        output = run_commands(module,
                              ['show running-config', 'show startup-config'])

        running_config = NetworkConfig(indent=1, contents=output[0],
                                       ignore_lines=diff_ignore_lines)
        startup_config = NetworkConfig(indent=1, contents=output[1],
                                       ignore_lines=diff_ignore_lines)

        if running_config.sha1 != startup_config.sha1:
            save_config(module)
    elif module.params['save_when'] == 'changed' and result['changed']:
        save_config(module)

    if module.params['diff_against'] == 'startup':
        difference_with_startup_config = get_diff(startup_config_list,
                                                  running_config_list,
                                                  diff_ignore_lines_list)
        if len(difference_with_startup_config) != 0:
            result.update({
                'diff_against_found': 'yes',
                'changed': True,
                'startup_diff': difference_with_startup_config
            })
        else:
            result.update({
                'diff_against_found': 'no',
                'changed': False,
                'startup_diff': None
            })

    after_config_list = configuration_to_list(run_commands(module,
                                              'show running-config'))
    diff = list(set(after_config_list)-set(before_config_list))
    if len(diff) != 0:
        result['changed'] = True
    else:
        result['changed'] = False

    module.exit_json(**result)

if __name__ == '__main__':
    main()
