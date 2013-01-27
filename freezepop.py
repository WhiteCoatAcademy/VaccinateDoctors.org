#!/usr/bin/env python
# Freeze Flask as static files & deploy to S3, which backs CloudFront.
#
# Author: semenko
#
""" Auto-deploy Frozen Flask sites to S3-backed CloudFront. """

import argparse
import gzip
import imp
import os
import StringIO
import subprocess
import sys
import time

from base64 import b64encode
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from flask_frozen import Freezer
from hashlib import md5


def main():
    """
    Freeze Vaccinate Your Doctors and resync S3 staging/prod stores.
    """

    parser = argparse.ArgumentParser(description='The Vaccinate Your Doctors S3/AWS management script.')

    parser.add_argument('--test', '-t', action='store_true', default=False,
                        dest='freeze_only',
                        help='Test the freeze results. Will NOT deploy.')

    parser.add_argument('--deploy', '-d', action='store_true', default=False,
                        dest='deploy',
                        help='Deploy staging and prod to S3. Will NOT test.')

    parser.add_argument('--no-delete', action='store_true', default=False,
                        dest='no_delete',
                        help='Don\'t delete orphan S3 files.')

    parser.add_argument('--overwrite-all', action='store_true', default=False,
                        dest='overwrite_all',
                        help='Overwrite everything. Useful if metadata changes.')

    parser.add_argument('--no-freeze', action='store_true', default=False,
                        dest='no_freeze',
                        help='Don\'t freeze Flask app first (assumes build/ is current)')

    args = parser.parse_args()

    # Special IAM user: vyd-deploy-bot
    with open('.awskey', 'r') as secret_key:
        os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAJB3TQFWKVRVAV46Q'
        os.environ['AWS_SECRET_ACCESS_KEY'] = secret_key.readline()

    if args.deploy or args.freeze_only:
        # Some flag constraints.
        assert((args.deploy and not args.freeze_only) or (args.freeze_only and not args.no_freeze))

        # Freeze Vaccinate Your Doctors
        # Per internal app configs, these make "frozen" static copies of these apps in:
        #    ./vyd_frozen/
        if not args.no_freeze:
            print("Freezing Vaccinate Your Doctors app ...")
            print("*** Look for errors here ***")
            vyd = imp.load_source('vyd', 'vyd.py')
            frozen_vyd = Freezer(vyd.app)

            # Targets required for URL generators for Flask static.
            targets = vyd.targets

            @frozen_vyd.register_generator
            def localized_branding():
                for target in targets:
                    yield {'target': target}

            frozen_vyd.freeze()
            print("")
        else:
            print('*** Skipping Flask freeze. Are you sure you wanted that?')

        print('*** Freeze complete!')
        time.sleep(1)

        print('*** Minifying results, including JS and CSS.')
        subprocess.call(['java', '-jar', 'htmlcompressor-1.5.3.jar', '--recursive',
                         '--compress-js', '--compress-css',                 # Compress CSS and JS
                         '--remove-script-attr', '--remove-style-attr',     # Remove unnecessary attributes
                         'vyd_frozen/', '-o', 'vyd_frozen/'])

        # Push the frozen apps above to S3, if we want.
        if args.deploy:
            #### Connect to S3
            print('Connecting to AWS...\n')
            conn = S3Connection()

            # Deploy: (conn, frozen_path, remote_bucket)
            deploy_to_s3(conn, 'vyd_frozen', 'prod.vaccinateyourdoctors.org', args.no_delete, args.overwrite_all)
            time.sleep(1)

        print('\nAll done!')
    else:
        print('Doing nothing. Type -h for help.')

    return True


