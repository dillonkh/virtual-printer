import os
import logging
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from printer_engine import detect_file_type, save_and_render, list_jobs, get_job_metadata, get_job_output_files
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Virtual Printer API", version="1.0.0")


@app.get("/")
async def root():
    return {
        "service": "Virtual Printer API",
        "endpoints": {
            "POST /print": "Submit a print job",
            "GET /jobs": "List all print jobs",
            "GET /jobs/{job_id}": "Get job metadata",
            "GET /jobs/{job_id}/pages/{page_number}": "Get rendered page image"
        }
    }


@app.post("/print")
async def print_file(file: UploadFile = File(...)):
    try:
        data = await file.read()
        
        if not data:
            raise HTTPException(status_code=400, detail="Empty file")
        
        file_type = detect_file_type(data)
        
        if file_type == 'unknown':
            raise HTTPException(
                status_code=400,
                detail="Unknown file type. Supported formats: PDF, PostScript, PCL"
            )
        
        job_id, metadata = save_and_render(data, file_type, source=f"api:{file.filename}")
        
        if metadata.get('error'):
            return JSONResponse(
                status_code=500,
                content={
                    "job_id": job_id,
                    "status": "error",
                    "error": metadata['error'],
                    "metadata": metadata
                }
            )
        
        return {
            "job_id": job_id,
            "status": "success",
            "metadata": metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing print job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def get_jobs():
    try:
        jobs = list_jobs()
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        metadata = get_job_metadata(job_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Job not found")
        
        output_files = get_job_output_files(job_id)
        
        return {
            "metadata": metadata,
            "pages": [os.path.basename(f) for f in output_files]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/pages/{page_number}")
async def get_job_page(job_id: str, page_number: int):
    try:
        output_files = get_job_output_files(job_id)
        
        if not output_files:
            raise HTTPException(status_code=404, detail="Job not found or no rendered pages")
        
        if page_number < 1 or page_number > len(output_files):
            raise HTTPException(
                status_code=404,
                detail=f"Page {page_number} not found. Job has {len(output_files)} pages."
            )
        
        page_file = output_files[page_number - 1]
        
        return FileResponse(
            page_file,
            media_type="image/png",
            filename=os.path.basename(page_file)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page {page_number} for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting FastAPI server on port {config.api_port}")
    uvicorn.run(app, host="0.0.0.0", port=config.api_port)
