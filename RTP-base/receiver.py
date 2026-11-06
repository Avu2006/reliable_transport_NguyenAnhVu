import argparse
import socket
import sys

from utils import PacketHeader, compute_checksum


def send_ack(s, address, seq_num):
    ack_header = PacketHeader(type=3, seq_num=seq_num, length=0, checksum=0)
    ack_header.checksum = compute_checksum(ack_header)
    s.sendto(bytes(ack_header), address)


def receiver(receiver_ip, receiver_port, window_size):
    """TODO: Listen on socket and print received message to sys.stdout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    buffer = {}

    while True:
        # Receive packet; address includes both IP and port
        pkt, address = s.recvfrom(2048)

        # Extract header and payload
        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16 : 16 + pkt_header.length]

        # Verify checksum
        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)
        if pkt_checksum != computed_checksum:
            continue

        if pkt_header.type == 0:
            if expected_seq == 0:
                expected_seq = 1
                send_ack(s, address, 1)
            continue

        elif pkt_header.type == 2:
            if pkt_header.seq_num >= expected_seq + window_size:
                continue

            if pkt_header.seq_num < expected_seq:
                send_ack(s, address, expected_seq)
            elif pkt_header.seq_num > expected_seq:
                buffer[pkt_header.seq_num] = msg
                send_ack(s, address, expected_seq)
            else:
                sys.stdout.buffer.write(msg)
                sys.stdout.buffer.flush()
                expected_seq += 1

                while expected_seq in buffer:
                    sys.stdout.buffer.write(buffer.pop(expected_seq))
                    sys.stdout.buffer.flush()
                    expected_seq += 1

                send_ack(s, address, expected_seq)

        elif pkt_header.type == 1:
            if pkt_header.seq_num == expected_seq:
                send_ack(s, address, pkt_header.seq_num)
                break
            else:
                send_ack(s, address, expected_seq)

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

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()