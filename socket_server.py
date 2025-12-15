import socket
import threading
import logging
from printer_engine import detect_file_type, save_and_render
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def receive_all_data(conn: socket.socket, buffer_size: int = 8192, timeout: float = 5.0) -> bytes:
    conn.settimeout(timeout)
    data = b''
    
    try:
        while True:
            chunk = conn.recv(buffer_size)
            if not chunk:
                break
            data += chunk
            conn.settimeout(1.0)
    except socket.timeout:
        pass
    
    return data


def handle_print_job(conn: socket.socket, addr: tuple):
    try:
        logger.info(f"Connection from {addr[0]}:{addr[1]}")
        
        data = receive_all_data(conn)
        
        if not data:
            logger.warning(f"No data received from {addr}")
            return
        
        file_type = detect_file_type(data)
        
        if file_type == 'unknown':
            logger.warning(f"Unknown file type from {addr}, size={len(data)} bytes")
            return
        
        job_id, metadata = save_and_render(data, file_type, source=f"socket:{addr[0]}:{addr[1]}")
        
        if metadata.get('error'):
            logger.error(f"Job {job_id} failed: {metadata['error']}")
        else:
            logger.info(f"Job {job_id} completed: {metadata['page_count']} pages")
    
    except Exception as e:
        logger.error(f"Error handling connection from {addr}: {e}")
    
    finally:
        conn.close()


def start_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('0.0.0.0', config.socket_port))
        sock.listen(5)
        logger.info(f"Raw printer socket server listening on port {config.socket_port}")
        
        while True:
            conn, addr = sock.accept()
            thread = threading.Thread(target=handle_print_job, args=(conn, addr), daemon=True)
            thread.start()
    
    except KeyboardInterrupt:
        logger.info("Socket server shutting down...")
    except Exception as e:
        logger.error(f"Socket server error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    start_socket_server()
