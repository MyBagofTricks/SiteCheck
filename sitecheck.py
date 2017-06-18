#!/usr/bin/python3
# Checks the status of ips by connecting to a port and reporting on the result

import socket
import smtplib
import time
import json
import multiprocessing
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


def portdown(host, port):
    """Uses socket to test a specified port
    host (str) - ip or hostname of target
    port (int) = port to test
    return False if online, time.time() if down
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    result = s.connect_ex((host, port))
    s.close()
    if result:
        return time.time()
    return False



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


def isdown(ip, port, retry):
    """Returns tuple epoc time if true, false if not (ip, time)
    ip(str) - ip address of target
    port(int) - port address to use
    retry(int) - number of times to retry
    site_down(dict) - sites already reporting down
    
    """
    for x in range(1, retry+1):
        if portdown(ip, port):
            return (ip, time.time())
            print("[x] {time} Error connecting to {ip} {x} out of {retry}".format(
                time=time.ctime(), ip=ip, x=x, retry=retry))
    return (ip, False)

        
def engine():
    settings = loadconf('sitecheck.config.json')
    port = settings['CONF']['port']
    creds = settings['EMAIL']
    retry = 2
    sites = {}

    for site, ip in settings['DEST'].items():
        sites[ip] = {
            'name': site,
            'dtime': portdown(ip, port),
            'emailed': 0
            }

    while True:
        if portdown('8.8.8.8', 53) == False:
            for ip, val in sites.items():
                down = isdown(ip, port, retry)
                if down[1]:
                    sites[ip]['dtime'] = down[1]
                else:
                    sites[ip]['dtime'] = False


            # Send message
            for ip, val in sites.items():
                if val['dtime'] and time.time() - val['emailed'] > 14400:
                    normaltime = time.ctime(val['dtime'])
                    msg = messagebuilder(val['name'], ip, port, normaltime)
                    msgid = callforhelp(msg, creds)
                    val['emailed'] = time.time()
                    print(
                        "[!] Email sent! ID: {msgid} :: {site} down since {time}".format(
                            msgid=msgid, ctime=time.ctime(), site=val['name'], time=normaltime)
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