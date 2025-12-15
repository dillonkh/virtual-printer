import os
from dataclasses import dataclass

@dataclass
class Config:
    socket_port: int = 9100
    api_port: int = 8000
    output_dir: str = "./outputs"
    dpi: int = 300
    processing_delay_kb_per_sec: int = 50
    
    def __post_init__(self):
        os.makedirs(self.output_dir, exist_ok=True)

config = Config()
