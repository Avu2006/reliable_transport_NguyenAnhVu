import argparse
import socket
import sys
import time

from utils import PacketHeader, compute_checksum

CHUNK_SIZE = 1456


def make_pkt(pkt_type, seq, data=b""):
    hdr = PacketHeader(type=pkt_type, seq_num=seq, length=len(data), checksum=0)
    hdr.checksum = compute_checksum(hdr / data)
    return bytes(hdr / data)


def parse_ack(raw_pkt):
    if len(raw_pkt) < 16:
        return False, 0
    hdr = PacketHeader(raw_pkt[:16])
    body = raw_pkt[16 : 16 + hdr.length]
    c = hdr.checksum
    hdr.checksum = 0
    if compute_checksum(hdr / body) == c and hdr.type == 3:
        return True, hdr.seq_num
    return False, 0


def sender(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (receiver_ip, receiver_port)

    msg = sys.stdin.buffer.read()
    chunks = [msg[i : i + CHUNK_SIZE] for i in range(0, len(msg), CHUNK_SIZE)] if msg else []
    total_pkts = len(chunks)

    packets = {}
    for i, chunk in enumerate(chunks):
        packets[i + 1] = make_pkt(2, i + 1, chunk)

    s.sendto(make_pkt(0, 0), dest)
    while True:
        pkt, _ = s.recvfrom(2048)
        valid, ack_seq = parse_ack(pkt)
        if valid and ack_seq == 1:
            break

    base = 1
    next_seq = 1
    last_ack_time = time.time()

    while next_seq <= total_pkts and next_seq < base + window_size:
        s.sendto(packets[next_seq], dest)
        next_seq += 1

    while base <= total_pkts:
        remain = max(0.0, 0.5 - (time.time() - last_ack_time))
        s.settimeout(remain)
        try:
            pkt, _ = s.recvfrom(2048)
            valid, ack_seq = parse_ack(pkt)
            if valid and ack_seq > base:
                base = ack_seq
                last_ack_time = time.time()

                while next_seq <= total_pkts and next_seq < base + window_size:
                    s.sendto(packets[next_seq], dest)
                    next_seq += 1
        except socket.timeout:
            for seq in range(base, next_seq):
                s.sendto(packets[seq], dest)
            last_ack_time = time.time()

    end_seq = total_pkts + 1
    s.sendto(make_pkt(1, end_seq), dest)
    s.settimeout(0.5)
    try:
        while True:
            pkt, _ = s.recvfrom(2048)
            valid, ack_seq = parse_ack(pkt)
            if valid and ack_seq == end_seq:
                break
    except socket.timeout:
        pass

    s.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()