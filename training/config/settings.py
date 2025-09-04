"""
Configuration settings for the training project
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_ROOT = PROJECT_ROOT / "datasamples"

@dataclass
class LlamaSettings:
    """Llama model configuration"""
    question_model: str = os.getenv("LLAMA_QUESTION_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
    answer_model: str = os.getenv("LLAMA_ANSWER_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
    model_cache_dir: str = os.getenv("LLAMA_MODEL_CACHE_DIR", str(PROJECT_ROOT / "datamodels" / "llama_cache"))
    device: str = "auto"
    max_new_tokens: int = int(os.getenv("MAX_NEW_TOKENS", "512"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    load_in_4bit: bool = os.getenv("LOAD_IN_4BIT", "true").lower() == "true"

@dataclass
class ProcessingSettings:
    """Content processing configuration"""
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    overlap_size: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    min_question_length: int = 8
    max_questions_per_chunk: int = int(os.getenv("MAX_QUESTIONS_PER_CHUNK", "5"))
    quality_threshold: float = float(os.getenv("QUALITY_THRESHOLD", "0.8"))
    max_content_length: int = int(os.getenv("MAX_CONTENT_LENGTH", "50000"))

@dataclass
class DatasetSettings:
    """Dataset creation configuration"""
    raw_dir: str = str(DATA_ROOT / "raw")
    processed_dir: str = str(DATA_ROOT / "processed")
    questions_dir: str = str(DATA_ROOT / "questions")
    answers_dir: str = str(DATA_ROOT / "answers")
    final_datasets_dir: str = str(DATA_ROOT / "final_datasets")
    
    # Quality control
    min_dataset_size: int = 10
    max_dataset_size: int = 1000
    duplicate_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))

# Initialize settings
LLAMA_SETTINGS = LlamaSettings()
PROCESSING_SETTINGS = ProcessingSettings()
DATASET_SETTINGS = DatasetSettings()

# Create directories
for setting in [DATASET_SETTINGS]:
    for attr_name in dir(setting):
        if attr_name.endswith('_dir'):
            dir_path = Path(getattr(setting, attr_name))
            dir_path.mkdir(parents=True, exist_ok=True)
