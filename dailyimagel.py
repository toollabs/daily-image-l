#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Initally written by https://commons.wikimedia.org/wiki/User:Pfctdayelise under Creative Commons Attribution-ShareAlike 3.0 license
# <https://creativecommons.org/licenses/by-sa/3.0/legalcode>
# Mostly re-written by https://www.mediawiki.org/wiki/User:Legoktm to
# use modern APIs and not wget.

import os
import re
import sys
import datetime
import requests
import traceback
import mwparserfromhell


def api(**kwargs):
    kwargs['formatversion'] = 2
    kwargs['format'] = 'json'
    r = requests.get('https://commons.wikimedia.org/w/api.php', params=kwargs)
    if not r.ok:
        r.raise_for_status()
    return r.json()


def page_content(title):
    params = {
        'action': 'query',
        'prop': 'revisions',
        'rvprop': 'content',
        'titles': title,
    }
    data = api(**params)
    return data['query']['pages'][0]['revisions'][0]['content']


def get_today_potd_title():
    d = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    return 'Template:Potd/' + d


def get_today_potd():
    title = get_today_potd_title()
    content = page_content(title)
    code = mwparserfromhell.parse(content)
    name = unicode(code.filter_templates()[0].get(1).value)
    # Avoid bug when the comment is kept in the template
    # https://commons.wikimedia.org/w/index.php?title=Template%3APotd%2F2022-12-06&diff=717399978&oldid=700576888
    name = re.sub("<!--.*-->", "", name, 0, re.DOTALL).strip()
    return 'File:' + name


def file_url(title):
    return 'https://commons.wikimedia.org/wiki/' + title.replace(' ', '_')


def get_metadata(title):
    params = {
        'action': 'query',
        'prop': 'imageinfo',
        'iiprop': 'extmetadata',
        'iilimit': '10',
        'titles': title,
    }
    data = api(**params)
    return data['query']['pages'][0]['imageinfo'][0]['extmetadata']


def expand_templates(text):
    params = {
        'action': 'expandtemplates',
        'text': text
    }
    data = api(**params)
    return data['expandtemplates']['wikitext']


def get_language_name(lang):
    return expand_templates('{{#language:%s}}' % lang)


def get_captions(title):
    params = {
        'action': 'query',
        'list': 'allpages',
        'apfrom': title.split(':', 1)[1],
        'aplimit': '100',
        'apnamespace': '10'
    }
    data = api(**params)
    langs = {}
    prefix = title + ' '
    for item in data['query']['allpages']:
        if item['title'].startswith(prefix):
            lang = item['title'].split('(')[1].split(')')[0]
            langs[lang] = item['title']
    text = ''
    for lang in sorted(langs):
        lang_name = get_language_name(lang)
        content = page_content(langs[lang])
        if content.strip().startswith('#REDIRECT'):
            # ???
            continue
        code = mwparserfromhell.parse(content)
        try:
            temp = code.filter_templates()[0]
        except IndexError:
            continue
        caption_code = temp.get(1).value
        # We want templates like {{w|FooBar}} to render, so expand them
        expanded = expand_templates(unicode(caption_code))
        caption = unicode(mwparserfromhell.parse(expanded).strip_code())
        text += '%s: %s\n' % (lang_name, caption)

    return text


SENDMAIL = "/usr/sbin/sendmail"

mailfrom = 'Wikimedia Commons Picture of the Day <tools.potd@tools.wmflabs.org>'
# mailto = "brianna.laugher@gmail.com"
mailto = "daily-image-l@lists.wikimedia.org"
# mailto = "zhuyifei1999@gmail.com"
# mailto = "steinsplitter-wiki@live.com"
# mailto = 'bryan.tongminh@gmail.com'
if len(sys.argv) > 1:
        mailto = sys.argv[1]


def createmail():

    title = get_today_potd()

    imageurl = file_url(title)
    metadata = get_metadata(title)
    captions = get_captions(get_today_potd_title())

    if 'UsageTerms' in metadata:
        lic = 'Licensed under the %s.' % metadata['UsageTerms']['value']
    else:
        # ????
        lic = None

    text = ''
    text += 'From: ' + mailfrom + '\r\n'
    text += "To: " + mailto + '\r\n'
    text += 'Content-Type: text/plain; charset=utf-8\r\n'
    text += "Subject: " + str(datetime.date.today()) + '\r\n\r\n'
    text += "Picture of the day:\r\n"

    text += imageurl + '\n'
    if lic:
        text += 'Copyright status: ' + lic + '\n'
    text += 'Descriptions:\n'
    text += captions

    return text


def main():
    error = None
    try:
        mail = createmail()
    except:
        # TODO: We should email this to someone
        traceback.print_exc()
        raise

    if error:
        mail += "Error information: " + str(error)

    # open a pipe to the mail program and
    # write the data to the pipe
    p = os.popen("%s -t" % SENDMAIL, 'w')
    p.write(mail.encode('utf-8'))
    exitcode = p.close()
    if exitcode:
        print "sendmail error: Exit code: %s" % exitcode

if __name__ == '__main__':
    main()
