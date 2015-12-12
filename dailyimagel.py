#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Initally written by https://commons.wikimedia.org/wiki/User:Pfctdayelise under Creative Commons Attribution-ShareAlike 3.0 license
# <https://creativecommons.org/licenses/by-sa/3.0/legalcode>

wget = '''/usr/bin/wget -S -erobots=off -q -O - '''

todaypotd = r'https://commons.wikimedia.org/w/index.php?title=Commons:Picture_of_the_day/Today_in_all_languages&action=purge&useskin=monobook'
urlbase = r'https://commons.wikimedia.org/wiki/'
#querycat = 'http://commons.wikimedia.org/w/query.php?what=categories&format=txt&titles='
querycat = 'https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=categories&titles='
#querylinks = r'http://commons.wikimedia.org/w/query.php?what=imagelinks&ilnamespace=4&format=txt&illimit=300&titles='
querylinks = r'https://commons.wikimedia.org/w/api.php?action=query&format=json&iunamespace=4&iulimit=500&list=imageusage&iutitle='


import json
import os,sys,re
import urllib2
from commands import getoutput
from datetime import date

repotdcontent = re.compile('"mw-content-text"(.*?)NewPP limit report', re.DOTALL)
reimagename = re.compile('<div class="magnify"><a href="/wiki/([^"]*)" class="internal"')
refplinks = re.compile('Commons:Featured pictures/([^c].*)')
reqilinks = re.compile('Commons:Quality [Ii]mages/([^c].*)')
recaptions = re.compile('<ul.*?>(.*?)</ul>', re.DOTALL)
reli = re.compile('</?li[^>]*>')
rea = re.compile('</?a[^>]*>')
rei = re.compile('</?i>')
renocaption = re.compile('\n[^:]*: Template:Potd[^)]*\)')

SENDMAIL = "/usr/sbin/sendmail"

mailfilename = "/data/project/potd/dailyimagel.txt"
mailerror = "/data/project/potd/mailerror.txt"

mailfrom = 'Wikimedia Commons Picture of the Day <local-potd@tools.wmflabs.org>'
#mailto = "brianna.laugher@gmail.com"
mailto = "daily-image-l@lists.wikimedia.org"
#mailto = "steinsplitter-wiki@live.com"
#mailto = 'bryan.tongminh@gmail.com'
if len(sys.argv) > 1:
        mailto = sys.argv[1]


def find_in_list(regex, strings):
    for string in strings:
        m = regex.search(string)
        if m:
            return m.group(1)
    raise IndexError


def createmail():
    '''
    Attempts to create an email at mailfilename.
    '''
    #print "starting"
    f = getoutput(wget + '--post-data "submit=OK&wpEditToken=%2B%5C&redirectparams=useskin%3Dvector" "' + todaypotd + '"')
    #print "got wget output ok"

    wgetfile = open('/data/project/potd/wgetoutput.txt','w')
    wgetfile.write(f)
    wgetfile.close()

    #print "f:",f

    content = repotdcontent.findall(f)

    #print "got content ok"

    # extract image name/url
    #print len(content)
    #print "content[0]:",content[0]

    imagename = reimagename.findall(content[0])[0]
    imageurl = urlbase + imagename

    #print "got image name ok"

    # attempt to determine license status from categories
    catstext = json.load(urllib2.urlopen(querycat + imagename))
    categories = [cat['title'][9:]
                  for cat in catstext['query']['pages'].values()[0].get('categories', [])]

    #print "categories:", categories

    licenses = {"GFDL":"GNU Free Documentation License",
                "CC-BY-SA-1.0":"Creative Commons Attribution ShareAlike license, version 1.0",
                "CC-BY-SA-2.0":"Creative Commons Attribution ShareAlike license, version 2.0",
                "CC-BY-SA-2.5":"Creative Commons Attribution ShareAlike license, version 2.5",
                "CC-BY-SA-3.0":"Creative Commons Attribution ShareAlike license, version 3.0",
                "CC-BY-SA-4.0":"Creative Commons Attribution ShareAlike license, version 4.0",
                "CC-BY-1.0":"Creative Commons Attribution license, version 1.0",
                "CC-BY-2.0":"Creative Commons Attribution license, version 2.0",
                "CC-BY-2.5":"Creative Commons Attribution license, version 2.5",
                "CC-BY-3.0":"Creative Commons Attribution license, version 3.0",
                "CC-BY-4.0":"Creative Commons Attribution license, version 4.0"
                }

    lic = ""
    if "Self-published work" in categories:
        lic = "Created by a Wikimedian (see image page for details); "
    for l in licenses.keys():
        if l in categories:
            lic += "Licensed under the " + licenses[l] +'. '

    if "Public domain" in categories:
        lic = "Public domain"

    for cat in categories:
        if cat.startswith("PD"):
            if cat=="PD-self":
                lic = "Created by a Wikimedian (see image page for details); released into the public domain."
            elif cat=="PD Art":
                lic = "Reproduction of a two-dimensional work of art whose copyright has expired (public domain)."
            elif cat=="PD Old":
                lic = "Public domain (copyright expired due to the age of the work)."
            else:
                lic = "Public domain as a work of the " + cat[3:] + " organisation."

    # determine FP category (or 'topic')
    linkstext = json.load(urllib2.urlopen(querylinks + imagename))
    imageusage = [iu['title'] for iu in linkstext['query']['imageusage']]
    isFP = True
    try:
        topics = find_in_list(refplinks, imageusage)
    except IndexError:
        try:
            isFP = False
            topics = find_in_list(reqilinks, imageusage)
        except IndexError:
            print "Could not find FP or QI backlink, aborting"
            raise IndexError, 'Could not find FP or QI backlink'

    if '/' in topics:
        topic = topics.split('/')[0] + ' (' + topics.split('/')[1] + ')'
    else:
        topic = topics

    # extract multilingual captions
    try:
        captions = recaptions.findall(content[0])[0]
    except IndexError:
        raise IndexError, 'no captions??'

    #print captions
    captions = reli.sub('',captions)
    captions = rea.sub('',captions)
    captions = rei.sub('',captions)
    captions = renocaption.sub('',captions)


    # write info to file
    g= open(mailfilename,'w')
    g.write('From: ' + mailfrom + '\r\n')
    g.write("To: " + mailto + '\r\n')
    g.write('Content-Type: text/plain; charset=utf-8\r\n')
    #don't need this?
    #g.write("From: brianna.laugher@gmail.com\n")
    g.write("Subject: " + str(date.today()) + '\r\n\r\n')
    g.write("Body of email:\r\n")

    g.write(imageurl + '\n')
    g.write('Copyright status: ' + lic +  '\n')
    if isFP:
        g.write('Featured Picture category: ' + topic + '\n\n')
    else:
        if 'Subject' in topic:
            g.write('Recognised as a Quality Image due to subject matter\n\n')
        else:
            g.write('Recognised as a Quality Image due to technical merit\n\n')
    g.write('Descriptions:\n')
    g.write(captions)
    g.close()
    return

###############################
error = None
try:
    createmail()
except:
    # some Python error, catch its name and send error mail
    error = sys.exc_info()[0]
    mailfilename = mailerror
    raise

# get the email message from a file
f = open(mailfilename, 'r')
mail = f.read()
f.close()

if error:
    mail += "Error information: " + str(error)

# open a pipe to the mail program and
# write the data to the pipe
p = os.popen("%s -t" % SENDMAIL, 'w')
p.write(mail)
exitcode = p.close()
if exitcode:
    print "sendmail error: Exit code: %s" % exitcode
