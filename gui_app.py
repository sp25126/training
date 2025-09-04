"""
Training QA Generator - Desktop Application
Standalone EXE version with file upload and output selection
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import asyncio
import threading
import os
import sys
from pathlib import Path
import logging

# Add project modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import UniversalQAGenerator
from config.settings import LLAMA_SETTINGS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainingQAGeneratorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Training QA Generator v2.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Initialize QA generator
        self.qa_generator = None
        self.output_directory = os.path.expanduser("~/Desktop/QA_Datasets")
        
        # Create UI
        self.setup_ui()
        self.startup_check()
    
    def setup_ui(self):
        """Create the main user interface"""
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🤖 Training QA Generator", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Subtitle
        subtitle_label = ttk.Label(main_frame, 
                                  text="Generate high-quality Q&A datasets from any content using Ollama 3.2",
                                  font=('Arial', 10))
        subtitle_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="📁 Select Content", padding="10")
        file_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # File path display
        self.file_path_var = tk.StringVar(value="No file selected")
        ttk.Label(file_frame, text="File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.file_path_label = ttk.Label(file_frame, textvariable=self.file_path_var, 
                                        relief="sunken", padding="5")
        self.file_path_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Browse button
        ttk.Button(file_frame, text="Browse Files", 
                  command=self.browse_file).grid(row=0, column=2, padx=(0, 10))
        
        # URL input
        ttk.Label(file_frame, text="Or URL:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(file_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(10, 0))
        
        # Output directory section
        output_frame = ttk.LabelFrame(main_frame, text="💾 Output Settings", padding="10")
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        # Output directory display
        self.output_path_var = tk.StringVar(value=self.output_directory)
        ttk.Label(output_frame, text="Save to:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.output_path_label = ttk.Label(output_frame, textvariable=self.output_path_var,
                                          relief="sunken", padding="5")
        self.output_path_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Browse output button
        ttk.Button(output_frame, text="Choose Folder", 
                  command=self.browse_output_folder).grid(row=0, column=2)
        
        # Dataset name
        ttk.Label(output_frame, text="Dataset Name:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.dataset_name_var = tk.StringVar(value="my_dataset")
        ttk.Entry(output_frame, textvariable=self.dataset_name_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # Process button
        self.process_button = ttk.Button(main_frame, text="🚀 Generate Q&A Dataset", 
                                        command=self.start_processing, style="Accent.TButton")
        self.process_button.grid(row=4, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, mode='indeterminate')
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status text
        self.status_var = tk.StringVar(value="Ready to generate datasets!")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="blue")
        self.status_label.grid(row=6, column=0, columnspan=3)
        
        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="📋 Processing Log", padding="10")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def startup_check(self):
        """Check system requirements and initialize"""
        self.log_message("🔧 Initializing Training QA Generator...")
        
        # Create output directory if it doesn't exist
        Path(self.output_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize QA generator in background
        threading.Thread(target=self.initialize_qa_generator, daemon=True).start()
    
    def initialize_qa_generator(self):
        """Initialize the QA generator system"""
        try:
            self.log_message("🧠 Loading Ollama 3.2 model...")
            self.qa_generator = UniversalQAGenerator()
            self.log_message("✅ System ready! You can now process content.")
            self.update_status("System initialized successfully!", "green")
        except Exception as e:
            self.log_message(f"❌ Initialization failed: {str(e)}")
            self.update_status(f"Initialization error: {str(e)}", "red")
    
    def browse_file(self):
        """Open file browser for content selection"""
        filetypes = [
            ("All Supported", "*.txt;*.pdf;*.docx;*.json;*.jsonl;*.csv;*.md;*.mp4;*.avi;*.mov;*.mp3;*.wav;*.m4a"),
            ("Documents", "*.txt;*.pdf;*.docx;*.md"),
            ("Data Files", "*.json;*.jsonl;*.csv"),
            ("Media Files", "*.mp4;*.avi;*.mov;*.mp3;*.wav;*.m4a"),
            ("All Files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Content File",
            filetypes=filetypes
        )
        
        if filename:
            self.file_path_var.set(filename)
            # Clear URL if file is selected
            self.url_var.set("")
            self.log_message(f"📁 Selected file: {Path(filename).name}")
    
    def browse_output_folder(self):
        """Open folder browser for output directory selection"""
        folder = filedialog.askdirectory(
            title="Choose Output Directory",
            initialdir=self.output_directory
        )
        
        if folder:
            self.output_directory = folder
            self.output_path_var.set(folder)
            self.log_message(f"💾 Output directory: {folder}")
    
    def start_processing(self):
        """Start the Q&A generation process"""
        if not self.qa_generator:
            messagebox.showerror("Error", "System not initialized yet. Please wait...")
            return
        
        # Get input source
        file_path = self.file_path_var.get()
        url = self.url_var.get().strip()
        
        if file_path == "No file selected" and not url:
            messagebox.showerror("Error", "Please select a file or enter a URL")
            return
        
        # Get dataset name
        dataset_name = self.dataset_name_var.get().strip()
        if not dataset_name:
            dataset_name = "generated_dataset"
        
        # Disable process button
        self.process_button.config(state='disabled')
        self.progress_bar.start()
        self.update_status("Processing content...", "blue")
        
        # Start processing in background thread
        processing_thread = threading.Thread(
            target=self.process_content,
            args=(file_path if file_path != "No file selected" else url, dataset_name),
            daemon=True
        )
        processing_thread.start()
    
    def process_content(self, resource, dataset_name):
        """Process content and generate Q&A dataset"""
        try:
            self.log_message("🚀 Starting Q&A generation...")
            
            # Determine resource type
            if resource.startswith(('http://', 'https://')):
                resource_type = "web"
                self.log_message(f"🌐 Processing URL: {resource}")
            else:
                resource_type = "file"
                self.log_message(f"📄 Processing file: {Path(resource).name}")
            
            # Create event loop for async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Process resource
            result = loop.run_until_complete(
                self.qa_generator.process_resource_to_dataset(
                    resource=resource,
                    resource_type=resource_type,
                    dataset_name=dataset_name
                )
            )
            
            loop.close()
            
            if result.get("success"):
                stats = result.get("processing_stats", {})
                
                # Copy files to user's chosen directory
                output_files = self.copy_output_files(result.get("dataset_files", {}), dataset_name)
                
                self.log_message("✅ Q&A generation completed successfully!")
                self.log_message(f"📊 Generated {stats.get('qa_pairs_generated', 0)} Q&A pairs")
                self.log_message(f"💾 Files saved to: {self.output_directory}")
                
                for filename in output_files:
                    self.log_message(f"   📄 {filename}")
                
                self.update_status("Dataset generation completed!", "green")
                
                # Show completion dialog
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success", 
                    f"Successfully generated {stats.get('qa_pairs_generated', 0)} Q&A pairs!\n\n"
                    f"Files saved to:\n{self.output_directory}"
                ))
                
            else:
                error_msg = result.get("error", "Unknown error")
                self.log_message(f"❌ Processing failed: {error_msg}")
                self.update_status(f"Error: {error_msg}", "red")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Processing failed:\n{error_msg}"))
        
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"❌ Unexpected error: {error_msg}")
            self.update_status(f"Error: {error_msg}", "red")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Unexpected error:\n{error_msg}"))
        
        finally:
            # Re-enable UI
            self.root.after(0, self.processing_finished)
    
    def copy_output_files(self, dataset_files, dataset_name):
        """Copy generated files to user's output directory"""
        output_files = []
        
        for quality_tier, source_path in dataset_files.items():
            if Path(source_path).exists():
                # Create new filename
                filename = f"{dataset_name}_{quality_tier}_quality.jsonl"
                dest_path = Path(self.output_directory) / filename
                
                # Copy file content
                import shutil
                shutil.copy2(source_path, dest_path)
                output_files.append(filename)
        
        return output_files
    
    def processing_finished(self):
        """Clean up after processing"""
        self.progress_bar.stop()
        self.process_button.config(state='normal')
    
    def log_message(self, message):
        """Add message to log output"""
        def _log():
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        
        if threading.current_thread() == threading.main_thread():
            _log()
        else:
            self.root.after(0, _log)
    
    def update_status(self, message, color="blue"):
        """Update status label"""
        def _update():
            self.status_var.set(message)
            self.status_label.config(foreground=color)
        
        if threading.current_thread() == threading.main_thread():
            _update()
        else:
            self.root.after(0, _update)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main application entry point"""
    app = TrainingQAGeneratorApp()
    app.run()

if __name__ == "__main__":
    main()
