"""
Module contains the SSH Shell class
"""
import logging
import re
import socket

import paramiko


class SshShell:
    """
    Activates a shell to a target host which can be used to run commands on another host over SSH
    """
    def __init__(self, target_host, user, pem_file):
        """
        Initializes the shell to the target host
        :param target_host:
        :param user:
        :param pem_file:
        """
        try:
            logging.info(f'Connecting with server: {target_host}')
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(target_host, username=user, key_filename=pem_file, port=22)
            channel = self.ssh.invoke_shell()
            self.stdin = channel.makefile('wb')
            self.stdout = channel.makefile('r')
            logging.info(f'Connected with server: {target_host}')

        except paramiko.AuthenticationException as exception:
            logging.debug(exception)
            logging.error('Authentication issue: Please check the pem_file')
            raise
        except socket.error as exception:
            logging.debug(exception)
            logging.error('Connection refused with server: {host}')
            raise
        except paramiko.SSHException as exception:
            logging.debug(exception)
            logging.error('Login issue: Please check the pem_file')
            raise

    def run_command(self, command_to_run):
        """
        :param command_to_run: the command to be executed on the remote computer
        :examples:  execute('ls')
                    execute('helm ls')
                    execute('cd folder_name')
        """
        logging.info(f'Executing the command: {command_to_run}')
        command_to_run = command_to_run.strip('\n')
        self.stdin.write(command_to_run + '\n')
        command_finished_identifier = 'end of stdOUT buffer. finished with exit status'
        echo_cmd = 'echo {} $?'.format(command_finished_identifier)
        self.stdin.write('\n' + echo_cmd + '\n')
        self.stdin.flush()

        shout, sherr, exit_code = self.__cleanup_command_output_and_get_exit_code__(
            command_to_run, echo_cmd, command_finished_identifier)

        if exit_code != 0:
            logging.error(f"Command not executed correctly. EXIT_CODE: {exit_code}. STDERR:"
                          f"{self.__shell_output_handler__(sherr)}.")

        return self.__shell_output_handler__(shout)

    def __cleanup_command_output_and_get_exit_code__(self, command_to_run, echo_cmd,
                                                     command_finished_identifier):
        """
        After running a command, it goes through shout to parse out the actual command output and
        get the command exit code
        :param command_to_run:
        :param echo_cmd:
        :param command_finished_identifier:
        :return: shout, sherr, exit_code
        """
        shout = []
        sherr = []
        exit_code = 0
        for line in self.stdout:
            if str(line).startswith(command_to_run) or str(line).startswith(echo_cmd):
                # up for now filled with shell junk from stdin
                shout = []
            elif str(line).startswith(command_finished_identifier):
                # our finish command ends with the exit status
                exit_code = int(str(line).rsplit(' ', 1)[1])
                if exit_code:
                    # stderr is combined with stdout.
                    # thus, swap sherr with shout in a case of failure.
                    sherr = shout
                    shout = []
                break
            elif " closed." in str(line):
                break
            elif str(line) == "logout":
                break
            else:
                # get rid of 'coloring and formatting' special characters
                shout.append(re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).
                             replace('\b', '').replace('\r', ''))

        # first and last lines of shout/sherr contain a prompt
        if shout and echo_cmd in shout[-1]:
            shout.pop()
        if shout and command_to_run in shout[0]:
            shout.pop(0)
        if sherr and echo_cmd in sherr[-1]:
            sherr.pop()
        if sherr and command_to_run in sherr[0]:
            sherr.pop(0)

        return shout, sherr, exit_code

    @staticmethod
    def __shell_output_handler__(list_of_output_lines_unformatted):
        """
        Method to format output returned by run_command function
        :param list_of_output_lines_unformatted:
        :return: formatted str
        :rtype: str
        """
        formatted_str = ''.join(list_of_output_lines_unformatted)
        return formatted_str

    def __del__(self):
        self.ssh.close()
