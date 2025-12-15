# Virtual Printer

A virtual printer system that accepts print jobs via raw TCP socket (port 9100) or HTTP API (port 8000), automatically detects file formats (PDF, PostScript, PCL), and renders them to PNG images using Ghostscript.

## Features

- **Raw Socket Server (Port 9100)**: Standard raw printer protocol compatible with network printing tools
- **REST API (Port 8000)**: FastAPI-based HTTP interface for programmatic access
- **Format Detection**: Automatically detects PDF, PostScript, and PCL formats
- **Ghostscript Rendering**: Converts print jobs to high-quality PNG images
- **Job Management**: Track all print jobs with metadata and access rendered outputs
- **Concurrent Processing**: Handles multiple simultaneous print jobs
- **Configurable**: Adjust DPI, processing delay, and output directory

## Prerequisites

### Docker (Recommended)
- Docker
- Docker Compose
- Make (optional, for convenience commands)

### Manual Installation
- Python 3.7+
- Ghostscript (must be installed and available in PATH)

### Installing Ghostscript (Manual Installation Only)

**macOS:**
```bash
brew install ghostscript
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ghostscript
```

**Windows:**
Download from https://www.ghostscript.com/download/gsdnld.html

## Quick Start (Docker)

1. Start both servers with Docker Compose:
```bash
make up
```

Or without Make:
```bash
docker-compose up -d
```

2. View logs:
```bash
make logs
```

3. Stop servers:
```bash
make down
```

That's it! The servers are now running:
- Socket Server: `localhost:9100`
- API Server: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

### Available Make Commands

```bash
make help          # Show all available commands
make build         # Build Docker images
make up            # Start all services
make down          # Stop and remove services
make restart       # Restart services
make logs          # View logs from all services
make logs-socket   # View socket server logs only
make logs-api      # View API server logs only
make status        # Show service status
make clean         # Stop services and remove outputs
make test          # Test both servers
```

## Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Verify Ghostscript is installed:
```bash
gs --version
```

## Usage

### Running the Socket Server

Start the raw printer socket server on port 9100:

```bash
python socket_server.py
```

Send print jobs via netcat or similar tools:
```bash
cat document.pdf | nc localhost 9100
cat document.pcl | nc localhost 9100
```

### Running the API Server

Start the FastAPI server on port 8000:

```bash
python api_server.py
```

Or with uvicorn directly:
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### API Examples

**Submit a print job:**
```bash
curl -X POST -F "file=@document.pdf" http://localhost:8000/print
```

**List all jobs:**
```bash
curl http://localhost:8000/jobs
```

**Get job details:**
```bash
curl http://localhost:8000/jobs/{job_id}
```

**Download rendered page:**
```bash
curl http://localhost:8000/jobs/{job_id}/pages/1 -o page1.png
```

### Running Both Servers

**With Docker (Recommended):**
```bash
make up
```

**Without Docker:**
You can run both servers simultaneously in separate terminals:

**Terminal 1:**
```bash
python socket_server.py
```

**Terminal 2:**
```bash
python api_server.py
```

## Docker Details

### Architecture

The Docker setup runs two separate containers:
- `virtual-printer-socket`: Raw socket server on port 9100
- `virtual-printer-api`: FastAPI server on port 8000

Both containers:
- Share the same `./outputs` directory via volume mount
- Use the same base Docker image
- Run on a shared network for potential inter-service communication
- Restart automatically unless stopped

### Dockerfile

The Dockerfile is based on `python:3.11-slim` and includes:
- Ghostscript installation
- Python dependencies
- Application code
- Pre-created output directory

### Environment Variables

You can customize the configuration by modifying `config.py` or by setting environment variables in `docker-compose.yml`.

## Configuration

Edit `config.py` to customize settings:

```python
@dataclass
class Config:
    socket_port: int = 9100              # Raw socket server port
    api_port: int = 8000                 # FastAPI server port
    output_dir: str = "./outputs"        # Output directory for rendered jobs
    dpi: int = 300                       # Rendering DPI
    processing_delay_kb_per_sec: int = 50  # Simulated processing delay (KB/s)
```

## Output Structure

Each print job creates a directory under `outputs/` with the following structure:

```
outputs/
  └── {timestamp}/
      ├── raw.{ext}           # Original print data (pdf/ps/pcl)
      ├── page_001.png        # Rendered page 1
      ├── page_002.png        # Rendered page 2
      ├── ...
      └── metadata.json       # Job metadata
```

### Metadata Format

```json
{
  "job_id": "20231106_143022_123456",
  "timestamp": "20231106_143022_123456",
  "file_type": "pdf",
  "file_size": 524288,
  "page_count": 3,
  "source": "socket:192.168.1.100:54321",
  "dpi": 300,
  "error": null
}
```

## Supported Formats

- **PDF**: Files starting with `%PDF`
- **PostScript**: Files starting with `%!PS`
- **PCL**: Files containing ESC character (`\x1b`) in first 100 bytes

## Error Handling

- Unknown file types are rejected with appropriate logging
- Ghostscript rendering errors are captured and logged in metadata
- Malformed data is handled gracefully with error responses
- Temporary files are cleaned up automatically

## Logging

All servers log to stdout with timestamps, including:
- Incoming connections and file sizes
- Detected file types
- Rendering progress and page counts
- Errors and warnings

## API Documentation

Once the API server is running, visit http://localhost:8000/docs for interactive Swagger UI documentation.

## License

MIT
