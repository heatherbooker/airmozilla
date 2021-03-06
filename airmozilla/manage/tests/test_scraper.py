from nose.tools import eq_
import mock

from django.test import TestCase

from airmozilla.manage import scraper
from airmozilla.base.tests.testbase import Response


SAMPLE_INTRANET_HTML = u"""<!doctype html>
<head><title>Title</title></head>
<div id="mw-content-text">
<h2>H2 Title</h2>
<p>Test Content</p>
</div>
</body>
</html>"""


class TestScraper(TestCase):

    def test_get_urls(self):
        text = """
        Some junk
        http://airmozilla/manage/events/1068/ stuff
        https://etherpad.mozilla.org/sumo-mobile
        hello, this is madness
        https://docs.python.org/2/library/urlparse.html..
        madness I say https://github.com/mozilla/airmozilla........
        yes http://blog.mozilla.org/devtools/.
        """
        urls = list(scraper.get_urls(text))
        eq_(
            urls,
            [
                'http://airmozilla/manage/events/1068/',
                'https://etherpad.mozilla.org/sumo-mobile',
                'https://docs.python.org/2/library/urlparse.html',
                'https://github.com/mozilla/airmozilla',
                'http://blog.mozilla.org/devtools/'
            ]
        )

    @mock.patch('requests.get')
    def test_get_content_readability(self, rget):

        def mocked_get(url):
            assert 'abc123' in url
            return Response({
                'content': '<p>Test content</p>'
            })

        rget.side_effect = mocked_get

        url = 'http://doesnotexist/path'
        with self.settings(READABILITY_PARSER_KEY='abc123'):
            content, status = scraper.get_content_readability(url)
            eq_(content, 'Test content')
            eq_(status, 200)

            # or use the scrape_url()
            result = scraper.scrape_urls([url])
            eq_(result['text'], 'Test content')
            eq_(result['results'][0], {
                'worked': True,
                'status': 200,
                'url': url
            })

        with self.settings(READABILITY_PARSER_KEY=None):
            content, status = scraper.get_content_readability(url)
            eq_(content, None)
            eq_(status, 'No READABILITY_PARSER_KEY setting set up')

    @mock.patch('requests.get')
    def test_get_content_readability_failed(self, rget):

        def mocked_get(url):
            assert 'abc123' in url
            return Response({}, status_code=500)

        rget.side_effect = mocked_get

        url = 'http://doesnotexist/path'
        with self.settings(READABILITY_PARSER_KEY='abc123'):
            content, status = scraper.get_content_readability(url)
            eq_(content, '')
            eq_(status, 500)

    @mock.patch('requests.get')
    def test_get_content_intranet(self, rget):

        def mocked_get(url, **options):
            assert options['auth'] == ('foo', 'bar')
            return Response(SAMPLE_INTRANET_HTML)

        rget.side_effect = mocked_get

        url = 'https://intranet.mozilla.org/path'
        scrape_credentials = {
            ('foo', 'bar'): ['intranet.mozilla.org'],
        }
        with self.settings(SCRAPE_CREDENTIALS=scrape_credentials):
            content, status = scraper.get_content_intranet(url)
            eq_(status, 200)
            eq_(content, 'H2 Title\nTest Content')

            # or use the scrape_url()
            result = scraper.scrape_urls([url])
            eq_(result['text'], 'H2 Title\nTest Content')
            eq_(result['results'][0], {
                'worked': True,
                'status': 200,
                'url': url
            })

        with self.settings(SCRAPE_CREDENTIALS={}):
            content, status = scraper.get_content_intranet(url)
            eq_(status, 'No credentials set up for intranet.mozilla.org')
            eq_(content, None)

    @mock.patch('requests.get')
    def test_get_content_etherpad(self, rget):

        def mocked_get(url, **options):
            eq_(
                url,
                'https://etherpad.mozilla.org/ep/pad/export/foo-bar/latest?'
                'format=txt'
            )
            return Response('Content here')

        rget.side_effect = mocked_get

        url = 'http://etherpad.mozilla.org/foo-bar'
        content, status = scraper.get_content_etherpad(url)
        eq_(status, 200)
        eq_(content, 'Content here')

        # or use the scrape_url()
        result = scraper.scrape_urls([url])
        eq_(result['text'], 'Content here')
        eq_(result['results'][0], {
            'worked': True,
            'status': 200,
            'url': url
        })
