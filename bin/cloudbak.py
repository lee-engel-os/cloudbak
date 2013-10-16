#!/usr/bin/python

from boto.s3.connection import S3Connection
import datetime
import getpass
from ConfigParser import SafeConfigParser
import logging
import os, os.path
import re
import shlex
import socket
from subprocess import call
import sys
import warnings

class cloudbak:
    args = None
    version = '0.1-alpha' #Build process should add this here

    aws_secret = None
    aws_id = None
    aws = None

    buckets = dict()
    backup_dirs = []

    config = None
    
    def __init__(self):
        self.handle_args()
        self.process_config()
        self.setup_logging()

        logging.info("Cloudback v%s - config: %s", self.version, self.args.configfile)

        if len(self.backup_dirs) < 1:
            logging.info("Could not find any directories to back up in the config file. exiting quietly")
            return None

        self.aws = S3Connection(self.aws_id, self.aws_secret)

        self.process_buckets()
        self.process_backups()

    def setup_logging(self):
        if not self.config.has_section('logging'):
            return None

        levels = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL, 'DEFAULT': logging.INFO}

        loglevel = levels['DEFAULT']
        logfile = '/var/log/cloudbak.log'
        format = '%(asctime)s - %(levelname)s - %(message)s'

        if self.config.has_option('logging', 'loglevel'):
            loglevel = levels[self.config.get('logging', 'loglevel').upper()]

        if self.config.has_option('logging', 'logfile'):
            logfile = self.config.get('logging', 'logfile')

        if self.config.has_option('logging', 'format'):
            format = self.config.get('logging', 'format')

        logging.basicConfig(filename=logfile, level=loglevel, format=format)

    def handle_args(self):
        #TODO: decide on which opts module to use
        from optparse import OptionParser
        parser = OptionParser(version="Version: %s" % self.version)
        parser.add_option('-c', '--config', dest='configfile', help='configuration file', default='/etc/cloudbak.ini')
        args = parser.parse_args()
        self.args = args[0]

    def process_config(self):
        config = SafeConfigParser()
        config.readfp(open(self.args.configfile, 'r'))

        self.config = config

        #Process aws section
        if config.has_section('aws'):
            self.aws_id = config.get('aws', 'aws_access_key_id')
            self.aws_secret = config.get('aws', 'aws_secret_access_key')
        else:
            raise Exception("You config file does not have a 'global' section.")

        for section in config.sections():
            # we found a bucket definition
            if re.match("^bucket:", section):
                (_t, bucket) = section.split(':')
                self.buckets[bucket] = dict()
                for item in config.items(section):
                    logging.debug("Config - Found bucket definition: %s", bucket)
                    self.buckets[bucket].update({item[0]: item[1]})
            
            # we found a directory to back up
            if os.path.isdir(section):
                logging.debug("Config - Found directory definition: %s", section)
                self.backup_dirs.append(section)

    def process_buckets(self):
        if len(self.buckets) < 1:
            logging.critical("No bucket definitions found. Exiting :-(")
            raise Exception("No bucket definitions found.")

        for bucket in self.buckets:
            if not self.aws.lookup(bucket):
                self.aws.create_bucket(bucket)
                logging.info("Created bucket: %s", bucket)

    def _exec_command(self, cmd):
        pass

    def process_backups(self):
        tmp_dir = '/tmp'
        if self.config.has_option('global','tmp_dir'):
            tmp_dir = self.config.get('global','tmp_dir')

        tar = '/usr/bin/tar'
        tar_opts = '-cvzf'
        username = getpass.getuser()
        hostname = socket.gethostname()
        now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')

        for dir in self.backup_dirs:
            if self.config.has_option(dir, 'enabled') and not self.config.getboolean(dir, 'enabled'):
                continue

            _d = dir.replace('/', '_')
            tarball_name = '%s,%s,%s,%s.tar.gz' % (username, hostname, now, _d)
            tarball_path = '%s/%s' % (tmp_dir, tarball_name)
            cmd = shlex.split('%s %s %s %s' % (tar, tar_opts, tarball_path, dir))

            self._exec_command(cmd)
            print cmd

if __name__ == '__main__':
    warnings.catch_warnings()
    warnings.simplefilter("ignore")

    cbak = cloudbak()
