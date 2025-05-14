import socket


def find_open_port(max_trials=10):
    """
    Find an open port on the local machine. Starting with 8081
    """
    import random

    port = random.randint(8081, 65535)

    while max_trials > 0:
        max_trials -= 1
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                port = random.randint(8081, 65535)
                continue
            except Exception as e:
                print(f"Error finding open port: {e}")
                return None


def get_host_ip_addr():
    # very sgs-related util
    # get hostname
    hostname = socket.gethostname()
    if "sgs" in hostname:
        # get ip address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    else:
        return "host-gateway"