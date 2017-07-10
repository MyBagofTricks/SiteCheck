#!/usr/bin/env python3
# Checks the status of ips by connecting to a port and reporting on the result

import socket
import time
import configparser
import os
import logging
import multiprocessing

import emailer

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.CRITICAL)
logging.getLogger('googleapiclient.discovery').setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-4s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)


def parse_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    """ Accepts a INI file, returns sites(dict), port(int), creds(dict), retry(int)"""
    sites = {ip: {'name': site, 'emailed': False} for site, ip in config['sites'].items()}
    port = int(config['settings'].get('port'))
    creds = config['email']
    retry = int(config['settings'].get('retry'))
    return sites, port, creds, retry


def portdown(ip, port):
    """ Checks if site is down

    ip(str) - ip address

    port(int) - port number

    Return True if down, False if up
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        result = s.connect_ex((ip, port))
    return True if result else False


def check_remote_status(ip, port, retry):
    """ Attempts to connect to an ip with 10 retries if the ip/port are
    not responding

    ip(str) - ip address of target

    port(int) - port address to use

    retry(int) - number of times to retry

    Returns time.time() if offline, True if online
    """
    logger.debug("Site {} check started".format(ip))
    for x in range(1, retry + 1):
        if not portdown(ip, port):
            break
    else:
        logger.debug("Site  {} check complete".format(ip))
        return ip, time.time()
    logger.debug("Site {} check complete".format(ip))
    return ip, False


def internet_working(ip='8.8.8.8', port=53):
    """Checks if socket can connect to a remote ip, Google DNS by default"""
    return not portdown(ip, port)


def update_sites(sites, result):
    """Updates a dict with values from a tuple
    
    sites(dict) - tracks which stores are up/down
    
    result(tup) - in the format of ip, down). Down is False if site up
    
    Return the updated sites(dict) """
    sites_down = []
    for ip, down in result:
        if down:
            sites_down.append(sites[ip]['name'])
            if not sites[ip].get('down'):
                sites[ip]['down'] = down
        else:
            sites[ip]['down'] = False
    if sites_down:
        logger.warning("{down} currently offline.".format(
            down=", ".join(sites_down)))
    return sites


def total_down(sites):
    """Return a string of sites which are not online, based on sites(dict)"""
    down = ", ".join(val['name'] for val in sites.values() if val['down'])
    if down:
        return down
    else:
        return None


def build_body(name, down, ip, port):
    """Builds a generic email template

    name(str) - site's name

    down(long) - epoc time of last time the site was online

    ip(str) - ip address of site

    port(int) - port scanned

    Returns the email body text"""
    return (
        "WARNING! {name} IS OFFLINE!\nLast online {down}"
        "Cannot connect to {ip}:{port}\n\n"
        "Please contact {name} to verify if there is a known issue.\n"
        "TIP: Power cycling the Shaw cable modem often fixes intermittent issues. "
        "This involves unplugging the modem from the power for 30 seconds, "
        "then plugging it back in, but be careful not to power cycle the wrong device.\n"
        "If the issue persists for more than 15 minutes and the store infrastructure seems fine, "
        "contact Shaw Technical Support @ 1-877-742-9249\n\n"
        "This alert was auto-generated. Do not reply").format(
            name=name, down=time.ctime(down), ip=ip, port=port)


def recently_emailed(emailed):
    """Return True if emailed(float) is less than 4hours from time.time, else False"""
    return time.time() - emailed < 14400


def send_email(name, ip, port, down, creds):
    """Assembles and sends an email

    name(str) - site name

    ip(str) - site ip

    port(int) - site port

    down(str) - last online epoch time

    creds(dict) - contains to, from, subject fields

    Returns the message id if sucessful
    """
    body = build_body(name, down, ip, port)
    return emailer.compose_and_send(
        creds['from'], creds['to'], creds['subject'], body
    )

def engine(sites, port, creds, retry):

    if internet_working():
        with multiprocessing.Pool(processes=3) as pool:
            result = pool.starmap(
                check_remote_status, ((ip, port, retry)
                                      for ip in sites.keys()),
            )
        site_status = update_sites(sites, result)
        for ip, v in site_status.items():
            if v.get('down'):
                if not recently_emailed(v['emailed']):
                    send_email(v['name'], ip, port, v['down'], creds)
                    site_status[ip]['emailed'] = time.time()
                    logger.info('{name} down. Email sent'.format(name=v['name']))
    else:
        logger.error(
            "Google unreachable. Check internet connection.")
    return sites
        

def main(settings):

    sites, port, creds, retry = parse_config(settings)
    while True:
        sites = engine(sites, port, creds, retry)
        time.sleep(900)
        

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('configuration_file', nargs='?')
    args = parser.parse_args()
    settings = (args.configuration_file or 'config.ini')
    main(settings)
