## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard ip module, which show ip
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time
import sh
import cbtask
import pdb

class IPTask(cbtask.CbPlayerTask):
    """
        Show Ip...
    """
    def __init__(self, name):
        cbtask.CbPlayerTask.__init__(self, name)
        self.ip_str = []
        self.output = self.name

    def _get_nic_info(self):
        #return [ 'eth0', '192.', '168.', '  1.', ' 148' ]
        nicinfo = {}
        item=None
        for line in sh.ifconfig(_iter = True):
            line = line.strip()
            ifline = line.split('Link encap:')
            if len(ifline) == 2: ## it's a if interface line
                ifname = ifline[0].strip()
                #tmplist = ifline[1].split('HWaddr ')
                tmplist = ifline[1].split()
                item = {}
                item_count = len(tmplist)
                if item_count < 2: ## 这行有错误
                    item = None
                    continue  ## should be loop back if
                if tmplist[0] == 'Local': ## 这是Loopback接口
                    item = None
                    continue
                if tmplist[0] == 'Ethernet': ## 这是以太网接口
                    if item_count == 3: item['MAC'] = tmplist[2] ## 可能有错误。
                elif tmplist[0] == 'Point-to-Point': ## 这是ppp接口
                    item['MAC'] = 'PPP interface'
                else: ## 不知道是什么接口
                    item = None
                    continue
                nicinfo[ifname] = item
                continue
            ipline = line.split('inet addr:')                
            if len(ipline) == 2: ## 这一行包含IP 地址
                if item == None : continue
                tmplist = ipline[1].split(' ', 1)
                ipval = tmplist[0]
                remain = tmplist[1].split('Mask:')
                item['Netmask'] = remain[1] 
                item['IP']      = ipval
                item['Bcast']   = remain[0].split(':')[1].strip()  ## 这一行也可能是 P-t-P 地址
                continue
        return nicinfo
    def _get_ip(self):
        ip_str = []
        nic_info = self._get_nic_info()
        for nic in nic_info:
            ip_str.append(str(nic))
            ips = str(nic_info[nic]['IP']).split(".")
            ip_str.extend(ips)
        return ip_str

    def main(self): ## task entry 
        ret = 0
        for s in self._get_ip(): 
            self.set_output(s)
            time.sleep(1.5)
        self.set_output(self.get_name())
        return ret 
        pass

    def set_output(self, s):
        self.output = s

    def get_output(self):
        return (self.output, 0)

    def handle_exit_key(self): ##
        #TODO
        pass

    def handle_left_key(self): ##
        #TODO
        pass

    def handle_right_key(self): ## 
        #TODO
        pass

if __name__ ==  "__main__" :
    ip_obj = IPTask()
    ip_info = ip_obj._get_ip()
    print repr(ip_info)
    pass
