# -*- coding: utf-8 -*-
'''
Dynamic DNS resolving tool for RaspberryPi. 
Used to resolve current IP to given domain. 
For DNSPod ( http://DNSPod.cn ) only. 
Date: 2014.11.18
Joker Qyou <Joker.Qyou@gmail.com>
'''
import json
import os
import logging
import socket
import sys
import time

import requests

import pdb

config = {
    'email': '', 
    'password': '', 
    'domain': '', 
    'subdomain': '', 
    'optauth': True
}

CODE_SAVE, CODE = 'ddns.cookies', {}
NO_CODE = not os.path.exists(CODE_SAVE)

if not NO_CODE:
    with open(CODE_SAVE) as f:
        CODE = json.load(f)

API_BASE = 'https://dnsapi.cn/'

public_payloads = {
    'login_email': config['email'], 
    'login_password': config['password'], 
    'format': 'json', 
    'lang': 'cn', 
    'error_on_empty': 'no'
}


def dns_request(api, params={}):
    '''Common wrapper for requesting DNSPod APIs.'''
    for k in params.keys():
        if params.get(k, None) is None:
            params.pop(k, None)
    payloads = public_payloads.copy()
    payloads.update(params)
    cookies = {}
    if not NO_CODE and CODE['expire_at'] > time.time():
        cookies = CODE.copy()
        cookies.pop('expire_at', None)
    else:
        payloads.update({
            'login_code': raw_input(u'Please input your optauth code:').strip(),
            'login_remember': 'yes'
        })
    response = requests.post('%s%s' % (API_BASE, api, ), 
                             data=payloads, 
                             headers={
                                 'User-Agent': 'PiDDNS/1(Joker.Qyou@gmail.com)'
                             }, 
                             cookies=cookies)
    if NO_CODE or CODE['expire_at'] <= time.time():
        code_cookie = response.cookies.get_dict()
        for cookie in code_cookie.iterkeys():
            if cookie.startswith('t_'):
                CODE.update({
                    cookie: code_cookie[cookie], 
                    'expire_at': time.time() + 1.0*60*60*24*30
                })
                with open(CODE_SAVE, 'w') as wf:
                    json.dump(CODE, wf)

    info = json.loads(response.content)
    if info['status']['code'] != '1':
        logger.warn(
            'Unsuccessful call to `%s` API, detailed response: ' % api, 
        )
        logger.warn(response.content)
        raise RuntimeError, u'Unsuccessful call to `%s` with return code `%s`' % (api, info['status']['code'], )

    return info

def get_domain_info(domain):
    '''
    Get info of a domain
    '''
    data = dns_request('Domain.Info', params={'domain': config['domain']})
    return data.get('domain')

def get_record_list(domain_id, subdomain=None):
    '''
    Get record list of a domain
    '''
    data = dns_request('Record.List', 
                       params={
                           'domain_id': domain_id, 
                           'subdomain': subdomain
                       })
    return data.get('records')

def get_record_info(domain_id, record_id):
    data = dns_request('Record.Info', 
                       params={'domain_id': domain_id, record_id: record_id})
    return data.get('record')

def set_ddns():
    domain = get_domain_info(config['domain'])
    records = get_record_list(domain.get('id'), subdomain=config['subdomain'])
    target_record = None
    for record in records:
        if record.get('type') == 'A' \
        and record.get('name') == config['subdomain']:
            target_record = record.copy()

    if target_record is None:
        logger.error(u'No target record found, full record list matched: ')
        logger.error(json.dumps(records))
        raise RuntimeError, u'No target record found'

    if target_record.get('value') == get_self_ip():
        logger.info(u'No need to update DDNS settings, self IP unchanged')
        return

    data = dns_request('Record.Ddns', 
                       params={
                           'domain_id': domain.get('id'), 
                           'record_id': target_record.get('id'), 
                           'sub_domain': config['subdomain'], 
                           'record_line': target_record.get('line')
                       })
    return

def get_self_ip():
    query_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    query_socket.connect(('ns1.dnspod.net', 6666, ))
    recv = query_socket.recv(16) 
    query_socket.close()
    return recv

def test():
    try:
        data = dns_request('Domain.Info', params={'domain': config['domain']})
        print data
    except Exception, e:
        print e
    finally:
        pdb.set_trace()

def _excepthook(type, value, tb):
    logger.exception(
        "{0} - Uncaught exception: {1}\n{2}".format(
            datetime.strftime(datetime.now(), '%H:%M:%S'), 
            str(value), ''.join(traceback.format_tb(tb))
        )
    )
    pdb.set_trace()

if __name__ == '__main__':
    sys.excepthook = _excepthook
    print get_self_ip()
