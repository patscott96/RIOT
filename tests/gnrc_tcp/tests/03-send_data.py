#!/usr/bin/env python3

# Copyright (C) 2018   Simon Brummer <simon.brummer@posteo.de>
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import os
import sys
import threading

from testrunner import run
from shared_func import TcpServer, generate_port_number, get_host_tap_device, \
                        get_host_ll_addr, get_riot_if_id, setup_internal_buffer, \
                        write_data_to_internal_buffer, verify_pktbuf_empty, \
                        sudo_guard


def tcp_server(port, shutdown_event, expected_data):
    with TcpServer(port, shutdown_event) as tcp_srv:
        assert tcp_srv.recv(len(expected_data)) == expected_data


def testfunc(child):
    port = generate_port_number()
    shutdown_event = threading.Event()

    # Try to send 2000 byte from RIOT to the Host System.
    data = '0123456789' * 200
    data_len = len(data)

    # Verify that RIOT Applications internal buffer can hold test data.
    assert setup_internal_buffer(child) >= data_len

    server_handle = threading.Thread(target=tcp_server, args=(port, shutdown_event, data))
    server_handle.start()

    target_addr = get_host_ll_addr(get_host_tap_device()) + '%' + get_riot_if_id(child)

    # Setup RIOT Node to connect to host systems TCP Server
    child.sendline('gnrc_tcp_tcb_init')
    child.sendline('gnrc_tcp_open_active [{}]:{} 0'.format(target_addr, str(port)))
    child.expect_exact('gnrc_tcp_open_active: returns 0')

    # Send data from RIOT Node to Linux
    write_data_to_internal_buffer(child, data)
    child.sendline('gnrc_tcp_send 0')
    child.expect_exact('gnrc_tcp_send: sent ' + str(data_len))

    # Close connection and verify that pktbuf is cleared
    shutdown_event.set()
    child.sendline('gnrc_tcp_close')
    server_handle.join()

    verify_pktbuf_empty(child)

    print(os.path.basename(sys.argv[0]) + ': success')


if __name__ == '__main__':
    sudo_guard()
    sys.exit(run(testfunc, timeout=5, echo=False, traceback=True))
