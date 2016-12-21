import socket
import subprocess
import threading
import time

class TimeoutException(Exception):
    pass

def timeout(func, args=(), kwargs={}, timeout_duration=10, default=None):
    
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = default
            self.error = None
            self.cancel = False
            
        def run(self):
            while(True):
                try:
                    self.result = func(*args, **kwargs)
                    break
                except socket.error, e:
                    if e.errno == 111 and not self.cancel:
                        time.sleep(0.1)
                    else:
                        self.error = e
                        break
                except Exception, e:
                    self.error = e
                    break
         
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        it.cancel = True
        raise TimeoutException()
    else:
        if it.error:
            raise BaseException(it.error)
        return it.result
        
class SubprocessTimer(object):
    def __init__(self, timeout):
        self.timeout = timeout
        self.timed_out = False
        self.stime = 0
        self.proc = None
        self.timeout_t = threading.Thread(target=self._check_timeout, name="PROCESS_TIMEOUT_THREAD_%s_SEC" % str(timeout))
        self.timeout_t.daemon = True
        self.timeout_t.start()
        
    def _check_timeout(self):
        while True:
            if self.proc != None:
                if time.time() - self.stime > self.timeout:
                    self.timed_out = True
                    try:
                        self.proc.kill()
                    except:
                        pass
                    self.proc = None
                    self.stime = 0
            time.sleep(1)
            
    def run(self, proc):
        self.timed_out = False
        self.stime = time.time()
        self.proc = proc
        return proc
    
    def run_communicate(self, max_retry, args, log=None, logging_extra_func=None):
        retry = 0
        successful = False
        com_res = None
        while(not successful and retry < max_retry):
            self.run(subprocess.Popen(**args))
            com_res = self.proc.communicate()
            
            if(self.timed_out):
                com_res = None
                retry += 1
                
                if(log != None):
                    msg = "Execution timed out (max %s seconds) at attempt %d of %d" % (self.timeout, retry, max_retry)
                    if(retry == max_retry):
                        msg += " [This was the last attempt]"
                    if(logging_extra_func != None):
                        msg += " %s" % logging_extra_func()
                    msg += "."
                    log.warning(msg)
            else:
                self.proc = None
                self.stime = 0
                successful = True
                
                
        return com_res
    
    
    
if __name__ == "__main__":
    ST = SubprocessTimer(3)
    
    print "Timer kills processes running more than 3 seconds...\n\n-->> First process \"sleep 5\":"
    stime = time.time()
    proc = ST.run(subprocess.Popen(["sleep", "5"], stderr=subprocess.PIPE, stdout=subprocess.PIPE))
    
    proc.wait()
    ret_val = proc.poll()
    
    if ret_val < 0:
        print "Process timeout!"
    else:
        print "Execution complete!"
    
    etime = time.time()
    print "Execution time: %s seconds\nReturn value: %s" % (str(etime-stime), str(ret_val))
    
    print "\n\n-->> Second process \"sleep 2\":\n"
    stime = time.time()
    proc = ST.run(subprocess.Popen(["sleep", "2"], stderr=subprocess.PIPE, stdout=subprocess.PIPE))
    
    proc.wait()
    ret_val = proc.poll()
    
    if ret_val < 0:
        print "Process timeout!"
    else:
        print "Execution complete!"
    
    etime = time.time()
    print "Execution time: %s seconds\nReturn value: %s" % (str(etime-stime), str(ret_val))
