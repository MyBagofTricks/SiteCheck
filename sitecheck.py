#!/usr/bin/python36
import asyncio
import asyncore
from concurrent.futures import ThreadPoolExecutor
import configparser
import logging
import time
from argparse import ArgumentParser
from asyncio import Queue
from collections import namedtuple

import emailer as gmailhandler

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.CRITICAL)
logging.getLogger('googleapiclient.discovery').setLevel(logging.CRITICAL)
logging.basicConfig(format='[%(asctime)s] [%(levelname)s] -- %(message)s')
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

scan_queue = Queue()
email_queue = Queue()


class Message:
    """Builds an alert message with the ability to email it"""
    def __init__(self, name, ip, port, down, advice):
        self.name = name
        self.ip = ip
        self.down = down
        self.port = port
        self.advice = advice


    async def send_email(self, creds):
        """Sends an email using accompanying emailer module, using Gmail and Oauth2

        creds(dict): dict with to and subject fields, from config.ini
        """
        self.body = "\n\n".join((
            f"WARNING! Site: {self.name.capitalize()} has been offline since {time.ctime(self.down)}",
            f"Details :: could not connect to {self.ip}",
            "Please contact the site to verify if this is a known issue.",
            f"TIP: {self.advice}",
            "This alert was auto-generated.\nDo not reply"))
        await asyncio.sleep(0)
        gmailhandler.compose_and_send(creds['to'], creds['subject'], self.body)
        


def parse_config(config_file):
    """ Accepts INI file, returns sites(dict), creds(dict)"""
    config = configparser.SafeConfigParser()
    try:
        config.read(config_file)
        email = dict(config.items('email'))
        sites = {ip: {'name': name} for name, ip in config['sites'].items()}
    except Exception as err:
        LOGGER.info(f'Error in {config_file} {err} Check formatting in config.ini.example')
        raise SystemExit
    return sites, email


def parse_args():
    """Sets up command line arguments. Return ArgumentParser object"""    
    import argparse
    parser = argparse.ArgumentParser(description="Sitecheck - Yet Another Port Scanner")
    parser.add_argument(
        "-c", "--config",  help="Configuration file - Default=config.ini",
        default="config.ini")
    parser.add_argument(
        "-p", "--port", type=int, help="Port to scan - Default=9111",
        default=9111)
    parser.add_argument(
        "-proc", "--processes", type=int, help="Number of processes to use - Default=3",
        default=3)
    parser.add_argument(
        "-q", "--quiet", type=int, nargs=2, 
        help='Start and End of quiet hours Off by Default. Format \"-q 1 5\"',
        default=False)
    parser.add_argument(
        "-r", "--retry", type=int, help="Number of retries before assuming site is down - Default=5",
        default=5)
    parser.add_argument(
        "-s", "--sleep", type=int, help="Time in seconds between scans - Default=900 (15min)",
        default=900)
    parser.add_argument(
        "-v", "--verbose", help="Verbose log output", action="store_true")
    return parser.parse_args()

    
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


async def check_site(ip, port, retry):
    """ Attempts to connect to an ip with 2 retries if the ip/port are not responding

    ip(str) - ip address of scan

    port(int) - port to scan

    retry(int) - (optional) number of times to retry

    Return time.time() if offline, None if online
    """
    LOGGER.debug(f"[{ip:}:{port}] Scan Started")
    for iteration in range(retry):
        await asyncio.sleep(0)
        fut = asyncio.open_connection(ip, port)
        try:
            reader, writer = await asyncio.wait_for(fut, timeout=5)
            return None
        except Exception as exc:
            pass
        finally:
            fut.close()
    LOGGER.debug(f'[{ip}:{port}] Connection Failed!')
    return time.time()


async def email_worker(sites, email_config, quiet):
    """Worker that sends emails every 4 hours if a site is down

    sites(dict) - structure: ip: {name:name} - built from config.ini

    email_config(dict) email settings built from config.ini
    """
    while True:
        name, ip, down = await email_queue.get()
        if not quiet_hours(quiet):
            if sites[ip].get('emailed', 0) < time.time() - 14400:
                Email = Message(name, ip, port, down, email_config['advice'])
                await Email.send_email(email_config)
                sites[ip]['emailed'] = time.time()
                LOGGER.info(f"[{ip}::{port}] Down! Email sent!")
        else:
            LOGGER.debug(f"{ip} down but quiet hours in effect: {quiet}")


async def schedule_worker(sites, port, retry, sleep):
    """ Schedules scans

    sites(dict) - structure: ip: {name:name} - built from config.ini

    """
    while True:
        [await scan_queue.put((ip, port, retry)) for ip in sites.keys()]
        LOGGER.info(f"{scan_queue.qsize()} sites queued to be scanned")
        await asyncio.sleep(sleep)


async def scan_worker(sites):
    """Pulls queued scans from scan_queue

    sites(dict) - built from config.ini
    """
    while True:
        ip, port, retry = await scan_queue.get()
        down = await check_site(ip, port, retry)
        if down:
            if 'down' not in sites[ip]:
                sites[ip]['down'] = down
            name = sites[ip]['name']
            await email_queue.put((name, ip, down))
        else:
            if 'down' in sites[ip]:
                sites[ip].pop('down')
        asyncio.sleep(0)


if __name__ == '__main__':
    flags = parse_args()
    port = flags.port
    retry = flags.retry
    sleep = flags.sleep

    if flags.verbose:
        LOGGER.setLevel(logging.DEBUG)
    sites, email_config = parse_config(flags.config)

    loop = asyncio.get_event_loop()

    scanners = [asyncio.ensure_future(scan_worker(sites)) for _ in range(flags.processes)]
    emailer = asyncio.ensure_future(email_worker(sites, email_config, flags.quiet))
    schedule_scan = asyncio.ensure_future(schedule_worker(sites, port, retry, sleep))

    futures = asyncio.gather(schedule_scan, emailer, *scanners)

    loop.run_until_complete(futures)
    loop.close()