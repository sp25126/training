"""
Enhanced Telegram bot integration with audio, video, and URL processing support
"""

import asyncio
import aiohttp
import os
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from main import UniversalQAGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramFileBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.qa_generator = UniversalQAGenerator()
        self.downloads_dir = Path("downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """🤖 **Enhanced Training QA Generator Bot**

🎬 **NEW: Audio & Video Support!**
🔗 **Enhanced URL Processing!**

**Send me any of these:**

📄 **Documents:** .pdf, .docx, .txt, .md, .json, .csv
🎬 **Videos:** .mp4, .avi, .mov, .mkv, .webm
🎵 **Audio:** .mp3, .wav, .m4a, .flac, .aac
🔗 **URLs:** Websites, direct media links
💬 **Text:** Plain messages (50+ characters)

**Features:**
✅ Speech-to-text from videos/audio
✅ Web content extraction
✅ High-quality Q&A generation with Ollama 3.2
✅ Professional training datasets

**Commands:**
/start - This message
/help - Detailed help
/formats - Supported file formats

Just send your content! 📤"""
        
        await update.message.reply_text(welcome_message)
    
    async def formats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show supported formats"""
        formats_message = """📁 **Supported File Formats**

**📄 Documents:**
• PDF (.pdf) - Text extraction
• Word (.docx, .doc) - Text extraction  
• Text (.txt, .md, .csv) - Direct processing
• Data (.json, .jsonl) - Structured data

**🎬 Videos:** 
• MP4, AVI, MOV, MKV, WEBM, FLV
• Extracts speech using advanced AI
• Supports most common video formats

**🎵 Audio:**
• MP3, WAV, M4A, FLAC, AAC, OGG
• High-quality speech recognition
• Works with recordings, podcasts, lectures

**🔗 URLs:**
• Web pages - Content extraction
• Direct media links - Downloads & processes
• YouTube links - Audio extraction (coming soon)

**💬 Text:** 
• Plain messages (minimum 50 characters)
• Any language, any topic

**File Limits:**
• Max size: 50MB per file
• Processing time: 1-5 minutes depending on length
• Unlimited Q&A generation based on content richness

Ready to create professional training datasets! 🚀"""
        
        await update.message.reply_text(formats_message)
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced document handler with audio/video support"""
        
        if not update.message.document:
            return
        
        try:
            # Get file info
            document = update.message.document
            file_id = document.file_id
            file_name = document.file_name or f"document_{file_id[:8]}"
            file_size = document.file_size or 0
            
            # Determine media type
            file_ext = Path(file_name).suffix.lower()
            media_type = self._classify_media_type(file_ext)
            
            # Check file size (increased limit for media files)
            max_size = 100 * 1024 * 1024 if media_type in ['video', 'audio'] else 50 * 1024 * 1024
            if file_size > max_size:
                size_limit = "100MB" if media_type in ['video', 'audio'] else "50MB"
                await update.message.reply_text(
                    f"❌ File too large ({file_size/1024/1024:.1f}MB). Maximum: {size_limit}"
                )
                return
            
            # Send processing message with media type info
            media_emoji = {"video": "🎬", "audio": "🎵", "document": "📄", "data": "📋"}.get(media_type, "📁")
            
            processing_msg = await update.message.reply_text(
                f"{media_emoji} **Processing {media_type}: {file_name}**\n"
                f"📊 Size: {file_size/1024:.1f} KB\n\n"
                f"⏳ {'Extracting speech and generating Q&A...' if media_type in ['video', 'audio'] else 'Generating Q&A...'}"
            )
            
            # Download file
            new_file = await context.bot.get_file(file_id)
            file_path = self.downloads_dir / file_name
            
            # Download file content
            async with aiohttp.ClientSession() as session:
                async with session.get(new_file.file_path) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        
                        # Save file locally
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        
                        logger.info(f"✅ Downloaded: {file_path}")
                    else:
                        raise Exception(f"Failed to download: HTTP {resp.status}")
            
            # Update processing message for media files
            if media_type in ['video', 'audio']:
                await processing_msg.edit_text(
                    f"{media_emoji} **Processing {media_type}: {file_name}**\n"
                    f"📊 Size: {file_size/1024:.1f} KB\n\n"
                    f"🎤 Extracting speech content...\n"
                    f"⏳ This may take 2-5 minutes..."
                )
            
            # Process through pipeline
            result = await self.qa_generator.process_resource_to_dataset(
                resource=str(file_path),
                resource_type="file",
                dataset_name=f"telegram_{media_type}_{file_id[:8]}"
            )
            
            # Send results
            await self._send_processing_results(update, result, processing_msg, file_name, media_type)
            
            # Clean up downloaded file
            if file_path.exists():
                file_path.unlink()
                
        except Exception as e:
            logger.error(f"❌ Error processing document: {e}")
            await update.message.reply_text(
                f"❌ **Error processing {file_name}:**\n{str(e)[:200]}..."
            )
    
    def _classify_media_type(self, file_extension: str) -> str:
        """Classify file by media type"""
        if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm', '.m4v']:
            return "video"
        elif file_extension in ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma']:
            return "audio"
        elif file_extension in ['.pdf', '.docx', '.doc', '.txt', '.md']:
            return "document"
        elif file_extension in ['.json', '.jsonl', '.csv']:
            return "data"
        else:
            return "unknown"
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle audio messages (voice notes, audio files)"""
        try:
            audio = update.message.audio or update.message.voice
            if not audio:
                return
            
            file_id = audio.file_id
            duration = getattr(audio, 'duration', 0)
            
            # Check duration (max 10 minutes for voice notes)
            if duration > 600:  # 10 minutes
                await update.message.reply_text(
                    "❌ Audio too long (max 10 minutes for voice messages)"
                )
                return
            
            processing_msg = await update.message.reply_text(
                f"🎵 **Processing audio message**\n"
                f"⏱️ Duration: {duration}s\n\n"
                f"🎤 Extracting speech and generating Q&A..."
            )
            
            # Download audio
            new_file = await context.bot.get_file(file_id)
            file_ext = '.ogg' if update.message.voice else '.mp3'
            file_path = self.downloads_dir / f"audio_{file_id[:8]}{file_ext}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(new_file.file_path) as resp:
                    content = await resp.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
            
            # Process audio
            result = await self.qa_generator.process_resource_to_dataset(
                resource=str(file_path),
                resource_type="file", 
                dataset_name=f"telegram_audio_{file_id[:8]}"
            )
            
            await self._send_processing_results(update, result, processing_msg, "audio message", "audio")
            
            # Clean up
            file_path.unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            await update.message.reply_text(f"❌ Error processing audio: {str(e)[:200]}...")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced text message handler with URL detection"""
        
        text = update.message.text
        
        # Skip if it's a command
        if text.startswith('/'):
            return
        
        # Enhanced URL detection
        if any(text.startswith(prefix) for prefix in ['http://', 'https://', 'www.']):
            await self._process_url(update, text.strip())
            return
        
        # Process as plain text
        if len(text) < 50:
            await update.message.reply_text(
                "📝 **Text too short!**\n\n"
                "Please send at least 50 characters for meaningful Q&A generation.\n\n"
                "💡 **Tip:** Send longer content, documents, media files, or URLs for better results!"
            )
            return
        
        try:
            processing_msg = await update.message.reply_text(
                f"📝 **Processing text message...**\n"
                f"📊 Length: {len(text)} characters\n\n"
                "⏳ Generating Q&A pairs..."
            )
            
            # Process through pipeline
            result = await self.qa_generator.process_resource_to_dataset(
                resource=text,
                resource_type="text",
                dataset_name=f"telegram_text_{update.message.message_id}"
            )
            
            await self._send_processing_results(update, result, processing_msg, "text message", "text")
            
        except Exception as e:
            logger.error(f"❌ Error processing text: {e}")
            await update.message.reply_text(
                f"❌ **Error processing text:**\n{str(e)[:200]}..."
            )
    
    async def _process_url(self, update: Update, url: str):
        """Enhanced URL processor with media detection"""
        
        try:
            # Detect media URLs
            media_type = "webpage"
            if any(ext in url.lower() for ext in ['.mp4', '.avi', '.mov', '.webm']):
                media_type = "video"
            elif any(ext in url.lower() for ext in ['.mp3', '.wav', '.m4a']):
                media_type = "audio"
            
            media_emoji = {"video": "🎬", "audio": "🎵", "webpage": "🌐"}[media_type]
            
            processing_msg = await update.message.reply_text(
                f"{media_emoji} **Processing {media_type} URL...**\n"
                f"🔗 {url[:50]}{'...' if len(url) > 50 else ''}\n\n"
                f"⏳ {'Downloading and extracting content...' if media_type != 'webpage' else 'Scraping content and generating Q&A...'}"
            )
            
            # Process through pipeline
            result = await self.qa_generator.process_resource_to_dataset(
                resource=url,
                resource_type="web",
                dataset_name=f"telegram_url_{update.message.message_id}"
            )
            
            await self._send_processing_results(update, result, processing_msg, f"{media_type} URL", media_type)
            
        except Exception as e:
            logger.error(f"❌ Error processing URL: {e}")
            await update.message.reply_text(
                f"❌ **Error processing URL:**\n{str(e)[:200]}..."
            )
    
    async def _send_processing_results(self, update: Update, result: dict, 
                                     processing_msg, source_name: str, media_type: str = "document"):
        """Enhanced results sender with media type awareness"""
        
        media_emoji = {"video": "🎬", "audio": "🎵", "document": "📄", "webpage": "🌐", "text": "📝"}.get(media_type, "📁")
        
        if result.get("success"):
            stats = result.get("processing_stats", {})
            
            # Create success message
            success_msg = f"""{media_emoji} **Processing Complete!**

📁 **Source:** {source_name}
📊 **Results:**
• Content processed: ✅
• Chunks processed: {stats.get('chunks_processed', 0)}
• Q&A pairs generated: {stats.get('qa_pairs_generated', 0)}  
• Final dataset size: {stats.get('final_dataset_size', 0)}

🎯 **Quality:** {result.get('dataset_metadata', {}).get('statistics', {}).get('quality_retention_rate', 0)*100:.1f}%
💾 **Status:** Ready for AI training!

{f'🎤 Speech content successfully extracted!' if media_type in ['video', 'audio'] else ''}"""
            
            # Edit the processing message
            try:
                await processing_msg.edit_text(success_msg)
            except Exception as e:
                logger.error(f"Failed to edit message: {e}")
                await update.message.reply_text(success_msg)
            
        else:
            error_msg = f"""{media_emoji} **Processing Failed**

📁 **Source:** {source_name}
🚨 **Error:** {result.get('error', 'Unknown error')[:100]}...
🎯 **Stage:** {result.get('stage', 'Unknown')}

Please try again with different content or check the file format."""
            
            try:
                await processing_msg.edit_text(error_msg)
            except Exception as e:
                logger.error(f"Failed to edit error message: {e}")
                await update.message.reply_text(error_msg)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced help command"""
        help_text = """🤖 **Enhanced Training QA Generator Bot - Help**

**🎯 What I Do:**
Transform any content into high-quality Q&A training datasets using advanced AI (Ollama 3.2)

**📁 Supported Content:**

**📄 Documents:**
• PDF, Word (.docx, .doc), Text (.txt, .md, .csv)
• JSON/JSONL data files

**🎬 Videos:** 
• MP4, AVI, MOV, MKV, WEBM, FLV
• Extracts speech automatically

**🎵 Audio:**
• MP3, WAV, M4A, FLAC, AAC, OGG
• Voice messages and recordings

**🔗 URLs:**
• Web pages with automatic content extraction
• Direct media file links

**💬 Text:** Any text content (50+ characters)

**🔧 Commands:**
• /start - Welcome message  
• /help - This help message
• /formats - Detailed format information

**⚙️ Features:**
✅ AI-powered speech-to-text
✅ Intelligent content extraction  
✅ Unlimited Q&A generation
✅ Professional quality control
✅ Multiple output formats

**📏 Limits:**
• Documents: 50MB max
• Audio/Video: 100MB max  
• Processing: 1-5 minutes
• Voice messages: 10 minutes max

**🚀 Usage:**
Just send your file, URL, or text - I'll handle the rest!

Need more help? Send /start for quick overview."""
        
        await update.message.reply_text(help_text)
    
    def run(self):
        """Start the enhanced Telegram bot"""
        
        # Create application
        app = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("formats", self.formats_command))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, self.handle_audio))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        # Run bot
        logger.info("🤖 Starting Enhanced Telegram bot with audio/video support...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
