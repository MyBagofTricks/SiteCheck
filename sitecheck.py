#!/usr/bin/python3
# Checks the status of ips by connecting to a port and reporting on the result

import socket
import smtplib
import time
import json
from threading import Thread
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


def builtdown(sites, port, site_down):
    for site, ip in sites.items():
        if portcheck(ip, port) == False:
            if site not in site_down.keys():
                site_down[site] = {
                    'ip': ip,
                    'dtime': time.time(),
                    'emailed': 0,
                }
    return site_down
            
            



def engine():
    settings = loadconf('sitecheck.config.json')
    sites = settings['DEST']
    port = settings['CONF']['port']
    creds = settings['EMAIL']
    site_down = {}

    while True:
        if portcheck('8.8.8.8', 53) == True:
            for site, ip in sites.items():
                if portcheck(ip, port) == False:
                    if site not in site_down.keys():
                        # Adds entry if none exists
                        site_down[site] = {
                            'ip': ip,
                            'dtime': time.time(),
                            'emailed': 0,
                        }
            if len(site_down) > 0:
                for site, value in site_down.items():
                    
                    ## threading entry
                    for x in range(1,11):
                        print("[x] {time} {site} down. Attempting to connect {att} of 10".format(
                            time=time.ctime(), site=site, att=x
                        ))
                        if portcheck(value['ip'], port) == True:
                            site_down[site].pop()
                            break
                        time.sleep(1)    # Short sleep between attemps

                    if time.time() - value['emailed'] > 14400:
                        normaltime = time.ctime(value['dtime'])
                        msg = messagebuilder(
                            site, value['ip'], port, normaltime
                        )
                        msgid = callforhelp(msg, settings['EMAIL'])
                        value['emailed'] = time.time()
                        print(
                            "[!] Email sent! ID: {msgid} :: {site} down since {time}".format(
                                msgid=msgid, ctime=time.ctime(), site=site, time=normaltime
                                ))
                    else:
                        print('skipped site because it was emailed {} min ago'.format((time.time() - value['emailed'])//60))

                    ## threading exit?
            print("[ ] {time} Sleeping for 30mins".format(time=time.ctime()))
            # time.sleep(1800)
            time.sleep(11)
        else:
            print("[x] {time} Can't reach Google. Sleeping for an hour".format(
                time=time.ctime()
            ))
            time.sleep(3600)
        



def main():
    engine()

if __name__ == '__main__':
    main()