#!/usr/bin/python3
# Checks the status of ips by connecting to a port and reporting on the result

import socket
import time
import json
import os
import multiprocessing

import emailer


def loadconf(f_name):
    """ Checks for a json file, returns data if it exists, or else exits
    f_name(str) - name of the file
    """
    if os.path.isfile(f_name):
        with open(f_name, 'r') as json_file:
            try:
                data = json.load(json_file)
                return data
            except ValueError as err:
                alert('x', "Cannot continue: {err}".format(err=err))
                raise SystemExit
    else:
        alert('x', "{f_name} not found. Check the readme. Exiting".format(f_name=f_name))
        raise SystemExit


def alert(status, text):
    """ Formats alerts and prints to console
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        result = s.connect_ex((ip, port))
    return True if result else False


def check_remote_status(ip, port, retry):
    """ Attempts to connect to an ip with retries if the ip/port are
    not responding
        ip(str) - ip address of target
    port(int) - port address to use
    retry(int) - number of times to retry
    Returns time.time() if offline, True if online
    """
    # alert('!', 'DEBUG: {} PROC STARTED'.format(ip))
    for x in range(1, retry + 1):
        if not portdown(ip, port):
            break
    else:
        # alert('!', 'DEBUG: {} PROC FINISHED'.format(ip))
        return ip, time.time()
    # alert('!', 'DEBUG: {} PROC FINISHED'.format(ip))
    return ip, False


def call_for_help(site, ip, port, down, creds):
    """Creates and sends an email
    site(str) - site name
    ip(str) - site ip
    port(int) - site port
    down(str) - time and date
    creds(dict) - contains to, from, subject fields
    """
    body = (
        "WARNING! {site} IS OFFLINE!\nLast online {down}"
        "Cannot connect to {ip}:{port}"
        "Please contact {site} to verify if there is a known issue.\n"
        "TIP: Power cycling the Shaw cable modem often fixes intermittent issues. "
        "This involves unplugging the modem from the power for 30 seconds, "
        "then plugging it back in, but be careful not to power cycle the wrong device.\n"
        "If the issue persists for more than 15 minutes and the store infrastructure seems fine, "
        "contact Shaw Technical Support @ 1-877-742-9249\n\n"
        "This alert was auto-generated. Do not reply").format(
            site=site, down=down, ip=ip, port=port)
    return emailer.compose_and_send(
        creds['from'], creds['to'], creds['subject'], body
    )


def internet_working(ip='8.8.8.8', port=53):
    """Checks if socket can connect to a remote ip, Google DNS by default
    """
    return not portdown(ip, port)


def recently_emailed(emailed):
    return time.time() - emailed < 14400


def updatedict(sites, result):
    """Updates a dictionary based on the fields in a list of tuples"""

    for ip, down in result:
        if down and sites[ip]['down'] == False:
            sites[ip]['down'] = down
        else:
            sites[ip]['down'] = False
    return sites


def try_email(sites, creds):

    for ip, val in sites.items():
        if val['down']:
            if not recently_emailed(val['emailed']):
                call_for_help(
                    sites[ip]['name'], ip, port, time.ctime(sites[ip]['down']), creds
                    )
                sites[ip]['emailed'] = time.time()
                alert('x', 'email sent')
            else:
                alert('-', 'Skipped {site} - It was emailed {time} min ago'.format(
                    site=sites[ip]['name'], time=(time.time() - sites[ip]['emailed']) // 60))


def main(sites, port, creds, retry):

    if internet_working():
        with multiprocessing.Pool(processes=3) as pool:
            result = pool.starmap(
                check_remote_status, ((ip, port, retry) for ip in sites.keys()),
            )

        sites = updatedict(sites, result)

        try_email(sites, creds)

        alert('-', "Scan complete. Sleeping for 15mins".format(time=time.ctime()))
        time.sleep(900)

    else:
        alert('x', "Can't reach Google. Sleeping for an hour")
        time.sleep(3600)


if __name__ == '__main__':
    retry = 5
    settings = loadconf('sitecheck.config.json')
    port = settings['CONF']['port']
    creds = settings['EMAIL']
    sites = {
        ip: { 
            'name': site, 'down': False, 'emailed': False
            } for site, ip in settings['DEST'].items()
    }

    while True:
        main(sites, port, creds, retry)
