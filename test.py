'''
Created on 22.12.2009

@author: Adrian
'''
import thread

def testfunc():
    global i, p
    
    ilock.acquire()
    i += 1
    ilock.release()
    writelock.acquire()
    print 'I am %d' % i
    if len(p):
        plock.acquire()
        print 'Last element of p is %s' % p.pop()
        plock.release()
    writelock.release()          
    
ilock = thread.allocate_lock()
plock = thread.allocate_lock()
writelock = thread.allocate_lock()
p = set(['a', 'b', 'c', 'd', 'q'])
i = 0

while 1:    
    thread.start_new_thread(testfunc, ())
    writelock.acquire()
    print '%d elements left in list' % (len(p))
    if not len(p):
        break
    writelock.release()

print '%d has elements' % len(p)
          
