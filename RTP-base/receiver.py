import argparse
import socket
import sys

from utils import PacketHeader, compute_checksum


def send_ack(s, address, seq_num):
    ack_header = PacketHeader(type=3, seq_num=seq_num, length=0, checksum=0)
    ack_header.checksum = compute_checksum(ack_header)
    s.sendto(bytes(ack_header), address)


def receiver(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    buffer = {}
    end_received = False
    end_seq = -1

    while True:
        pkt, address = s.recvfrom(2048)

        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16 : 16 + pkt_header.length]

        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)
        if pkt_checksum != computed_checksum:
            continue

        if pkt_header.type == 0:
            if expected_seq == 0:
                expected_seq = 1
                send_ack(s, address, 1)
            elif expected_seq == 1:
                send_ack(s, address, 1)
            continue

        if expected_seq == 0:
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

                if end_received and expected_seq == end_seq:
                    send_ack(s, address, end_seq)
                    break

        elif pkt_header.type == 1:
            end_received = True
            end_seq = pkt_header.seq_num
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
