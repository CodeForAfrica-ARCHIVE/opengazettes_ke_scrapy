# -*- coding: utf-8 -*-
import os.path
from scrapy.http import Request
from scrapy.pipelines.files import FilesPipeline


class OpengazettesFilesPipeline(FilesPipeline):

    def get_media_requests(self, item, info):
        return [Request(x, meta={'filename': item["filename"],
                'publication_date': item["publication_date"]})
                for x in item.get(self.files_urls_field, [])]

    def file_path(self, request, response=None, info=None):
        # start of deprecation warning block (can be removed in the future)
        def _warn():
            from scrapy.exceptions import ScrapyDeprecationWarning
            import warnings
            warnings.warn('FilesPipeline.file_key(url) method is deprecated,\
            please use file_path(request, response=None, info=None) instead',
                          category=ScrapyDeprecationWarning, stacklevel=1)

        # check if called from file_key with url as first argument
        if not isinstance(request, Request):
            _warn()
            url = request
        else:
            url = request.url

        # detect if file_key() method has been overridden
        if not hasattr(self.file_key, '_base'):
            _warn()
            return self.file_key(url)
        # end of deprecation warning block

        # Now using file name passed in the meta data
        filename = request.meta['filename']
        media_ext = os.path.splitext(url)[1]
        return '%s/%s/%s%s' % \
            (request.meta['publication_date'].strftime("%Y"),
                request.meta['publication_date'].strftime("%m"),
                filename, media_ext)
