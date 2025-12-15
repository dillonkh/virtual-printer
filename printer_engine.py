import os
import json
import logging
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Optional, Dict
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def detect_file_type(data: bytes) -> str:
    if data.startswith(b'%PDF'):
        return 'pdf'
    elif data.startswith(b'%!PS'):
        return 'postscript'
    elif b'\x1b' in data[:100]:
        return 'pcl'
    return 'unknown'


def get_file_extension(file_type: str) -> str:
    extensions = {
        'pdf': 'pdf',
        'postscript': 'ps',
        'pcl': 'pcl'
    }
    return extensions.get(file_type, 'bin')


def parse_pjl_copies(data: bytes) -> int:
    try:
        header_end = data.find(b'@PJL ENTER LANGUAGE')
        if header_end == -1:
            return 1
        
        header = data[:header_end + 200].decode('ascii', errors='ignore')
        
        qty_match = re.search(r'@PJL SET QTY\s*=\s*(\d+)', header, re.IGNORECASE)
        if qty_match:
            qty = int(qty_match.group(1))
            logger.info(f"Found PJL QTY={qty}")
            return qty
        
        copies_match = re.search(r'@PJL SET COPIES\s*=\s*(\d+)', header, re.IGNORECASE)
        if copies_match:
            copies = int(copies_match.group(1))
            logger.info(f"Found PJL COPIES={copies}")
            return copies
        
        return 1
    except Exception as e:
        logger.warning(f"Error parsing PJL copies: {e}")
        return 1


def render_with_ghostscript(input_path: str, output_dir: str, dpi: int = 300, file_type: str = 'pdf') -> List[str]:
    output_pattern = os.path.join(output_dir, "page_%03d.png")
    
    if file_type == 'pcl':
        command = [
            'gpcl6',
            '-dBATCH',
            '-dNOPAUSE',
            '-dQUIET',
            '-dSAFER',
            '-sDEVICE=png16m',
            f'-r{dpi}',
            f'-sOutputFile={output_pattern}',
            input_path
        ]
    else:
        command = [
            'gs',
            '-dNOPAUSE',
            '-dBATCH',
            '-dQUIET',
            '-sDEVICE=png16m',
            f'-r{dpi}',
            f'-sOutputFile={output_pattern}',
            input_path
        ]
    
    logger.info(f"Rendering with command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=10
        )
        
        if result.returncode != 0:
            renderer = 'GhostPCL' if file_type == 'pcl' else 'Ghostscript'
            stderr_output = result.stderr.strip() if result.stderr else 'No error output'
            stdout_output = result.stdout.strip() if result.stdout else 'No stdout'
            raise Exception(f"{renderer} error (exit {result.returncode}): stderr={stderr_output}, stdout={stdout_output}")
        
        rendered_files = sorted([
            f for f in os.listdir(output_dir)
            if f.startswith('page_') and f.endswith('.png')
        ])
        
        if not rendered_files:
            raise Exception("No pages were rendered")
        
        return rendered_files
    
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Rendering timed out, checking for partial results")
        if e.stdout:
            logger.debug(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.debug(f"Stderr: {e.stderr}")
        
        rendered_files = sorted([
            f for f in os.listdir(output_dir)
            if f.startswith('page_') and f.endswith('.png')
        ])
        
        if rendered_files:
            logger.info(f"Found {len(rendered_files)} pages despite timeout, continuing")
            return rendered_files
        else:
            raise Exception("Rendering timed out after 10 seconds with no output")
    except FileNotFoundError:
        renderer = 'GhostPCL (gpcl6)' if file_type == 'pcl' else 'Ghostscript (gs)'
        raise Exception(f"{renderer} not found. Please install it.")
    except Exception as e:
        raise Exception(f"Rendering failed: {str(e)}")


def save_and_render(data: bytes, file_type: str, source: str = "unknown") -> Tuple[str, dict]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    job_id = f"{timestamp}"
    job_dir = os.path.join(config.output_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    file_extension = get_file_extension(file_type)
    raw_file_path = os.path.join(job_dir, f"raw.{file_extension}")
    
    with open(raw_file_path, 'wb') as f:
        f.write(data)
    
    logger.info(f"Job {job_id}: Received {len(data)} bytes, type={file_type}, source={source}")
    
    delay_seconds = len(data) / (config.processing_delay_kb_per_sec * 1024)
    time.sleep(delay_seconds)
    
    rendered_files = []
    error = None
    
    try:
        rendered_files = render_with_ghostscript(raw_file_path, job_dir, config.dpi, file_type)
        logger.info(f"Job {job_id}: Rendered {len(rendered_files)} pages")
    except Exception as e:
        error = str(e)
        logger.error(f"Job {job_id}: Rendering failed - {error}")
    
    metadata = {
        "job_id": job_id,
        "timestamp": timestamp,
        "file_type": file_type,
        "file_size": len(data),
        "page_count": len(rendered_files),
        "source": source,
        "dpi": config.dpi,
        "error": error
    }
    
    metadata_path = os.path.join(job_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return job_id, metadata


def get_job_metadata(job_id: str) -> Optional[dict]:
    job_dir = os.path.join(config.output_dir, job_id)
    metadata_path = os.path.join(job_dir, "metadata.json")
    
    if not os.path.exists(metadata_path):
        return None
    
    with open(metadata_path, 'r') as f:
        return json.load(f)


def list_jobs() -> List[dict]:
    jobs = []
    if not os.path.exists(config.output_dir):
        return jobs
    
    for job_id in sorted(os.listdir(config.output_dir), reverse=True):
        job_dir = os.path.join(config.output_dir, job_id)
        if os.path.isdir(job_dir):
            metadata = get_job_metadata(job_id)
            if metadata:
                jobs.append(metadata)
    
    return jobs


def get_job_output_files(job_id: str) -> List[str]:
    job_dir = os.path.join(config.output_dir, job_id)
    if not os.path.exists(job_dir):
        return []
    
    return sorted([
        os.path.join(job_dir, f)
        for f in os.listdir(job_dir)
        if f.startswith('page_') and f.endswith('.png')
    ])
