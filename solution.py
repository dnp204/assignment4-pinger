import socket
from socket import AF_INET, SOCK_RAW, getprotobyname, gethostbyname, htons
import os
import sys
import struct
import time
import select
import statistics
import math
import binascii
# Should use stdev

ICMP_ECHO_REQUEST = 8


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    recPacket = bytes()

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        end_time = time.time()
        howLongInSelect = (end_time - startedSelect)
        if whatReady[0] == []:  # Timeout
            raise RuntimeError("Request timed out.")

        timeReceived = time.time()
        buffer, addr = mySocket.recvfrom(1024)

        # Fill in start

        # Fetch the ICMP header from the IP packet
        recPacket += buffer
        if len(recPacket) >= 16:
            break

        # Fill in end
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            raise RuntimeError("Request timed out.")

    # skip IP header [why is it here?]
    (htype, hcode, hchecksum, hid, hseq, htime) = struct.unpack('bbHHhd', recPacket[20:])
    return end_time - htime


def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")

    # SOCK_RAW is a powerful socket type. For more details:   https://sock-raw.org/papers/sock_raw
    mySocket = socket.socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF  # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    try:
        delay = receiveOnePing(mySocket, myID, timeout, destAddr)
        delay *= 1000

    except RuntimeError as e:
        delay = math.nan
        print(e)

    mySocket.close()
    return delay


def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,  	
    # the client assumes that either the client's ping or the server's pong is lost
    try:
        dest = gethostbyname(host)
    except socket.gaierror:
        print(f"Ping request could not find host {host}. Please check the name and try again")
        return ['0.0'] * 4

    print("Pinging " + dest + " using Python:")
    print("")
    
    #Send ping requests to a server separated by approximately one second
    #Add something here to collect the delays of each ping in a list so you can calculate vars after your ping
    delays = []
    
    for i in range(0, 4):  # Four pings will be sent (loop runs for i=0, 1, 2, 3)
        delay = doOnePing(dest, timeout)
        print(delay)
        delays.append(delay)
        time.sleep(1)  # one second
        
    #You should have the values of delay for each ping here; fill in calculation for packet_min, packet_avg, packet_max, and stdev

    not_nans = [d for d in delays if not math.isnan(d)] or [0.0]
    stats = [str(round(min(not_nans), 8)),
             str(round(statistics.mean(not_nans), 8)),
             str(round(max(not_nans), 8)),
             str(round(statistics.stdev(not_nans), 8))]

    return stats


def main():
    stats = ping("google.co.il")
    print(stats)
    stats = ping('127.0.0.1')
    print(stats)
    stats = ping('no.no.e')
    print(stats)


if __name__ == '__main__':
    main()
