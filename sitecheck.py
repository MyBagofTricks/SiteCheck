#!/usr/bin/python3
# Checks the status of ips by connecting to a port and reporting on the result

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


def downreminder(dtime):
    """returns True if 4 hours have passed since down_time
    dtime (float) - epoc time
    """
    if time.time() - dtime < 14400:
        return False
    else:
        return True


def engine():
    settings = loadconf('sitecheck.config.json')
    sites = settings['DEST']
    port = settings['CONF']['port']
    creds = settings['EMAIL']

    while True:
        site_down = {}
        for site, ip in sites.items():
            if portcheck(ip, port) == False and portcheck('8.8.8.8',53) == True:
                site_down[site] = {
                    'ip': ip,
                    'dtime': time.time(),
                    'lastemail': 0,
                    }
                    # last func may be useful for fixing dict reset
        if site_down:
            # double check list x10, pop off any that have come online, but log
            for x in range(1,11):
                for site, value in site_down.items():
                    if portcheck(value['ip'], port) == True:
                        site_down.pop(site)
                        # log here
                print('[!] {} site(s) unreachable. Attempt {} of 10 {}'.format(
                    len(site_down), x, time.ctime()))
                time.sleep(1)    # sleep bottleneck
            if portcheck('8.8.8.8', 53) == True:
                for site, value in site_down.items():
                    if downreminder(value['lastemail']) == True:
                        normaltime = time.ctime(value['dtime'])
                        msg = messagebuilder(
                            site, value['ip'], port, normaltime
                        )
                        msgid = callforhelp(msg, settings['EMAIL'])
                        print(
                            "[!] Email sent! ID: {msgid} :: {site} down since {time}".format(
                                msgid=msgid, ctime=time.ctime(), site=site, time=normaltime
                                ))

        print("[ ] Sleeping for 30 min", time.ctime())
        time.sleep(1800)


def main():
    engine()

if __name__ == '__main__':
    main()