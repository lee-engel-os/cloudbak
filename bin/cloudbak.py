#!/usr/bin/python

from boto.s3.connection import S3Connection
import datetime
import getpass
import hashlib
from ConfigParser import SafeConfigParser
import logging
import os, os.path
import re
import shlex
import socket
import subprocess
from subprocess import call, Popen, PIPE
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

    def start_backups(self):
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
        format = '%(asctime)s - %(levelname)s - PID=%(process)d - %(message)s'

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
            raise Exception("You config file does not have a 'aws' section.")

        for section in config.sections():
            # we found a bucket definition
            if re.match("^bucket:", section):
                (_t, bucket) = section.split(':')
                self.buckets[bucket] = dict()
                for item in config.items(section):
                    self.buckets[bucket].update({item[0]: item[1]})
            
            # we found a directory to back up
            if os.path.isdir(section):
                if self.config.has_option(section, 'enabled') and not self.config.getboolean(section, 'enabled'):
                    continue

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
        logging.debug("About to exec %s", cmd)

        child = Popen(cmd, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = child.communicate()

        logging.debug("PID for command %s is %s", cmd, child.pid)
        logging.debug("STDOUT for PID %s: %s", child.pid, stdout)
        logging.debug("STDERR for PID %s: %s", child.pid, stderr)
        logging.debug("Command %s completed.", cmd)

        return child

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
            cmd = shlex.split('%s %s %s %s' % (tar, tar_opts, tarball_path, dir))

            proc = self._exec_command(cmd)

            if proc.returncode <> 0:
                logging.critical("Tar command returned non-zero return code: %s - will not be uploading this tarball.", proc.returncode)
                warnings.warn("While creating tarball for %s the tar command returned %s", dir, proc.returncode)
                continue

            logging.info("Created tarball %s from directory %s", tarball_path, dir)

            st_size = os.stat(tarball_path)[6]
            md5hash = hashlib.md5(tarball_path).hexdigest()
            key = '/%s/%s/%s' % (username, hostname, datetime.datetime.now().strftime('%Y/%m/%d/%H:%M:%S/'))
            key += '%s/%s|%s' % (md5hash, st_size, os.path.basename(tarball_path))

            logging.debug("Key: %s", key)

            # Do the upload here
            # Ask AWS S3 if the file exists

            os.remove(tarball_path)
            logging.info("Deleted tarball %s", tarball_path)

if __name__ == '__main__':
    warnings.catch_warnings()
    warnings.simplefilter("ignore",category=DeprecationWarning)

    cbak = cloudbak()
    cbak.start_backups()
