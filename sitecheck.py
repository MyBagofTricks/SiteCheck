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
logging.basicConfig(format='%(asctime)s %(levelname)-4s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def parse_config(config_file):
    """ Accepts INI file, returns sites(dict), port(int), creds(dict), retry(int)"""
    config = configparser.SafeConfigParser()
    config.read(config_file)
    sites = {ip: {'name': site} for site, ip in config['sites'].items()}
    settings = config['settings']
    email_creds = config['email']
    return sites, settings, email_creds


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
    """ Attempts to connect to an ip with 10 retries if the ip/port are not responding

    ip(str) - ip address of target

    port(int) - port address to use

    retry(int) - number of times to retry

    Returns time.time() if offline, True if online
    """
    logger.debug(f"Started Site {ip}")
    for x in range(1, retry + 1):
        if not portdown(ip, port):
            break
    else:
        logger.debug(f"Complete Site {ip}")
        return ip, time.time()
    logger.debug(f"Complete Site {ip}")
    return ip, False


def internet_working(ip='8.8.8.8', port=53):
    """Checks if socket can connect to a remote ip, Google DNS by default"""
    return not portdown(ip, port)


def recently_emailed(emailed):
    """Return True if emailed(float epoc time) is less than 4hours ago, else False"""
    return time.time() - emailed < 14400


def quiet_hours(start, stop, time_to_test=int(time.strftime("%H"))):
    """Return True if time_to_test(int) is between start(int), stop(int), time_to_test(int)"""
    if start > stop:
        return time_to_test >= start or time_to_test <= stop
    else:
        return time_to_test >= start and time_to_test <= stop


def build_body(name, down, ip, port, advice):
    """Return email body text (str) based on parameters name(str), down(long), ip(str), port(int), advice(string)"""
    return "\n\n".join((
        f"WARNING! Site: {name.capitalize()} IS OFFLINE!",
        f"Last online {time.ctime(down)}",
        f"Details :: could not connect to {ip} on port {port}",
        "Please contact the site to verify if this is a known issue.",
        f"TIP: {advice}",
        "This alert was auto-generated.\nDo not reply"))


def send_email(name, ip, port, down, creds):
    """Assembles and sends an email

    name(str) - site name

    ip(str) - site ip

    port(int) - site port

    down(str) - last online epoch time

    creds(dict) - contains to, from, subject fields

    Returns the message id if sucessful
    """
    body = build_body(name, down, ip, port, creds['advice'])
    return emailer.compose_and_send(
        creds['from'], creds['to'], creds['subject'], body
    )


def engine(sites, config, creds):
    port = int(config.get('port'))
    retry = int(config.get('retry'))
    quiet_start = int(config.get('quiet_start'))
    quiet_stop = int(config.get('quiet_stop'))
    if internet_working():
        logger.info('Scan started')
        with multiprocessing.Pool(processes=3) as pool:
            result = pool.starmap(
                check_remote_status, ((ip, port, retry)
                                      for ip in sites.keys()),
            )
        for ip, down in result:
            if down:
                if not sites[ip].get('down'):
                    sites[ip]['down'] = down
                if not quiet_hours(quiet_start, quiet_stop):
                    if not recently_emailed(sites[ip].get('emailed', 0)):
                        send_email(sites[ip]['name'], ip, port,
                                   sites[ip]['down'], creds)
                        sites[ip]['emailed'] = time.time()
                        logger.warning(f"{sites[ip]['name']} down. Email sent")
                else:
                    logger.warning(
                        f"{sites[ip]['name']} is down, but quiet hours in effect")
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
