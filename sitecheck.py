#!/usr/bin/env python3
# Checks the status of ips by connecting to a port and reporting on the result

import socket
import time
import configparser
import os
import logging
import multiprocessing
from functools import partial

import emailer

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.CRITICAL)
logging.getLogger('googleapiclient.discovery').setLevel(logging.CRITICAL)
logging.basicConfig(format='%(asctime)s %(levelname)-4s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def parse_config(config_file):
    """ Accepts INI file, returns sites(dict), port(int), creds(dict), retry(int)"""
    config = configparser.SafeConfigParser()
    config.read(config_file)
    sites = {ip: {'name': site} for site, ip in config['sites'].items()}
    return sites, config['settings'], config['email']


def check_site_status(ip, port, retry=5):
    """ Attempts to connect to an ip with 10 retries if the ip/port are not responding

    ip(str) - ip address of target

    port(int) - port address to use

    retry(int) - (optional) number of times to retry

    Return time.time() if offline, True if online
    """
    for x in range(1, retry+1):
        logger.debug(f"{ip} Scanning")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            result = s.connect_ex((ip, port))
        logger.debug(f'{ip} Completed')
        if not result:
            return ip, None
    return ip, time.time()


def internet_working(ip='8.8.8.8', port=53):
    """Checks if socket can connect to a remote ip, Google DNS by default"""
    return not check_site_status(ip, port)[1]


def recently_emailed(emailed):
    """Return True if emailed(float epoc time) is less than 4hours ago, else False"""
    return time.time() - emailed < 14400


def quiet_hours(start, stop, time_to_test=int(time.strftime("%H"))):
    """Return True if time_to_test(int) is between start(int), stop(int), time_to_test(int)"""
    if start > stop:
        return time_to_test >= start or time_to_test <= stop
    else:
        return time_to_test >= start and time_to_test <= stop


def build_body(name, ip, port, down, advice):
    """Return email body text (str) based on parameters name(str), down(long), ip(str), port(int), advice(string)"""
    body = "\n\n".join((
        f"WARNING! Site: {name.capitalize()} IS OFFLINE!",
        f"Last online {time.ctime(down)}",
        f"Details :: could not connect to {ip} on port {port}",
        "Please contact the site to verify if this is a known issue.",
        f"TIP: {advice}",
        "This alert was auto-generated.\nDo not reply"))
    return body


def send_email(body, creds):
    """Assembles and sends an email

    body(str) - body text of the e-mail

    creds(dict) - contains to, from, subject fields

    Returns the message id if sucessful
    """
    return emailer.compose_and_send(
        creds['from'], creds['to'], creds['subject'], body
    )


def engine(sites, config, creds):
    
    port = int(config.get('port'))
    retry = int(config.get('retry'))
    check_status = partial(check_site_status, port=port, retry=retry)
    quiet_start = int(config.get('quiet_start'))
    quiet_stop = int(config.get('quiet_stop'))

    if internet_working():
        logger.info('Scan started')
        with multiprocessing.Pool(processes=10) as pool:
            results = pool.map(check_status, sites.keys(),)
        for ip, down in results:
            if down:
                if 'down' not in sites[ip]:
                    sites[ip]['down'] = down
                if not quiet_hours(quiet_start, quiet_stop):
                    if not recently_emailed(sites[ip].get('emailed', 0)):
                        body = build_body(sites[ip]['name'], ip, port, sites[ip]['down'], creds['advice'])
                        send_email(body, creds)
                        sites[ip]['emailed'] = time.time()
                        logger.info(f"{sites[ip]['name']} down. Email sent")
                else:
                    logger.info(
                        f"{sites[ip]['name']} down, but quiet hours in effect"
                        )
            elif not down and 'down' in sites[ip]:
                sites[ip].pop('down')
    else:
        logger.error("Google unreachable. Check internet connection.")
    return sites


def main(config_file):

    sites, config, email_creds = parse_config(config_file)
    while True:
        sites = engine(sites, config, email_creds)
        time.sleep(900)


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('configuration_file', nargs='?')
    args = parser.parse_args()
    config_file = (args.configuration_file or 'config.ini')
    main(config_file)
