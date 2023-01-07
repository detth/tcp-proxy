#!/usr/bin/env python3
import socket
import sys
import threading


# contains ASCII printable chars, or a dot(.) if such a char not printable
HEX_FILTER = "".join([(len(repr(chr(i))) == 3) and chr(i) or "." for i in range(256)])


def hexdump(src, length=16, show=True):
    """
    takes some input as bytes or a string and prints a hexdump to the console.

    Args:
        src: input string
        length: symbols length in one line. Defaults to 16.
        show: tells to show results of hexdump. Defaults to True.

    Returns:
        hex value of the index of the first byte in the word,
        the hex value of the word, and printable representation
    """

    # decoding the bytes if a byte string was passed in function
    if isinstance(src, bytes):
        src = src.decode()

    results = list()

    for i in range(0, len(src), length):

        # grab a piece of the string to dump
        word = str(src[i : i + length])

        # replace the string representation of each character for the corresponding character in the raw string
        printable = word.translate(HEX_FILTER)
        hexa = " ".join([f"{ord(c):02X}" for c in word])
        hexwidth = length * 3
        results.append(f"{i:04x} {hexa:<{hexwidth}} {printable}")

    if show:
        for line in results:
            print(line)
    else:
        return results


def receive_from(connection):
    """
    Uses by two ends of the proxy to receive data

    Args:
        connection: remote or local

    Returns:
        Buffer of bytes
    """

    # for accumulate responses from the socket
    buffer = b""
    connection.settimeout(5)

    try:
        while True:
            data = connection.recv(4096)
            if not data:
                break
            buffer += data
    except Exception as e:
        pass
    return buffer


def request_handler(buffer):
    """
    Perform packet modifications
    """
    return buffer


def response_handle(buffer):
    """
    Perform packet modifications
    """
    return buffer


def proxy_handler(client_socket, remote_host, remote_port, receive_first):
    """
    Contains the bulk of the logic for proxy

    Args:
        client_socket: client socket obj
        remote_host: remote address
        remote_port: remote port number
        receive_first: check connect initiation
    """

    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # connect to the remote host
    remote_socket.connect((remote_host, remote_port))

    # check to make sure we don’t need to first initiate a connection
    # to the remote side and request data before going into the main loop
    if receive_first:
        remote_buffer = receive_from(remote_socket)
        hexdump(remote_buffer)

    remote_buffer = response_handle(remote_buffer)
    if len(remote_buffer):
        print(f"[<==] Sending {len(remote_buffer)} bytes to localhost.")
        client_socket.send(remote_buffer)

    while True:
        local_buffer = receive_from(client_socket)
        if len(local_buffer):
            line = f"[==>] Received {len(local_buffer)} bytes from localhost."
            print(line)
            hexdump(local_buffer)

            local_buffer = request_handler(local_buffer)
            remote_socket.send(local_buffer)
            print("[==>] Sent to remote.")

        remote_buffer = receive_from(remote_socket)
        if len(remote_buffer):
            print(f"[<==] Received {len(remote_buffer)} bytes from remote.")
            hexdump(remote_buffer)

            remote_buffer = response_handle(remote_buffer)
            client_socket.send(remote_buffer)
            print("[<==] Sent to localhost.")

        # When there’s no data to send on either side of the connection - close them.
        if not len(local_buffer) or not len(remote_buffer):
            client_socket.close()
            remote_socket.close()
            print("[#] No more data. Closing connections.")
            break


def server_loop(local_host, local_port, remote_host, remote_port, receive_first):
    """
    Creates a socket and then binds to the local host and listens.
    In the main loop, them a fresh connection request comes in,
    we hand it off to the proxy_handler in a new thread,
    which does all of the sending and receiving of bits to either side of the datastream.

    Args:
        local_host: local address
        local_port: local port number
        remote_host: remote address
        remote_port: remote port number
        receive_first: check connect initiation
    """

    # create server socket and bind it.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((local_host, local_port))
    except Exception as e:
        print(f"[-] Error on bind: {e}")

        print(f"[!] Failed to listen on {local_host}:{local_port}")
        print("[!] Check for other listening sockets or correct permissions.")
        sys.exit(0)

    print(f"[*] Listening on {local_host}:{local_port}")
    server.listen(5)
    while True:
        client_socket, addr = server.accept()

        # print out the local connection information
        print(f"> Received incoming connection from {addr[0]}:{addr[1]}")

        # start a thread to talk to the remote host
        proxy_thread = threading.Threкad(
            target=proxy_handler,
            args=(client_socket, remote_host, remote_port, receive_first),
        )
        proxy_thread.start()


def main():
    if len(sys.argv[1:]) != 5:
        print(
            "Usage: ./proxy.py [localhost] [localport] [remotehost] [remoteport] [receive_first]"
        )
        print("Example: proxy.py 127.0.0.1 9000 10.11.121.4 9000 True")

        sys.exit(0)

    local_host = sys.argv[1]
    local_port = int(sys.argv[2])

    remote_host = sys.argv[3]
    remote_port = int(sys.argv[4])

    receive_first = sys.argv[5]

    if "True" in receive_first:
        receive_first = True
    else:
        receive_first = False

    server_loop(local_host, local_port, remote_host, remote_port, receive_first)


if __name__ == "__main__":
    main()
