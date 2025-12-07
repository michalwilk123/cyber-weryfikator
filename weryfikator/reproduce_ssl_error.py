import socket
import OpenSSL.SSL
import sys

def check_ssl(domain, port=443):
    print(f"Checking {domain}:{port}...")
    context = OpenSSL.SSL.Context(OpenSSL.SSL.TLS_CLIENT_METHOD)
    context.set_verify(OpenSSL.SSL.VERIFY_PEER, lambda conn, cert, errno, depth, ok: True)
    context.set_default_verify_paths()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        sock.connect((domain, port))
        print("Socket connected.")
        
        connection = OpenSSL.SSL.Connection(context, sock)
        connection.set_tlsext_host_name(domain.encode('utf-8'))
        connection.set_connect_state()
        print("Starting handshake...")
        connection.do_handshake()
        print("Handshake done.")
        
        cert_chain = connection.get_peer_cert_chain()
        print(f"Chain length: {len(cert_chain) if cert_chain else 0}")
        
    except OpenSSL.SSL.Error as e:
        print(f"OpenSSL Error caught!")
        print(f"Type: {type(e)}")
        print(f"String representation: '{str(e)}'")
        print(f"Repr: {repr(e)}")
        print(f"Args: {e.args}")
    except Exception as e:
        print(f"Other Error: {e}")
    finally:
        try:
            connection.shutdown()
        except:
            pass
        sock.close()

if __name__ == "__main__":
    check_ssl("google.com")
    check_ssl("gov.pl")

