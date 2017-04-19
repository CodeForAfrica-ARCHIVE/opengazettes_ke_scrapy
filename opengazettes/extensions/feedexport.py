import logging
from six.moves.urllib.parse import urlparse
from scrapy.utils.boto import is_botocore
from scrapy.extensions.feedexport import BlockingFeedStorage

logger = logging.getLogger(__name__)


class S3FeedStorage(BlockingFeedStorage):

    def __init__(self, uri):
        from scrapy.conf import settings
        u = urlparse(uri)
        self.bucketname = u.hostname
        self.access_key = u.username or settings['AWS_ACCESS_KEY_ID']
        self.secret_key = u.password or settings['AWS_SECRET_ACCESS_KEY']
        self.is_botocore = is_botocore()
        self.keyname = u.path[1:]  # remove first "/"
        self.policy = settings['FILES_STORE_S3_ACL']
        if self.is_botocore:
            import botocore.session
            session = botocore.session.get_session()
            self.s3_client = session.create_client(
                's3', aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key)
        else:
            import boto
            self.connect_s3 = boto.connect_s3

    def _store_in_thread(self, file):
        file.seek(0)
        if self.is_botocore:
            import botocore.exceptions
            # Handle non-existent key
            try:
                self.s3_client.head_object(Bucket=self.bucketname,
                                           Key=self.keyname)
                # Get the old object
                old_file = self.s3_client.get_object(Bucket=self.bucketname,
                                                     Key=self.keyname)['Body']
                # Append new data to the end of the old data
                new_file = old_file.read() + file.read()
            except botocore.exceptions.ClientError:
                new_file = file.read()

            self.s3_client.put_object(
                Bucket=self.bucketname, Key=self.keyname, Body=new_file,
                ACL=self.policy)
        else:
            conn = self.connect_s3(self.access_key, self.secret_key)
            bucket = conn.get_bucket(self.bucketname, validate=False)
            key = bucket.new_key(self.keyname)
            key.set_contents_from_file(file)
            bucket.set_acl(self.policy, key)
            key.close()
