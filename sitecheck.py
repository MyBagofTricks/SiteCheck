#!/usr/bin/python3
# Checks the status of ips

import socket
import smtplib
import time
import json
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


def portcheck(rhost, rport):
    """Uses socket to test port 9111 from a dict. 
    rhost (str) - ip or hostname of target
    rport (int) = port to test
    return False if fails, True if successful
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    result = s.connect_ex((rhost, rport))
    s.close()
    if result:
        return False
    return True

def callforhelp(site_down, creds):
    """Sends an email via google api
    site_down(dict) - sites to email about. format {'site':'ip'}
    """
    msg_text = "Cannot connect to site(s) on port 9111 for 10mins+"
    for site in site_down.keys():
        msg_text+= "\n{site}\t{ip}".format(site=site, ip=site_down[site])
    msg_text += "\n\nInvestigate and contact support\n\nI AM A BOT - DO NOT REPLY"
    emailer.compose_and_send(
        creds['from'], creds['to'], creds['subject'], msg_text)


def main():
    settings = loadconf('sitecheck.config.json')
    while True:
        site_down = {}
        for site in settings['DEST'].keys():
            if portcheck(settings['DEST'][site], 9111) == False and portcheck('8.8.8.8',53) == True:
                site_down[site] = settings['DEST'][site]
        if site_down:
            for x in range(1,11):
                for site in site_down.keys():
                    if portcheck(settings['DEST'][site], 9111) == True:
                        site_down.pop(site)
                print('[!] {} site(s) unreachable. Attempt {} of 10 {}'.format(
                    len(site_down), x, time.ctime()))
                time.sleep(1)
            if portcheck('8.8.8.8', 53) == True:
                callforhelp(site_down, settings['EMAIL'])
                print("[!] Site(s) down: " + " ".join(site_down))
                print("[ ] Sleeping for 6 hours", time.ctime())
                time.sleep(18000)
        print("[ ] Sleeping for 1 hour", time.ctime())
        time.sleep(3600)
            
if __name__ == '__main__':
    main()