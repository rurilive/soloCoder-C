import socket
import uvicorn


def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    port = s.getsockname()[1]
    s.close()
    return port


if __name__ == "__main__":
    port = 3333
    print(f"Starting photo album server on http://localhost:{port}")
    print(f"Press Ctrl+C to stop the server")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
