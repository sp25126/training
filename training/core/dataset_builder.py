"""
Dataset builder for creating high-quality training datasets
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from config.settings import DATASET_SETTINGS
from utils.file_manager import FileManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatasetBuilder:
    def __init__(self):
        self.file_manager = FileManager()
    
    async def build_final_dataset(self, qa_pairs: List[Dict], dataset_name: str = None) -> Dict:
        """
        Build final high-quality dataset from Q&A pairs
        """
        
        if not dataset_name:
            dataset_name = f"training_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🏗️ Building final dataset: {dataset_name}")
        logger.info(f"📊 Input: {len(qa_pairs)} Q&A pairs")
        
        try:
            # Step 1: Quality filtering
            high_quality_pairs = await self._quality_filter(qa_pairs)
            
            # Step 2: Deduplication
            deduplicated_pairs = await self._deduplicate_pairs(high_quality_pairs)
            
            # Step 3: Format standardization
            standardized_pairs = await self._standardize_format(deduplicated_pairs)
            
            # Step 4: Create quality tiers
            tiered_datasets = await self._create_quality_tiers(standardized_pairs)
            
            # Step 5: Save datasets
            dataset_paths = await self._save_datasets(tiered_datasets, dataset_name)
            
            # Step 6: Generate metadata
            metadata = await self._generate_dataset_metadata(
                tiered_datasets, 
                dataset_name, 
                dataset_paths,
                len(qa_pairs)
            )
            
            logger.info(f"✅ Dataset built successfully: {dataset_name}")
            logger.info(f"📈 Final quality distribution:")
            logger.info(f"   - High: {len(tiered_datasets['high'])} pairs")
            logger.info(f"   - Medium: {len(tiered_datasets['medium'])} pairs")
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Dataset building failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dataset_name": dataset_name
            }
    
    async def _quality_filter(self, qa_pairs: List[Dict]) -> List[Dict]:
        """Apply quality filtering"""
        
        logger.info("🔍 Applying quality filters...")
        
        filtered_pairs = []
        
        for qa_pair in qa_pairs:
            overall_quality = qa_pair.get("overall_quality", 0.5)
            
            if overall_quality >= 0.6:  # Minimum quality threshold
                filtered_pairs.append(qa_pair)
        
        logger.info(f"✅ Quality filter: {len(filtered_pairs)}/{len(qa_pairs)} pairs passed")
        return filtered_pairs
    
    async def _deduplicate_pairs(self, qa_pairs: List[Dict]) -> List[Dict]:
        """Remove duplicate Q&A pairs"""
        
        logger.info("🔄 Deduplicating Q&A pairs...")
        
        seen_questions = set()
        unique_pairs = []
        
        for qa_pair in qa_pairs:
            question = qa_pair.get("instruction", "").lower().strip()
            
            if question not in seen_questions:
                seen_questions.add(question)
                unique_pairs.append(qa_pair)
        
        logger.info(f"✅ Deduplication: {len(unique_pairs)} unique pairs remaining")
        return unique_pairs
    
    async def _standardize_format(self, qa_pairs: List[Dict]) -> List[Dict]:
        """Standardize format for consistent training"""
        
        logger.info("📝 Standardizing format...")
        
        standardized_pairs = []
        
        for i, qa_pair in enumerate(qa_pairs):
            standardized_pair = {
                # Core training fields
                "instruction": qa_pair.get("instruction", "").strip(),
                "input": qa_pair.get("input", "").strip(),
                "output": qa_pair.get("output", "").strip(),
                
                # Metadata
                "id": qa_pair.get("qa_pair_id", f"qa_{i}"),
                "source": qa_pair.get("resource_id", "unknown"),
                "timestamp": qa_pair.get("generation_timestamp", datetime.now().isoformat()),
                
                # Quality information
                "quality_score": qa_pair.get("overall_quality", 0.8),
                "confidence": qa_pair.get("confidence", 0.8),
                
                # Training metadata
                "generation_method": qa_pair.get("generation_method", "template_enhanced"),
                "validated": True,
                "ready_for_training": True
            }
            
            # Ensure required fields are not empty
            if (standardized_pair["instruction"] and 
                standardized_pair["output"] and
                len(standardized_pair["instruction"]) >= 10 and
                len(standardized_pair["output"]) >= 10):
                
                standardized_pairs.append(standardized_pair)
        
        logger.info(f"✅ Format standardization: {len(standardized_pairs)} pairs standardized")
        return standardized_pairs
    
    async def _create_quality_tiers(self, qa_pairs: List[Dict]) -> Dict[str, List[Dict]]:
        """Create quality-based tiers"""
        
        logger.info("📊 Creating quality tiers...")
        
        tiers = {
            "high": [],     # Score >= 0.8
            "medium": [],   # Score >= 0.6
            "all": qa_pairs
        }
        
        for qa_pair in qa_pairs:
            score = qa_pair["quality_score"]
            
            if score >= 0.8:
                tiers["high"].append(qa_pair)
                tiers["medium"].append(qa_pair)
            elif score >= 0.6:
                tiers["medium"].append(qa_pair)
        
        return tiers
    
    async def _save_datasets(self, tiered_datasets: Dict[str, List[Dict]], dataset_name: str) -> Dict[str, str]:
        """Save dataset tiers to files"""
        
        logger.info("💾 Saving datasets...")
        
        dataset_paths = {}
        
        for tier_name, qa_pairs in tiered_datasets.items():
            if not qa_pairs or tier_name == "all":
                continue
            
            # Create filename
            filename = f"{dataset_name}_{tier_name}.jsonl"
            filepath = Path(DATASET_SETTINGS.final_datasets_dir) / filename
            
            # Save dataset
            await self.file_manager.save_jsonl(qa_pairs, str(filepath))
            
            dataset_paths[tier_name] = str(filepath)
            logger.info(f"   - {tier_name}: {len(qa_pairs)} pairs → {filepath}")
        
        return dataset_paths
    
    async def _generate_dataset_metadata(self, tiered_datasets: Dict, dataset_name: str, 
                                       dataset_paths: Dict[str, str], original_count: int) -> Dict:
        """Generate comprehensive dataset metadata"""
        
        metadata = {
            "dataset_name": dataset_name,
            "creation_timestamp": datetime.now().isoformat(),
            "success": True,
            
            # Statistics
            "statistics": {
                "original_qa_pairs": original_count,
                "final_qa_pairs": len(tiered_datasets.get("all", [])),
                "high_quality_pairs": len(tiered_datasets.get("high", [])),
                "medium_quality_pairs": len(tiered_datasets.get("medium", [])),
                "quality_retention_rate": len(tiered_datasets.get("all", [])) / max(original_count, 1)
            },
            
            # Files
            "dataset_files": dataset_paths,
            
            # Processing info
            "processing_info": {
                "quality_threshold": 0.6,
                "deduplication": True,
                "format_standardization": True
            }
        }
        
        # Save metadata
        metadata_path = Path(DATASET_SETTINGS.final_datasets_dir) / f"{dataset_name}_metadata.json"
        await self.file_manager.save_json(metadata, str(metadata_path))
        
        return metadata
