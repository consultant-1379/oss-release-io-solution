"""
Server Connection operator
"""
import socket
import logging
import paramiko


class SFTPServerConnection:
    """
    Class for connecting to Server in order to perform SFTP operations
    """
    def __init__(self, server_ip, user_name, pem_file):
        self.connection = paramiko.SSHClient()
        self.connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.__create_shell_server_connection__(server_ip, user_name, pem_file)

    def copy_file_via_sftp(self, source_path, destination_path):
        """
        Method to copy file via sftp
        :param source_path: source file path
        :param destination_path: destination file path
        :rtype: void
        """
        sftp = self.connection.open_sftp()
        sftp.put(source_path, destination_path)
        sftp.close()

    def __create_shell_server_connection__(self, server_ip, user_name, pem_file):
        """
        sets up SFTP server connection
        :param server_ip:
        :param user_name:
        :param pem_file:
        :rtype: void
        """
        try:
            logging.debug('Connecting with server :%s ', server_ip)
            self.connection.connect(hostname=server_ip, username=user_name, key_filename=pem_file, look_for_keys=False)
            logging.debug('Connected with server : %s ', server_ip)
        except paramiko.AuthenticationException as exception:
            logging.debug(exception)
            logging.error("Login issue: Please check the pem_file, %s ", server_ip)
            logging.debug('Script terminated due to error printed above. | AuthenticationException')
            raise
        except socket.error as exception:
            logging.debug(exception)
            logging.error("Connection refused with server :%s ", server_ip)
            logging.debug('Script terminated due to error printed above. | socket error or AuthenticationException')
            raise
        except paramiko.SSHException as exception:
            logging.debug(exception)
            logging.error("Login issue: Please check the pem_file , %s ", server_ip)
            logging.debug('Script terminated due to error printed above. | SshException')
            raise

    def __del__(self):
        """Closes connection"""
        logging.debug('Connection closed with server ')
        self.connection.close()
