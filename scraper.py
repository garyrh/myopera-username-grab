#!/usr/bin/python
# -*- coding: utf-8 -*-
import random
import re
import sys
import time
import traceback
import urllib
import urllib2
import gzip
from lxml import etree
from cStringIO import StringIO

user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36'
per_screen = '200'

class NoPager(Exception):
    pass

def sleep(seconds=0.75):
    sleep_time = seconds * random.uniform(0.5, 2.0)
    time.sleep(sleep_time)

def download_url(url, headers):
    while True:
        try:
            request = urllib2.Request(url, headers=headers)
            response = urllib2.urlopen(request)
            content = response.read()
            # Is it compressed with gzip?
            if content.startswith("\x1f\x8b\x08"):
                content = StringIO(content)
                content = gzip.GzipFile(fileobj=content)
                content = content.read()
        except urllib2.HTTPError as error:
            if error.code == 404:
                raise error
            elif error.code == 503 or error.code == 500 or error.code == 403:
                sleep_time = 10
                print 'My Opera threw an error ( code', error.code, ') Sleep for', sleep_time, 'seconds.'
                time.sleep(sleep_time)
                continue # retry
            elif error.code != 200 and error.code != 404:
                print 'Unexpected error. ( code', error.code, ') Retrying.'
                sleep(seconds=5)
                continue # retry
        return content


def scrape_visitors(content):
    ''' Scrape about page for recent visitors'''
    try:
        html = etree.HTML(content)
        xhtml = html.xpath('//div[@id = "visitors"]')
        visitors = []
        for visitor in xhtml[0][1][0]:
            visitors.append(visitor[0].values()[0].strip('/'))
    except IndexError:
        # No visitors found
        return ''
    return visitors

def scrape_friends(content):
    ''' Scrape friends page for... wait for it... friends'''
    html = etree.HTML(content)
    xhtml = html.xpath('//div[@id = "myfriends"]//ul//a/@href')
    friends = []
    for friend in xhtml:
        friends.append(friend.strip('/'))
    return friends

def scrape_maxpage(content):
    ''' Scrape friends page for max number of pages.'''
    html = etree.HTML(content)
    xhtml = html.xpath('//p[@class = "pagenav"]//span/a/@href')
    try:
        return int(re.search(r"index\.dml\?page\=(\d+)", xhtml[-2], re.DOTALL).group(1))
    except:
        return 1

def fetch_usernames(username, category_name):
    print 'Fetch', username, category_name

    # Use gzip to save time and bandwidth! Yay!
    headers = {
        'User-Agent': user_agent,
        'Accept-encoding': 'gzip'
    }
    if category_name == 'visitors':
        category_name = 'about'
    else:
        category_name += '/index.dml?page=1&order=updated&perscreen={0}'.format(per_screen)
    url = 'http://my.opera.com/{0}/{1}'.format(username, category_name)
    content = download_url(url, headers)

    if category_name == 'about':
        for visitor in scrape_visitors(content):
            yield visitor
    else:
        maxPage = scrape_maxpage(content)
        # Page 1
        for friend in scrape_friends(content):
            yield friend
        # Page 2 to Page $maxPage
        print "Grabbing {0} pages".format(maxPage)
        if maxPage > 1:
            for page in xrange(2,maxPage+1):
                content = download_url('http://my.opera.com/{0}/friends/index.dml?page={1}&order=updated&perscreen={2}'.format(username, page, per_screen), headers)
                for friend in scrape_friends(content):
                    yield friend

def friendly_error_msg(error):
    if isinstance(error, urllib2.HTTPError) and error.code == 404:
        print 'No user/group members discovered on this page (404). Continuing.'
    else:
        traceback.print_exc(limit=1)


if __name__ == '__main__':
    username = sys.argv[1]
    filename = sys.argv[2]

    for category_name in ['visitors', 'friends']:
        with open('{0}.{1}.txt'.format(filename, category_name), 'w') as out_file:
            try:
                for found_username in fetch_usernames(username, category_name):
                    out_file.write(urllib.unquote(found_username)+'\n')
                    out_file.flush() # Override stupid write cache
            except (urllib2.HTTPError, NoPager) as error:
               friendly_error_msg(error)
               break
