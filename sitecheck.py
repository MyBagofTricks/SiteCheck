#!/usr/bin/python3
# Checks the status of ips by connecting to a port and reporting on the result

import socket
import smtplib
import time
import json
from multiprocessing import Process
from threading import Thread
from queue import Queue
from os import path

import emailer

def loadconf(f_name):
    """ Checks for a json file, returns data if it exists, or else exits
    f_name(str) - name of the file
    """
    if path.isfile(f_name):
        with open(f_name, 'r') as json_file:
            try:
                data = json.load(json_file)
                return data
            except ValueError as err:
                print("[x] Cannot continue: {err}".format(err=err))
                raise SystemExit
    else:
        print("[x] {f_name} not found. Exiting".format(f_name=f_name))
        raise SystemExit


def portcheck(host, port):
    """Uses socket to test a specified port
    rhost (str) - ip or hostname of target
    rport (int) = port to test
    return False if fails, True if successful
    """
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    result = s.connect_ex((host, port))
    s.close()
    if result:
        return False
    return True


def callforhelp(msg, creds):
    """Sends an email via google api
    msg (str) - text for email message
    creds(dict) = email info keys: from, to, subject
    Returns the msgid if success, error if failed
    """
    return emailer.compose_and_send(
        creds['from'], creds['to'], creds['subject'], msg
        )

def messagebuilder(name, ip, port, dtime):
    """builds and returns email text
    name(str) - site name
    ip(str) - ip
    port(int) - port used
    dtime(str) - date and time when site was last reachable
    """
    msg_text = """WARNING! {name} IS OFFLINE!
    Last online: {dtime}
    Cannot connect to {ip} via port {port}

    Please contact the {name} site and possibly the ISP

    I AM A BOT - DO NOT REPLY
    """.format(name=name, dtime=dtime, ip=ip, port=port)
    return msg_text


def isalive(ip, port, retry):
    """Returns True if site responds, false if not
    ip(str) - ip address of target
    port(int) - port address to use
    retry(int) - number of times to retry
    site_down(dict) - sites already reporting down
    
    """
    for x in range(1, 11):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        result = s.connect_ex((ip, port))
        s.close()
        if not result:
            return True
        else:
            print(
                "[x] {time} Error connecting to {ip} {x} out of 10".format(
                    time=time.ctime(), ip=ip, x=x))
    return False


def engine():
    settings = loadconf('sitecheck.config.json')
    sites = settings['DEST']
    port = settings['CONF']['port']
    creds = settings['EMAIL']
    site_down = {}
    retry = 10

    for site, ip in sites.items():
        sites[site] = {'ip': ip, 'dtime': 0, 'emailed': 0}

    while True:
        if isalive('8.8.8.8', 53, retry) == True:
            
            jobs = []

            for site, val in sites.items():
                ts = Thread(target=isalive, args=(val['ip'], port, retry))
                jobs.append(ts)
            for j in jobs:
                j.start()
            for j in jobs:
                j.join()
            print(jobs)

            status = isalive(val['ip'], port, retry)    # thread this

            if status == False and sites[site]['dtime'] == 0:
                sites[site]['dtime'] = time.time()

            for site, val in sites.items():
                if val['dtime'] > 0 and time.time() - val['emailed'] > 14400:
                    normaltime = time.ctime(val['dtime'])
                    msg = messagebuilder(site, val['ip'], port, normaltime)
                    msgid = callforhelp(msg, settings['EMAIL'])
                    val['emailed'] = time.time()
                    print(
                        "[!] Email sent! ID: {msgid} :: {site} down since {time}".format(
                            msgid=msgid, ctime=time.ctime(), site=site, time=normaltime)
                            )
                elif val['dtime'] > 0 and time.time() - val['emailed'] < 14400:
                    print('skipped site because it was emailed {} min ago'.format(
                        (time.time() - val['emailed'])//60))

                    
                

            print("[ ] {time} Sleeping for 30mins".format(time=time.ctime()))
            # time.sleep(1800)
            time.sleep(1)
        else:
            print("[x] {time} Can't reach Google. Sleeping for an hour".format(
                time=time.ctime()
            ))
            time.sleep(3600)
        



def main():
    engine()

if __name__ == '__main__':
    main()