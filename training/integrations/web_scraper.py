"""
Enhanced web scraper with YouTube transcript extraction and improved content processing
"""

import aiohttp
import asyncio
import logging
import re
import json
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse, parse_qs
import tempfile
from pathlib import Path

# YouTube transcript extraction
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_TRANSCRIPT_SUPPORT = True
except ImportError:
    YOUTUBE_TRANSCRIPT_SUPPORT = False
    logging.warning("YouTube transcript API not available. Install with: pip install youtube-transcript-api")

# Alternative YouTube extraction
try:
    import yt_dlp
    YT_DLP_SUPPORT = True
except ImportError:
    YT_DLP_SUPPORT = False
    logging.warning("yt-dlp not available. Install with: pip install yt-dlp")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScraper:
    """Enhanced web scraper with YouTube and video platform support"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def scrape_url(self, url: str) -> Dict:
        """
        Enhanced URL scraper with platform-specific handling
        """
        logger.info(f"Scraping content from: {url}")
        
        try:
            # Detect platform type
            platform = self._detect_platform(url)
            
            if platform == "youtube":
                return await self._scrape_youtube_content(url)
            elif platform == "video_platform":
                return await self._scrape_video_platform(url)
            else:
                return await self._scrape_regular_webpage(url)
                
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {
                "content": f"Failed to extract content from {url}. Error: {str(e)}",
                "metadata": {
                    "source_type": "web",
                    "url": url,
                    "title": "Scraping failed",
                    "error": str(e),
                    "platform": "unknown"
                }
            }
    
    def _detect_platform(self, url: str) -> str:
        """Detect the platform type from URL"""
        url_lower = url.lower()
        
        # YouTube detection
        if any(domain in url_lower for domain in ['youtube.com', 'youtu.be', 'm.youtube.com']):
            return "youtube"
        
        # Other video platforms
        elif any(platform in url_lower for platform in ['vimeo.com', 'dailymotion.com', 'twitch.tv']):
            return "video_platform"
        
        # Regular webpage
        else:
            return "webpage"
    
    async def _scrape_youtube_content(self, url: str) -> Dict:
        """Extract content from YouTube videos using multiple methods"""
        
        try:
            # Extract video ID
            video_id = self._extract_youtube_video_id(url)
            if not video_id:
                raise Exception("Could not extract YouTube video ID")
            
            logger.info(f"Processing YouTube video: {video_id}")
            
            # Method 1: Try transcript API first
            transcript_content = await self._get_youtube_transcript(video_id)
            
            # Method 2: Fallback to yt-dlp for metadata and description
            video_info = await self._get_youtube_info_ytdlp(url)
            
            # Method 3: Fallback to web scraping
            if not transcript_content and not video_info.get('description'):
                return await self._scrape_youtube_webpage(url)
            
            # Combine available content
            content_parts = []
            
            # Add video title and description
            if video_info:
                if video_info.get('title'):
                    content_parts.append(f"Video Title: {video_info['title']}")
                
                if video_info.get('description'):
                    # Clean description
                    description = self._clean_youtube_description(video_info['description'])
                    if description:
                        content_parts.append(f"Video Description:\n{description}")
                
                if video_info.get('uploader'):
                    content_parts.append(f"Channel: {video_info['uploader']}")
            
            # Add transcript
            if transcript_content:
                content_parts.append(f"Video Transcript:\n{transcript_content}")
            
            # Combine all content
            full_content = "\n\n".join(content_parts)
            
            if not full_content.strip():
                full_content = "No readable content could be extracted from this YouTube video."
            
            return {
                "content": full_content,
                "metadata": {
                    "source_type": "youtube_video",
                    "url": url,
                    "video_id": video_id,
                    "title": video_info.get('title', 'Unknown Title') if video_info else 'Unknown Title',
                    "channel": video_info.get('uploader', 'Unknown Channel') if video_info else 'Unknown Channel',
                    "duration": video_info.get('duration', 0) if video_info else 0,
                    "view_count": video_info.get('view_count', 0) if video_info else 0,
                    "upload_date": video_info.get('upload_date', '') if video_info else '',
                    "platform": "youtube",
                    "has_transcript": bool(transcript_content),
                    "content_length": len(full_content)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to extract YouTube content: {e}")
            # Fallback to regular web scraping
            return await self._scrape_youtube_webpage(url)
    
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        
        # Regular YouTube URL
        if 'watch?v=' in url:
            return parse_qs(urlparse(url).query).get('v', [None])[0]
        
        # Short YouTube URL
        elif 'youtu.be/' in url:
            return urlparse(url).path[1:]
        
        # YouTube embed URL
        elif 'youtube.com/embed/' in url:
            return urlparse(url).path.split('/')[-1]
        
        # YouTube mobile URL
        elif 'm.youtube.com' in url:
            return parse_qs(urlparse(url).query).get('v', [None])[0]
        
        return None
    
    async def _get_youtube_transcript(self, video_id: str) -> Optional[str]:
        """Get YouTube video transcript using youtube-transcript-api"""
        
        if not YOUTUBE_TRANSCRIPT_SUPPORT:
            return None
        
        try:
            logger.info(f"Fetching transcript for video: {video_id}")
            
            # Get transcript in preferred languages
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to find English transcript first
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except:
                # If no English, try auto-generated
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    # Get any available transcript
                    for transcript_item in transcript_list:
                        transcript = transcript_item
                        break
            
            if transcript:
                # Fetch the actual transcript data
                transcript_data = transcript.fetch()
                
                # Format transcript
                formatter = TextFormatter()
                transcript_text = formatter.format_transcript(transcript_data)
                
                # Clean up transcript
                cleaned_transcript = self._clean_transcript(transcript_text)
                
                logger.info(f"Successfully extracted transcript: {len(cleaned_transcript)} characters")
                return cleaned_transcript
            
        except Exception as e:
            logger.warning(f"Could not fetch transcript for {video_id}: {e}")
        
        return None
    
    async def _get_youtube_info_ytdlp(self, url: str) -> Optional[Dict]:
        """Get YouTube video info using yt-dlp"""
        
        if not YT_DLP_SUPPORT:
            return None
        
        try:
            logger.info("Fetching video info with yt-dlp...")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    return {
                        'title': info.get('title', ''),
                        'description': info.get('description', ''),
                        'uploader': info.get('uploader', ''),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'upload_date': info.get('upload_date', ''),
                        'tags': info.get('tags', [])
                    }
                    
        except Exception as e:
            logger.warning(f"Could not fetch video info with yt-dlp: {e}")
        
        return None
    
    def _clean_transcript(self, transcript: str) -> str:
        """Clean and format transcript text"""
        
        if not transcript:
            return ""
        
        # Remove extra whitespace
        transcript = re.sub(r'\s+', ' ', transcript)
        
        # Remove music notes and sound effects
        transcript = re.sub(r'\[.*?\]', '', transcript)
        transcript = re.sub(r'\(.*?\)', '', transcript)
        
        # Remove repetitive filler words
        filler_words = ['um', 'uh', 'like', 'you know', 'so', 'actually']
        for word in filler_words:
            transcript = re.sub(rf'\b{word}\b', '', transcript, flags=re.IGNORECASE)

        # Clean up extra spaces
        transcript = re.sub(r'\s+', ' ', transcript)
        
        return transcript.strip()
    
    def _clean_youtube_description(self, description: str) -> str:
        """Clean YouTube video description"""
        
        if not description:
            return ""
        
        # Remove common promotional elements
        lines = description.split('\n')
        cleaned_lines = []
        
        skip_patterns = [
            r'subscribe.*channel', r'like.*video', r'follow.*on', 
            r'social.*media', r'instagram', r'twitter', r'facebook',
            r'patreon', r'merchandise', r'merch', r'sponsor'
        ]
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip promotional lines
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue
            
            # Skip lines that are mostly URLs
            if len(re.findall(r'http[s]?://\S+', line)) > len(line.split()) // 2:
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    async def _scrape_youtube_webpage(self, url: str) -> Dict:
        """Fallback method to scrape YouTube webpage"""
        
        logger.info("Using fallback web scraping for YouTube")
        
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        
        try:
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract title
                title = "Unknown Title"
                title_elem = soup.find('title')
                if title_elem:
                    title = title_elem.get_text().replace(' - YouTube', '')
                
                # Try to extract video description from page data
                content = f"Video Title: {title}\n\n"
                
                # Look for JSON data with video info
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'ytInitialPlayerResponse' in script.string:
                        try:
                            # Extract description from player response
                            script_content = script.string
                            if 'shortDescription' in script_content:
                                # This is a simplified extraction - in practice, you'd parse the JSON
                                content += "Note: This is a YouTube video. For full content, transcript extraction is recommended."
                                break
                        except:
                            continue
                
                return {
                    "content": content,
                    "metadata": {
                        "source_type": "youtube_webpage",
                        "url": url,
                        "title": title,
                        "platform": "youtube",
                        "extraction_method": "webpage_fallback"
                    }
                }
                
        finally:
            if self.session:
                await self.session.close()
                self.session = None
    
    async def _scrape_video_platform(self, url: str) -> Dict:
        """Handle other video platforms"""
        
        # For now, treat as regular webpage but with video-specific handling
        result = await self._scrape_regular_webpage(url)
        result["metadata"]["platform"] = "video_platform"
        
        return result
    
    async def _scrape_regular_webpage(self, url: str) -> Dict:
        """Enhanced regular webpage scraping with better content extraction"""
        
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        
        try:
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                html_content = await response.text()
                
                # Parse HTML content
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract main content
                content = self._extract_main_content(soup)
                
                # Filter out generic/irrelevant content
                content = self._filter_generic_content(content, url)
                
                # Get metadata
                metadata = self._extract_metadata(soup, url)
                
                return {
                    "content": content,
                    "metadata": metadata
                }
                
        finally:
            if self.session:
                await self.session.close()
                self.session = None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Enhanced main content extraction"""
        
        content_parts = []
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
            element.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Primary content selectors (ordered by priority)
        content_selectors = [
            'article', 'main', '[role="main"]',
            '.content', '.post-content', '.entry-content', '.article-content',
            '.post', '.article', '.blog-post',
            '#content', '#main-content', '#primary-content',
            '.container .content', '.wrapper .content'
        ]
        
        # Try each selector
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text = self._clean_text(element.get_text())
                    if len(text) > 200:  # Minimum meaningful content length
                        content_parts.append(text)
                        break
                if content_parts:
                    break
        
        # Fallback to paragraph extraction
        if not content_parts:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = self._clean_text(p.get_text())
                if len(text) > 50:
                    content_parts.append(text)
        
        # Final fallback to headings + paragraphs
        if not content_parts:
            for tag in ['h1', 'h2', 'h3', 'p', 'div']:
                elements = soup.find_all(tag)
                for element in elements:
                    text = self._clean_text(element.get_text())
                    if len(text) > 30:
                        content_parts.append(text)
                        
                if len(content_parts) > 10:  # Enough content found
                    break
        
        # Join and limit content
        full_content = '\n\n'.join(content_parts)
        
        # Limit total length but preserve completeness
        if len(full_content) > 20000:
            # Try to cut at sentence boundary
            sentences = full_content.split('.')
            truncated = []
            current_length = 0
            
            for sentence in sentences:
                if current_length + len(sentence) > 15000:
                    break
                truncated.append(sentence)
                current_length += len(sentence)
            
            full_content = '.'.join(truncated) + '.'
        
        return full_content or "No meaningful content could be extracted from this webpage."
    
    def _filter_generic_content(self, content: str, url: str) -> str:
        """Filter out generic webpage elements"""
        
        # Generic patterns to remove
        generic_patterns = [
            # YouTube specific
            r'About\s+Press\s+Copyright\s+Contact\s+us',
            r'Terms\s+Privacy\s+Policy\s+Safety',
            r'How\s+YouTube\s+works\s+Test\s+new\s+features',
            r'©?\s*20\d{2}\s+Google\s+LLC',
            r'Creators?\s+Advertise\s+Developers?',
            
            # Common website elements
            r'Subscribe\s+to\s+our\s+newsletter',
            r'Follow\s+us\s+on\s+social\s+media',
            r'All\s+rights\s+reserved',
            r'Cookie\s+policy',
            r'Privacy\s+policy',
            r'Terms\s+of\s+service',
            
            # Navigation elements
            r'Home\s+About\s+Contact',
            r'Menu\s+Search\s+Login',
            
            # Common spam
            r'Click\s+here\s+to\s+',
            r'Sign\s+up\s+now',
            r'Free\s+trial',
        ]
        
        # Apply filters
        for pattern in generic_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Remove very short paragraphs (likely navigation/footer elements)
        lines = content.split('\n')
        meaningful_lines = []
        
        for line in lines:
            line = line.strip()
            # Keep lines that are substantial or part of meaningful content
            if len(line) > 20 or (line and not self._is_likely_navigation(line)):
                meaningful_lines.append(line)
        
        return '\n'.join(meaningful_lines)
    
    def _is_likely_navigation(self, text: str) -> bool:
        """Check if text is likely navigation/menu element"""
        
        nav_indicators = [
            'home', 'about', 'contact', 'menu', 'search', 'login', 'logout',
            'sign up', 'sign in', 'register', 'cart', 'checkout', 'account'
        ]
        
        text_lower = text.lower()
        word_count = len(text.split())
        
        # Short text with nav keywords is likely navigation
        if word_count <= 3 and any(indicator in text_lower for indicator in nav_indicators):
            return True
        
        # Very short text is likely navigation
        if word_count <= 1:
            return True
        
        return False
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Enhanced metadata extraction"""
        
        # Get title
        title = "Unknown Title"
        title_elem = soup.find('title')
        if title_elem:
            title = self._clean_text(title_elem.get_text())
        
        # Get description
        description = ""
        desc_elem = soup.find('meta', attrs={'name': 'description'}) or \
                   soup.find('meta', attrs={'property': 'og:description'})
        if desc_elem:
            description = desc_elem.get('content', '')
        
        # Get keywords
        keywords = []
        keywords_elem = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_elem:
            keywords = [k.strip() for k in keywords_elem.get('content', '').split(',')]
        
        # Get author
        author = ""
        author_elem = soup.find('meta', attrs={'name': 'author'}) or \
                     soup.find('meta', attrs={'property': 'article:author'})
        if author_elem:
            author = author_elem.get('content', '')
        
        return {
            "source_type": "web",
            "url": url,
            "domain": urlparse(url).netloc,
            "title": title,
            "description": description,
            "author": author,
            "keywords": keywords,
            "platform": "webpage"
        }
    
    def _clean_text(self, text: str) -> str:
        """Enhanced text cleaning"""
        
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\']+', ' ', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