def deploy_to_s3(conn, frozen_path, bucket_name, no_delete, overwrite_all):
    """ Deploy a frozen app to S3, semi-intelligently. """

    print('*** Preparing to deploy in: %s' % bucket_name)
    time.sleep(1)

    # Get our bucket
    bucket = conn.lookup(bucket_name)
    if not bucket:
        # TODO: Standardize errors. Should we die always? Raise()? Return?
        sys.stderr.write('Cannot find bucket!\n')
        sys.exit(1)

    # Data structures
    cloud_set = set()
    cloud_hashes = {}
    local_set = set()
    local_hashes = {}

    print("Getting cloud file list ...")
    # Make a list of cloud objects & etag hashes
    # NOTE: Boto claims it provides a Content-MD5 value, but it totally lies.
    objects = bucket.list()
    for storage_object in objects:
        # WARN: This is a bit of a hack. Naming files .gz. will break the world.
        # if '.gz.' not in storage_object.name:
        cloud_set.add(storage_object.name)
        cloud_hashes[storage_object.name] = storage_object.etag

    print("Files in cloud: %s" % str(len(cloud_set)))

    # Build local files an a (more complex) hash list for Boto
    for dirname, dirnames, filenames in os.walk(frozen_path):
        # Filter out "~" files.
        for filename in filter(lambda x: not x.endswith("~"), filenames):
            full_path = os.path.join(dirname, filename)
            # TODO: Fix this hack.
            stripped_name = '/'.join(full_path.split('/', 2)[1:])
            local_set.add(stripped_name)
            # Add checksums on files
            cksum = md5()
            cksum.update(open(full_path).read())
            local_hashes[stripped_name] = (cksum.hexdigest(), b64encode(cksum.digest()))

    print("Files on disk: %s" % str(len(local_set)))
    time.sleep(1)

    # Completely missing files
    upload_pending = local_set.difference(cloud_set)
    delete_pending = cloud_set.difference(local_set)

    # Compare local and cloud hashes
    for filename, hashes in local_hashes.iteritems():
        hex_hash, b64hash = hashes
        if overwrite_all or cloud_hashes.get(filename) != '"' + hex_hash + '"':
            # NOTE: AWS overwrites uploads, so no need to delete first.
            upload_pending.add(filename)

    # TODO: Make these much higher when we have good versioning set up.
    cache_times = {'.png': '2628000',  # 1 month
                   '.jpg': '2628000',  # 1 month
                   '.js': '86400',     # 1 day
                   '.css': '86400',    # 1 day
                   '.html': '14400',   # 4 hours
                   '.ico': '604800',   # 1 week
                   '_DEFAULT_': '86400'
                   }

    def get_headers(filename, extn):
        headers = {}
        exp_seconds = cache_times.get(extn, cache_times['_DEFAULT_'])

        headers['Cache-control'] = 'public, max-age=' + exp_seconds

        # Security-related headers
        if extn in {'.html'}:
            headers['Content-Type'] = 'text/html; charset=UTF-8'
            headers['X-Content-Type-Options'] = 'nosniff'
            headers['X-Frame-Options'] = 'SAMEORIGIN'
            headers['X-XSS-Protection'] = '1; mode=block'
        # SSO magic
        if filename.endswith('openid') and extn is "":
            headers['Content-Type'] = 'application/xrds+xml; charset=UTF-8'
        if filename.endswith('host-meta') and extn is "":
            headers['Content-Type'] = 'application/host-meta; charset=UTF-8'
        return headers

    # Note: We don't need to setup permission here (e.g. k.make_public()), because there is
    # a bucket-wide AWS policy: http://docs.amazonwebservices.com/AmazonS3/latest/dev/WebsiteAccessPermissionsReqd.html
    # TODO: Do we need those bucket policies since we're using the S3 web hosting route? I don't think so.
    if len(upload_pending) > 0:
        print("Uploading: %s" % str(len(upload_pending)))
        for upload_file in upload_pending:
            filename, extn = os.path.splitext(upload_file)

            k = Key(bucket)
            k.key = upload_file
            k.set_contents_from_filename(frozen_path + '/' + upload_file, headers=get_headers(filename, extn), md5=local_hashes[upload_file])

            # Setup a gzip copy, too, maybe:
            if extn in {'.html', '.htm', '.css', '.js', '.txt'} and False:
                kgz = Key(bucket)
                kgz.key = filename + '.gz' + extn
                gz_buffer = StringIO.StringIO()
                gz_fh = gzip.GzipFile(mode='wb', compresslevel=9, fileobj=gz_buffer)
                gz_fh.write(open(frozen_path + '/' + upload_file).read())
                gz_fh.close()
                gz_buffer.seek(0)
                kgz.set_contents_from_file(gz_buffer, headers={'Content-Encoding': 'gzip', 'Content-Type': k.content_type})

    # Delete orphans, maybe.
    if len(delete_pending) > 0 and not no_delete:
        print("\nDeleting: %s" % str(len(delete_pending)))
        for delete_file in delete_pending:
            print("\t %s" % str(delete_file))
            bucket.delete_key(delete_file)
            # Try to delete .gz.ext files, too
            filename, extn = os.path.splitext(delete_file)
            bucket.delete_key(filename + '.gz' + extn)

    print('** Successfully deployed: %s!\n' % bucket_name)


if __name__ == '__main__':
    main()
