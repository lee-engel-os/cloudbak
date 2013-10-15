#!/usr/bin/python

from boto.s3.connection import S3Connection
import datetime
import getpass
from ConfigParser import SafeConfigParser
import os, os.path
import re
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

        self.aws = S3Connection(self.aws_id, self.aws_secret)

        self.process_buckets()
        self.process_backups()

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

        #Process global section
        if config.has_section('global'):
            self.aws_id = config.get('global', 'aws_access_key_id')
            self.aws_secret = config.get('global', 'aws_secret_access_key')
        else:
            raise Exception("You config file does not have a 'global' section.")

        for section in config.sections():
            # we found a bucket definition
            if re.match("^bucket:", section):
                (_t, bucket) = section.split(':')
                self.buckets[bucket] = dict()
                for item in config.items(section):
                    self.buckets[bucket].update({item[0]: item[1]})
            
            # we found a directory to back up
            if os.path.isdir(section):
                self.backup_dirs.append(section)

    def process_buckets(self):
        for bucket in self.buckets:
            if not self.aws.lookup(bucket):
                self.aws.create_bucket(bucket)

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
            _d = dir.replace('/', '_')
            tarball_name = '%s,%s,%s,%s.tar.gz' % (username, hostname, now, _d)
            tarball_path = '%s/%s' % (tmp_dir, tarball_name)
            cmd = '%s %s %s %s' % (tar, tar_opts, tarball_path, dir)
            print cmd

if __name__ == '__main__':
    warnings.catch_warnings()
    warnings.simplefilter("ignore")

    cbak = cloudbak()
