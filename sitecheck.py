#!/usr/bin/env python3

"""Sitecheck - Basic Port Scanner 
Scans multiple sites by ip and a specified port
Reads settings from config.ini
"""
import configparser
import logging
import multiprocessing
import socket
import time
from functools import partial

import emailer

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.CRITICAL)
logging.getLogger('googleapiclient.discovery').setLevel(logging.CRITICAL)
logging.basicConfig(format='[%(asctime)s] [%(levelname)s] -- %(message)s')
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def parse_config(config_file):
    """ Accepts INI file, returns sites(dict), creds(dict)"""
    config = configparser.SafeConfigParser()
    try:
        config.read(config_file)
        sites = {ip: {'name': site} for site, ip in config['sites'].items()}
        email = config['email']
    except Exception as err:
        print(f'Error in {config_file} {err} Check formatting in config.ini.example')
        raise SystemExit
    return sites, email


def parse_args():
    """Parses arguments to Return ArgumentParser object"""    
    import argparse
    parser = argparse.ArgumentParser(description="Sitecheck - Yet Another Port Scanner")
    parser.add_argument("-c", "--config", 
                        help="Configuration file - Default=config.ini",
                        default="config.ini")
    parser.add_argument("-p", "--port", type=int,
                        help="Port to scan - Default=9111",
                        default=9111)
    parser.add_argument("-proc", "--processes", type=int,
                        help="Number of processes to use - Default=3",
                        default=3)
    parser.add_argument("-q", "--quiet", type=int, nargs=2,
                        help='Start and End of quiet hours Off by Default.\
                        Format \"-q 1 5\"',
                        default=False)
    parser.add_argument("-r", "--retry", type=int,
                        help="Number of retries before assuming site is down - Default=5",
                        default=5)
    parser.add_argument("-s", "--sleep", type=int,
                        help="Time in seconds between scans - Default=900 (15min)",
                        default=900)
    return parser.parse_args()
    


def check_site_status(ip, port, retry):
    """ Attempts to connect to an ip with 10 retries if the ip/port are not responding

    ip(str) - ip address of target

    port(int) - port address to use

    retry(int) - (optional) number of times to retry

    Return time.time() if offline, True if online
    """
    LOGGER.debug(f"{ip:<16} Scanning")
    for x in range(1, retry+1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            result = s.connect_ex((ip, port))
        if not result:
            LOGGER.debug(f'{ip:<16} Completed')
            return ip, None
        LOGGER.debug(f'{ip:<16} OFFLINE {x} of {retry}')
    return ip, time.time()


def recently_emailed(emailed):
    """Return True if emailed(float epoc time) is less than 4hours ago, else False"""
    return time.time() - emailed < 14400


def quiet_hours(quiet, local_hour=int(time.strftime("%H"))):
    """Determines whether quiet hours are in effect based on local time

    quiet(list) - contains two numbers, a start and end hour.

    local_hour(time obj) - local hour using time module

    Return False if quiet is False, or local_hour does not fall within quiet's hour range,
    else Return True"""
    if not quiet:
        return False
    else:
        start = quiet[0]
        stop = quiet[1]
        if start > stop:
            return local_hour >= start or local_hour <= stop
        else:
            return local_hour >= start and local_hour <= stop


def build_body(name, ip, down, advice):
    """Return email body text (str) based on parameters name(str), down(long), ip(str), port(int), advice(string)"""
    body = "\n\n".join((
        f"WARNING! Site: {name.capitalize()} IS OFFLINE!",
        f"Last online {time.ctime(down)}",
        f"Details :: could not connect to {ip}",
        "Please contact the site to verify if this is a known issue.",
        f"TIP: {advice}",
        "This alert was auto-generated.\nDo not reply"))
    return body


def send_email(body, creds):
    """Assembles and sends an email

    body(str) - body text of the e-mail

    creds(dict) - contains to and subject fields

    Returns the message id if sucessful
    """
    return emailer.compose_and_send(creds['to'], creds['subject'], body)


def engine(sites, creds, flags):
    """ Runs the script

    sites//creds (dict) - built by parse_Config

    flags(argparse obj) - flags from cmd line

    Return updated sites dict for next iteration
    """
    check_status = partial(check_site_status, port=flags.port, retry=flags.retry)
    internet_down = partial(check_site_status, '8.8.8.8', 53, 1)
    
    if not internet_down()[1]:
        LOGGER.info('Scan started')
        with multiprocessing.Pool(processes=flags.processes) as pool:
            results = pool.map(check_status, sites.keys(),)

        for ip, down in results:
            if down:
                if 'down' not in sites[ip]:
                    sites[ip]['down'] = down
                if not quiet_hours(flags.quiet):
                    if not recently_emailed(sites[ip].get('emailed', 0)):
                        body = build_body(sites[ip]['name'], ip, sites[ip]['down'], creds['advice'])
                        send_email(body, creds)
                        sites[ip]['emailed'] = time.time()
                        LOGGER.info(f"{sites[ip]['name'].capitalize()} down. Email sent")
                else:
                    LOGGER.info(
                        f"{sites[ip]['name']} down, but quiet hours in effect"
                        )
            elif not down and 'down' in sites[ip]:
                sites[ip].pop('down')
    else:
        LOGGER.error("Google unreachable. Check internet connection.")
    return sites


def main(flags):
    sites, email = parse_config(flags.config)
    while True:
        sites = engine(sites, email, flags)
        time.sleep(flags.sleep)


if __name__ == '__main__':
    flags = parse_args()
    main(flags)
