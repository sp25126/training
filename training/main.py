"""
Main orchestrator for the enhanced training project
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Union, Dict
import argparse

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from core.resource_processor import ResourceProcessor
from core.llama_question_generator import LlamaQuestionGenerator
from core.dataset_builder import DatasetBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UniversalQAGenerator:
    def __init__(self):
        self.resource_processor = ResourceProcessor()
        self.question_generator = LlamaQuestionGenerator()
        self.dataset_builder = DatasetBuilder()
    
    async def process_resource_to_dataset(self, resource: Union[str, Dict], 
                                        resource_type: str = "auto",
                                        dataset_name: str = None) -> Dict:
        """
        Complete pipeline: resource → questions → answers → dataset
        """
        
        logger.info("🚀 Starting complete resource-to-dataset pipeline")
        logger.info(f"📥 Resource: {str(resource)[:100]}...")
        
        try:
            # Step 1: Process resource
            logger.info("📊 Step 1: Processing resource...")
            processed_resource = await self.resource_processor.process_resource(resource, resource_type)
            
            if not processed_resource["content"]:
                return {
                    "success": False,
                    "error": "Failed to extract content from resource",
                    "stage": "resource_processing"
                }
            
            # Step 2: Chunk content
            logger.info("📄 Step 2: Chunking content...")
            chunks = await self.resource_processor.chunk_content(processed_resource)
            
            # Step 3: Generate questions and answers
            logger.info(f"🧠 Step 3: Generating Q&A for {len(chunks)} chunks...")
            all_qa_pairs = []
            
            for chunk in chunks:
                qa_pairs = await self.question_generator.generate_questions_and_answers(chunk)
                all_qa_pairs.extend(qa_pairs)
            
            if not all_qa_pairs:
                return {
                    "success": False,
                    "error": "No Q&A pairs generated",
                    "stage": "qa_generation"
                }
            
            # Step 4: Build final dataset
            logger.info(f"🏗️ Step 4: Building dataset from {len(all_qa_pairs)} Q&A pairs...")
            dataset_metadata = await self.dataset_builder.build_final_dataset(all_qa_pairs, dataset_name)
            
            if not dataset_metadata.get("success", False):
                return {
                    "success": False,
                    "error": dataset_metadata.get("error", "Dataset building failed"),
                    "stage": "dataset_building"
                }
            
            # Complete success
            result = {
                "success": True,
                "resource_metadata": processed_resource["metadata"],
                "processing_stats": {
                    "chunks_processed": len(chunks),
                    "qa_pairs_generated": len(all_qa_pairs),
                    "final_dataset_size": dataset_metadata["statistics"]["final_qa_pairs"]
                },
                "dataset_metadata": dataset_metadata,
                "dataset_files": dataset_metadata["dataset_files"]
            }
            
            logger.info("🎉 Pipeline completed successfully!")
            logger.info(f"📈 Results: {len(all_qa_pairs)} → {dataset_metadata['statistics']['final_qa_pairs']} Q&A pairs")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "stage": "unknown"
            }

# CLI Interface
async def main():
    parser = argparse.ArgumentParser(description="Training QA Generator")
    parser.add_argument("resource", help="Resource to process (URL, file path, or text)")
    parser.add_argument("--type", choices=["web", "telegram", "file", "text", "auto"], 
                       default="auto", help="Resource type")
    parser.add_argument("--dataset-name", help="Custom dataset name")
    parser.add_argument("--batch", nargs="+", help="Process multiple resources")
    
    args = parser.parse_args()
    
    generator = UniversalQAGenerator()
    
    try:
        if args.batch:
            # Simple batch processing (process each individually)
            results = []
            for i, resource in enumerate(args.batch):
                logger.info(f"Processing resource {i+1}/{len(args.batch)}: {str(resource)[:50]}...")
                result = await generator.process_resource_to_dataset(
                    resource, 
                    "auto", 
                    f"{args.dataset_name or 'batch'}_{i}" if args.dataset_name else None
                )
                results.append(result)
            
            # Summary
            successful = sum(1 for r in results if r.get("success"))
            print(f"\n🎉 Batch processing complete: {successful}/{len(args.batch)} successful")
            
        else:
            # Single resource processing
            result = await generator.process_resource_to_dataset(
                args.resource, 
                args.type, 
                args.dataset_name
            )
            
            # Print results
            if result["success"]:
                print("\n🎉 SUCCESS!")
                if "dataset_files" in result:
                    print("📁 Dataset files created:")
                    for tier, filepath in result["dataset_files"].items():
                        print(f"   - {tier}: {filepath}")
                
                if "processing_stats" in result:
                    stats = result["processing_stats"]
                    print(f"📊 Processing stats:")
                    print(f"   - Chunks: {stats['chunks_processed']}")
                    print(f"   - Generated Q&A: {stats['qa_pairs_generated']}")
                    print(f"   - Final dataset: {stats['final_dataset_size']}")
            
            else:
                print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
                print(f"Stage: {result.get('stage', 'Unknown')}")
    
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
