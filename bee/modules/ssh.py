#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
    @FileName    : d.py
    @Author      : citang
    @Date        : 2021/5/13 9:20 上午
    @Description : description the function of the file
"""
from __future__ import print_function
from bee.modules import BeeService

import os
from twisted.cred import portal, checkers
from twisted.conch import avatar, recvline, interfaces as conchinterfaces
from twisted.conch.ssh import factory, keys, session
from twisted.conch.insults import insults
from twisted.application import internet
from zope.interface import implementer
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

SSH_PATH = "/var/tmp"


class HoneyPotProtocol(recvline.HistoricRecvLine):

    def __init__(self, user, env):
        self.user = user
        self.env = env

    def connectionMade(self):
        recvline.HistoricRecvLine.connectionMade(self)
        self.terminal.write("Welcome to my test SSH server.")
        self.terminal.nextLine()
        self.do_help()
        self.showPrompt()

    def showPrompt(self):
        self.terminal.write("$ ")

    def getCommandFunc(self, cmd):
        """记录操作"""
        self
        log_data = {
            'cmd': bytes.decode(cmd),
            'local_version': self.user.conn.transport.ourVersionString,
            'remote_version': self.user.conn.transport.otherVersionString
        }
        log_type = self.user.factory.beeservice.logger.LOG_SSH_CMD
        log = self.user.factory.beeservice.log
        log(log_data, logtype=log_type,
            src_host=self.env['src_host'],
            src_port=self.env['src_port'],
            dst_host=self.env['dst_host'],
            dst_port=self.env['dst_port'])

        return getattr(self, 'do_' + bytes.decode(cmd), None)

    def lineReceived(self, line):
        line = line.strip()
        if line:
            cmdAndArgs = line.split()
            cmd = cmdAndArgs[0]
            args = cmdAndArgs[1:]
            func = self.getCommandFunc(cmd)
            if func:
                try:
                    func(*args)
                except Exception as e:
                    self.terminal.write("Error: %s" % e)
                    self.terminal.nextLine()
            else:
                self.terminal.write("No such command.")
                self.terminal.nextLine()
        self.showPrompt()

    def do_help(self, cmd=''):
        "Get help on a command. Usage: help command"
        if cmd:
            func = self.getCommandFunc(cmd)
            if func:
                self.terminal.write(func.__doc__)
                self.terminal.nextLine()
                return

        publicMethods = filter(
            lambda funcname: funcname.startswith('do_'), dir(self))
        commands = [cmd.replace('do_', '', 1) for cmd in publicMethods]
        self.terminal.write("Commands: " + " ".join(commands))
        self.terminal.nextLine()

    def do_echo(self, *args):
        "Echo a string. Usage: echo my line of text"
        self.terminal.write(" ".join(args))
        self.terminal.nextLine()

    def do_whoami(self):
        "Prints your user name. Usage: whoami"
        self.terminal.write(self.user.username)
        self.terminal.nextLine()

    def do_quit(self):
        "Ends your session. Usage: quit"
        self.terminal.write("Thanks for playing!")
        self.terminal.nextLine()
        self.terminal.loseConnection()

    def do_clear(self):
        "Clears the screen. Usage: clear"
        self.terminal.reset()


@implementer(portal.IRealm)
class HoneyPotRealm:

    def __init__(self, factory):
        self.factory = factory

    def requestAvatar(self, avatarId, *interfaces):
        if conchinterfaces.IConchUser in interfaces:
            return interfaces[0], HoneyPotAvatar(avatarId, self.factory), lambda: None
        else:
            raise Exception("No supported interfaces found.")


@implementer(conchinterfaces.ISession)
class HoneyPotAvatar(avatar.ConchUser):

    def __init__(self, username, factory):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.factory = factory
        self.channelLookup.update({b'session': session.SSHSession})

    def openShell(self, protocol):
        us = session.SSHSession.getHost(self)
        peer = session.SSHSession.getPeer(self)
        log_data = {
            'USERNAME': self.username,
            'local_version': self.conn.transport.ourVersionString,
            'remote_version': self.conn.transport.otherVersionString}
        log_type = self.factory.beeservice.logger.LOG_SSH_NEW_CONNECTION
        log = self.factory.beeservice.log
        log(log_data, logtype=log_type,
            src_host=peer.address.host,
            src_port=peer.address.port,
            dst_host=us.address.host,
            dst_port=us.address.port)

        env = {
            'src_host': peer.address.host,
            'src_port': peer.address.port,
            'dst_host': us.address.host,
            'dst_port': us.address.port,
        }

        serverProtocol = insults.ServerProtocol(HoneyPotProtocol, self, env)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))

    def getPty(self, terminal, windowSize, attrs):
        return None

    def execCommand(self, protocol, cmd):
        raise NotImplementedError

    def closed(self):
        pass


def getRSAKeys():
    public_key = os.path.join(SSH_PATH, 'id_rsa.pub')
    private_key = os.path.join(SSH_PATH, 'id_rsa')

    if not (os.path.exists(public_key) and os.path.exists(private_key)):
        ssh_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend())
        public_key_string = ssh_key.public_key().public_bytes(
            serialization.Encoding.OpenSSH,
            serialization.PublicFormat.OpenSSH)
        private_key_string = ssh_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption())
        with open(public_key, 'w+b') as key_file:
            key_file.write(public_key_string)

        with open(private_key, 'w+b') as key_file:
            key_file.write(private_key_string)
    else:
        with open(public_key) as key_file:
            public_key_string = key_file.read()
        with open(private_key) as key_file:
            private_key_string = key_file.read()

    return public_key_string, private_key_string


class HoneyPotSSHFactory(factory.SSHFactory):

    def __init__(self, logger=None, version=None):
        self.sessions = {}
        self.logger = logger
        self.version = version


class BeeSSH(BeeService):
    NAME = 'ssh'

    def __init__(self, config=None, logger=None):
        BeeService.__init__(self, config=config, logger=logger)
        self.port = int(config.getVal("ssh.port", default=223))
        self.version = config.getVal("ssh.version", default="SSH-2.0-OpenSSH_5.1p1 Debian-5").encode('utf8')
        self.listen_addr = config.getVal('device.listen_addr', default='')

    def getService(self):
        factory = HoneyPotSSHFactory(version=self.version, logger=self.logger)
        factory.beeservice = self
        factory.portal = portal.Portal(HoneyPotRealm(factory))

        users = {'admin': b'aaa', 'guest': b'bbb'}
        factory.portal.registerChecker(checkers.InMemoryUsernamePasswordDatabaseDontUse(**users))

        rsa_pubKeyString, rsa_privKeyString = getRSAKeys()
        factory.publicKeys = {b'ssh-rsa': keys.Key.fromString(data=rsa_pubKeyString)}
        factory.privateKeys = {b'ssh-rsa': keys.Key.fromString(data=rsa_privKeyString)}
        return internet.TCPServer(self.port, factory, interface=self.listen_addr)

