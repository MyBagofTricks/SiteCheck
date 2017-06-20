#!/usr/bin/python3
# Checks the status of ips by connecting to a port and reporting on the result

import socket
import smtplib
import time
import json
from os import path

import multiprocessing

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
                message('x', "[x] Cannot continue: {err}".format(err=err))
                raise SystemExit
    else:
        message('x', "[x] {f_name} not found. Exiting".format(f_name=f_name))
        raise SystemExit


def message(status, text):
    """ Formats messages and prints to console
    status(str) - error type (x means bad)
    text(str) - text to print
    """
    print("[{status}] {time} :: {text}".format(
        status=status, time=time.ctime(), text=text))


def portdown(ip, port):
    """ Checks if site is down
    ip(str) - ip address
    port(int) - port number
    Returns true if down, false if up
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    result = s.connect_ex((ip, port))
    s.close()
    if not result:
        return False
    else:
        return True


def isdown(ip, port, retry):
    """ Attempts to connect to an ip with retries if the ip/port are
    not responding
        ip(str) - ip address of target
    port(int) - port address to use
    retry(int) - number of times to retry
    Returns time.time() if offline, True if online
    """
    for x in range(1, retry+1):
        if not portdown(ip, port):
            return ip, False
        else:
            message('x', "Site {} Down. Attempt {} of {} ".format(ip, x, retry))
    return ip, time.time()
        

def callforhelp(site, ip, port, dtime, creds):
    """Creates and sends an email
    site(str) - site name
    ip(str) - site ip
    port(int) - site port
    dtime(str) - time and date
    creds(dict) - contains to, from, subject fields
    """
    msg = """WARNING! {name} IS OFFLINE!
    Last online: {dtime}
    Cannot connect to {ip} via port {port}

    Please contact the {name} site and possibly the ISP

    I AM A BOT - DO NOT REPLY
    """.format(name=site, dtime=dtime, ip=ip, port=port)
    return emailer.compose_and_send(
        creds['from'], creds['to'], creds['subject'], msg
        )


def engine(sites, port, creds, retry):
    while True:
        if portdown('8.8.8.8', 53) == False:
            with multiprocessing.Pool(processes=3) as pool:
                result = pool.starmap(
                    isdown, {(ip, port, retry) for ip in sites.keys()}, 
                    )
            for tup in result:
                ip = tup[0]
                dtime = tup[1]
                if not dtime:
                    sites[ip]['dtime'] == False
                else:
                    if sites[ip]['dtime'] == False:
                        sites[ip]['dtime'] = dtime
            for ip, val in sites.items():
                if val['dtime'] and time.time() - val['emailed'] > 14400:
                    callforhelp(val['name'], ip, port, time.ctime(val['dtime']), creds)
                    val['emailed'] = time.time()
                    message('!', "Email sent! :: {site}".format(site=val['name']))
                elif val['dtime'] > 0 and time.time() - val['emailed'] < 14400:
                    message(
                        '-', 'Skipped {site} - It was emailed {time} min ago'.format(
                            site=val['name'], time=(time.time() - val['emailed'])//60)
                            )
            message(' ', "{time} Sleeping for 15mins".format(time=time.ctime()))
            time.sleep(900)
        else:
            message('x', "Can't reach Google. Sleeping for an hour")
            time.sleep(3600)

def generatedict(sites_ips):
    # removed dtime check... keep simple
    sites = {}
    for site, ip in sites_ips.items():
        sites[ip] = {
            'name': site,
            'dtime': False,
            'emailed': False,
        }
    return sites


def main():
    pass
    

if __name__ == '__main__':
    settings = loadconf('sitecheck.config.json')
    port = settings['CONF']['port']
    creds = settings['EMAIL']
    retry = 5
    sites = generatedict(settings['DEST'])

    engine(sites, port, creds, retry)

    