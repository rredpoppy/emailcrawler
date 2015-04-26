'''
Created on 22.12.2009

@author: Adrian
'''
#linkregex = re.compile(
    #                        '<a(?:\s[A-Za-z]+=".*")*(?:\s[A-Za-z]+=\'.*\')*'+ #non-group sequence matching any attribute
    #                        '\s+href=[\'"](.*?)[\'"].*?>' #group sequence to match the href part
    # 
import re, sys
import urllib2
import urlparse
import htmllib, formatter, os
import thread, signal

#************** Define the link extraction class *************************

class LinksExtractor(htmllib.HTMLParser):
    def __init__(self, formatter) :        # class constructor
        htmllib.HTMLParser.__init__(self, formatter)  # base class constructor
        self.links = []        # create an empty list for storing hyperlinks

    def start_a(self, attrs) :  # override handler of <A ...>...</A> tags
        # process the attributes
        if len(attrs) > 0 :
            for attr in attrs :
                if attr[0] == "href" :         # ignore all non HREF attributes
                    self.links.append(attr[1]) # save the link info in the list

    def get_links(self) :
        return self.links


        
#**************Define the email extraction function ***********************
        
def extractEmail(baseurl, basename, headers, f):
    global numberOfThreads, numberOfThreadsLock, consoleLock, tocrawl, tocrawlLock, crawled, crawledLock, pattern, numberOfPages, numberOfPagesLock, fileLock

    # increase the threads number
    numberOfThreadsLock.acquire()
    numberOfThreads += 1
    numberOfThreadsLock.release()
        
    
    tocrawlLock.acquire()    
    if not len(tocrawl):
        tocrawlLock.release()
        numberOfThreadsLock.acquire()
        numberOfThreads -= 1
        numberOfThreadsLock.release()
        thread.exit()
        return
    crawling = tocrawl.pop()
    tocrawlLock.release()
    
    try:
        # Get the url components for checks
        url = urlparse.urlparse(crawling)
        reqObj = urllib2.Request(crawling, None, headers)
        response = urllib2.urlopen(reqObj, None, 4)
        consoleLock.acquire()
        print thread.get_ident(), 'conectare la: %s' % crawling        
        consoleLock.release()
    except:
        numberOfThreadsLock.acquire()
        numberOfThreads -= 1
        numberOfThreadsLock.release()
        thread.exit()
        return    

    numberOfPagesLock.acquire()
    numberOfPages += 1
    numberOfPagesLock.release()
    
    
    #After connecting, read the response
    msg = response.read()
    #Find all emails
    emailuri = pattern.findall(msg)
    
    #Create default formatter
    sformat = formatter.NullFormatter()           
    htmlparser = LinksExtractor(sformat)
    
    #Parse the response, saving the info about links
    htmlparser.feed(msg)      
    htmlparser.close()                
    links = htmlparser.get_links()
    
    # Add the emails to the file
    for i in range(len(emailuri)):
        try:            
            fileLock.acquire()
            f.write(emailuri[i] + "\n")            
            fileLock.release()
        except:
            numberOfThreadsLock.acquire()
            numberOfThreads -= 1
            numberOfThreadsLock.release()
            thread.exit()
            return
    
    # Mark url as crawled 
    try:
        crawledLock.acquire()
        crawled.add(crawling)
        crawledLock.release()
    except:
        numberOfThreadsLock.acquire()
        numberOfThreads -= 1
        numberOfThreadsLock.release()
        thread.exit()
        return
    
    if not len(links):
        thread.exit()
        return
    
    #Find the new links to crawl in the extracted links
    for link in links:
        if (link.endswith('.png') or link.endswith('.jpg') or \
            link.endswith('.gif') or link.endswith('.jpeg') or \
            link.endswith('.zip') or link.endswith('.rar') or \
            link.endswith('.avi') or link.endswith('.exe')):
            continue
        if link.startswith('/'):
                link = 'http://' + url[1] + link
        elif link.startswith('#'):
                link = 'http://' + url[1] + url[2] + link
        elif not link.startswith('http'):
                link = 'http://' + url[1] + '/' + link
                
        if link not in crawled:
            if basename[1] == url[1]:
                try:
                    tocrawlLock.acquire()                    
                    tocrawl.add(link)
                    tocrawlLock.release()
                except:
                    numberOfThreadsLock.acquire()
                    numberOfThreads -= 1
                    numberOfThreadsLock.release()                    
                    thread.exit()
                    return
    numberOfThreadsLock.acquire()
    numberOfThreads -= 1
    numberOfThreadsLock.release()
    thread.exit()     
    return

def signal_handler(signal, frame):
    global stop, consoleLock
    consoleLock.acquire()
    print 'exiting...'
    consoleLock.release()
    stop = 1

#************* Start the main program ***********************************

if __name__ == '__main__':

    numberOfThreads = 0
    numberOfThreadsLock = thread.allocate_lock()
    consoleLock = thread.allocate_lock()
    
    urlToStart = raw_input('Start url: ')    
    fileToSave = raw_input('Results file: ')
    fileLock = thread.allocate_lock()
    
    if urlToStart == '':
        urlToStart = 'http://www.google.ro'
    if fileToSave == '':
        fileToSave = 'email.txt'
        
    #Pattern for the email extraction
    pattern = re.compile("[A-Za-z0-9._]+@[A-Za-z0-9_]+\.[a-z]+")
    
    #The set holding the urls to crawl
    tocrawl = set([urlToStart])    
    numberOfPages = 0
    tocrawlLock = thread.allocate_lock()
    numberOfPagesLock = thread.allocate_lock()
    
    baseurl = tocrawl.copy()
    basename = urlparse.urlparse(baseurl.pop())
    crawled = set([])
    crawledLock = thread.allocate_lock()
    
    f = open(fileToSave, 'w')
    
    user_agent = 'Googlebot/2.1 (Google\'s crawler; www.googlebot.com; googlebot@google.com)'
    headers = {'User-agent' : user_agent}

    #define the stop thread
    stop = 0
    signal.signal(signal.SIGINT, signal_handler)
    
    while 1:
        if stop:
            break
        # if the are not any more links and no threads, exit, we're done
        numberOfThreadsLock.acquire()
        if numberOfThreads == 0 and not len(tocrawl):
            numberOfThreadsLock.release()
            break;
        if numberOfThreadsLock.locked():
            numberOfThreadsLock.release()

        # if no more links, wait for threads to add some
        tocrawlLock.acquire()    
        if not len(tocrawl):
            tocrawlLock.release()
            continue
        if tocrawlLock.locked():
            tocrawlLock.release()     

        # id we have what to crawl and we reached here, create new thread
        numberOfThreadsLock.acquire()
        if len(tocrawl) and numberOfThreads <= 4:            
            thread.start_new_thread(extractEmail, (baseurl, basename, headers, f))
        if numberOfThreadsLock.locked():
            numberOfThreadsLock.release()
     
    
    f.close()
    f = open(fileToSave, 'r+')
    uniquelines = set(f.readlines())
    f.writelines(set(uniquelines))
    f.close()

    consoleLock.acquire()
    print '%d linkuri de scotocit' % len(tocrawl)
    print '%d linkuri scotocite' % len(crawled)    
    print '%d pagini obtinute' % numberOfPages
    consoleLock.release()
    raw_input('Program terminated. Press any key to exit')
    
