#!/usr/bin/python
"""

"""
import asyncio
import json
import pyaudio
import math
import socket
import time


def rms(data, width=8):
    sum_squares = 0
    if width == 8:
        sum_squares = sum([v*v for v in data])
        return int(math.sqrt(sum_squares / len(data)))


def sample(audio, connection):
    bytes_out = 0
    buf = bytearray(1)

    while True:
        vol = rms(audio.read(chunk))
        buf[0] = vol
        bytes_out += connection.send(buf)
        time.sleep(1)


if __name__ == '__main__':

    pa = pyaudio.PyAudio()
    chunk = 1024
    stream = pa.open(format = pyaudio.paInt8,
                     channels = 1,
                     rate = 44100,
                     input=True,
                     frames_per_buffer = chunk)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.bind(('', 2263))
    sock.listen(5)
    while True:
        cnx, addr = sock.accept()
        cnx.settimeout(0)
        print('Connected to {}'.format(addr))
        sample(stream, cnx)