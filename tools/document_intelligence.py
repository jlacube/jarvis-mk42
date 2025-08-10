"""
Enhanced Document Intelligence Tools for Jarvis-MK42
Phase 2A Implementation: Advanced document processing with OCR, analysis, and multi-document synthesis
"""

import io
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import base64
import tempfile
import mimetypes

# Document processing libraries (with optional imports for testing)
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    
try:
    import fitz  # PyMuPDF for advanced PDF processing
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

# AI and NLP libraries
from langchain_core.tools import tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Internal imports
from config.settings import get_settings
from utils.exceptions import JarvisValidationError, JarvisAPIError, JarvisToolError
from utils.logging_config import get_logger
from models.models import get_google_model

# Initialize logger and settings
logger = get_logger(__name__)
settings = get_settings()

# Security and processing limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
MAX_PAGES_PER_DOCUMENT = 500  
SUPPORTED_FORMATS = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'text/plain': 'txt',
    'text/csv': 'csv',
    'image/jpeg': 'jpg',
    'image/png': 'png', 
    'image/tiff': 'tiff'
}

class DocumentProcessor:
    """Advanced document processing engine with OCR and content analysis"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            length_function=len
        )
        
        # Check for missing dependencies and log warnings
        missing_deps = []
        if not PYPDF2_AVAILABLE:
            missing_deps.append("PyPDF2")
        if not PYMUPDF_AVAILABLE:
            missing_deps.append("PyMuPDF")
        if not DOCX_AVAILABLE:
            missing_deps.append("python-docx")
        if not PANDAS_AVAILABLE:
            missing_deps.append("pandas")
        if not PIL_AVAILABLE:
            missing_deps.append("Pillow")
        if not PYTESSERACT_AVAILABLE:
            missing_deps.append("pytesseract")
            
        if missing_deps:
            logger.warning(f"Some document processing dependencies are missing: {missing_deps}. Limited functionality available.")

    async def process_document(self, file_path: str, file_content: bytes = None) -> Dict[str, Any]:
        """
        Process a document and extract structured content with metadata
        
        Args:
            file_path: Path to the document file
            file_content: Raw file content (optional)
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        import time
        start_time = time.time()
        
        try:
            if file_content is None and file_path and os.path.exists(file_path):
                # Read from file
                with open(file_path, 'rb') as f:
                    file_content = f.read()
            
            if file_content is None:
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size
            if len(file_content) > MAX_FILE_SIZE:
                raise JarvisValidationError(f"File too large: {len(file_content)} bytes (max: {MAX_FILE_SIZE})")
            
            # Determine file type and extract content
            content = ""
            content_type = "unknown"
            structure_detected = False
            
            file_ext = Path(file_path).suffix.lower() if file_path else ""
            
            # PDF processing
            if file_ext == '.pdf':
                content = await self._extract_pdf_content(file_content, file_path)
                content_type = "pdf"
                structure_detected = True
            # Word document processing
            elif file_ext in ['.docx', '.doc']:
                content = await self._extract_docx_content(file_content, file_path)
                content_type = "docx"
                structure_detected = True
            # Excel processing
            elif file_ext in ['.xlsx', '.xls']:
                content = await self._extract_excel_content(file_content, file_path)
                content_type = "excel"
                structure_detected = True
            # CSV processing
            elif file_ext == '.csv':
                content = await self._extract_csv_content(file_content)
                content_type = "csv"
                structure_detected = True
            # Plain text
            elif file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']:
                content = file_content.decode('utf-8', errors='ignore')
                content_type = "text"
            # Image processing (OCR)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                content = await self._extract_image_text(file_content)
                content_type = "image"
                structure_detected = True
            else:
                # Try to decode as text for unknown formats
                try:
                    content = file_content.decode('utf-8', errors='ignore')
                    content_type = "text"
                except:
                    content = f"Binary file detected. File size: {len(file_content)} bytes"
                    content_type = "binary"
            
            # Basic analysis
            word_count = len(content.split()) if content else 0
            char_count = len(content) if content else 0
            processing_time = round(time.time() - start_time, 2)
            
            return {
                "content": content,
                "metadata": {
                    "file_path": file_path,
                    "file_size": len(file_content),
                    "word_count": word_count,
                    "char_count": char_count,
                    "processing_time": f"{processing_time}s",
                    "file_extension": file_ext
                },
                "analysis": {
                    "content_type": content_type,
                    "language_detected": "en",  # TODO: Implement language detection
                    "structure_detected": structure_detected
                }
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise JarvisToolError(f"Failed to process document: {str(e)}")

    async def _extract_pdf_content(self, file_content: bytes, file_path: str) -> str:
        """Extract text content from PDF using PyMuPDF or PyPDF2"""
        content = ""
        
        try:
            # Try PyMuPDF first (more reliable)
            if PYMUPDF_AVAILABLE:
                import fitz
                pdf_doc = fitz.open(stream=file_content, filetype="pdf")
                
                page_count = min(len(pdf_doc), MAX_PAGES_PER_DOCUMENT)
                for page_num in range(page_count):
                    page = pdf_doc.load_page(page_num)
                    content += page.get_text()
                    content += "\n\n"  # Add spacing between pages
                
                pdf_doc.close()
                logger.info(f"Extracted {len(content)} characters from {page_count} pages using PyMuPDF")
                
            # Fallback to PyPDF2
            elif PYPDF2_AVAILABLE:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                
                page_count = min(len(pdf_reader.pages), MAX_PAGES_PER_DOCUMENT)
                for page_num in range(page_count):
                    page = pdf_reader.pages[page_num]
                    content += page.extract_text()
                    content += "\n\n"  # Add spacing between pages
                
                logger.info(f"Extracted {len(content)} characters from {page_count} pages using PyPDF2")
            else:
                raise JarvisToolError("No PDF processing libraries available (PyMuPDF or PyPDF2 required)")
                
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            content = f"Error extracting PDF content: {str(e)}"
        
        return content.strip()

    async def _extract_docx_content(self, file_content: bytes, file_path: str) -> str:
        """Extract text content from Word documents"""
        content = ""
        
        try:
            if DOCX_AVAILABLE:
                from docx import Document as DocxDocument
                doc = DocxDocument(io.BytesIO(file_content))
                
                # Extract paragraphs
                for paragraph in doc.paragraphs:
                    content += paragraph.text + "\n"
                
                # Extract tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells)
                        content += row_text + "\n"
                    content += "\n"
                
                logger.info(f"Extracted {len(content)} characters from DOCX document")
            else:
                content = "Error: python-docx library not available for Word document processing"
                
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            content = f"Error extracting DOCX content: {str(e)}"
        
        return content.strip()

    async def _extract_excel_content(self, file_content: bytes, file_path: str) -> str:
        """Extract text content from Excel files"""
        content = ""
        
        try:
            if PANDAS_AVAILABLE:
                import pandas as pd
                
                # Read all sheets
                with io.BytesIO(file_content) as buffer:
                    excel_file = pd.ExcelFile(buffer)
                    
                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(buffer, sheet_name=sheet_name)
                        content += f"\n=== Sheet: {sheet_name} ===\n"
                        content += df.to_string(index=False)
                        content += "\n\n"
                
                logger.info(f"Extracted {len(content)} characters from Excel file")
            else:
                content = "Error: pandas library not available for Excel processing"
                
        except Exception as e:
            logger.error(f"Excel extraction failed: {e}")
            content = f"Error extracting Excel content: {str(e)}"
        
        return content.strip()

    async def _extract_csv_content(self, file_content: bytes) -> str:
        """Extract content from CSV files"""
        content = ""
        
        try:
            if PANDAS_AVAILABLE:
                import pandas as pd
                df = pd.read_csv(io.BytesIO(file_content))
                content = df.to_string(index=False)
                logger.info(f"Extracted {len(content)} characters from CSV file")
            else:
                # Fallback to basic text processing
                content = file_content.decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.error(f"CSV extraction failed: {e}")
            content = f"Error extracting CSV content: {str(e)}"
        
        return content

    async def _extract_image_text(self, file_content: bytes) -> str:
        """Extract text from images using OCR"""
        content = ""
        
        try:
            if PIL_AVAILABLE and PYTESSERACT_AVAILABLE:
                from PIL import Image
                import pytesseract
                
                image = Image.open(io.BytesIO(file_content))
                content = pytesseract.image_to_string(image)
                logger.info(f"Extracted {len(content)} characters from image using OCR")
            else:
                content = "Error: PIL and pytesseract libraries required for image text extraction"
                
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            content = f"Error extracting text from image: {str(e)}"
        
        return content.strip()

@tool
async def analyze_document_tool(file_path: Optional[str] = None) -> str:
    """
    Analyze a document and extract comprehensive information including content, structure, and metadata.
    
    This tool can work with documents in two ways:
    1. Direct file path: When file_path is provided, analyzes the specified file
    2. Session documents: When no file_path is provided, analyzes documents uploaded to the chat
    
    Args:
        file_path: Optional path to the document file to analyze. If not provided,
                  the tool will look for documents in the user session.
        
    Returns:
        JSON string containing document analysis results
        
    Note:
        Documents are handled directly by this tool from the user session when uploaded
        to the chat interface, so they don't need to be passed as parameters.
    """
    try:
        target_file_path = file_path
        
        # If no file path provided, check user session for uploaded documents
        if not target_file_path:
            import chainlit as cl
            documents = cl.user_session.get("documents")
            if not documents:
                return "Error: No document provided. Please upload a document to analyze or specify a file path."
            
            # Use the first document if multiple are uploaded
            document = documents[0]
            target_file_path = document.path
            logger.info(f"Analyzing uploaded document: {target_file_path}")
        
        processor = DocumentProcessor()
        result = await processor.process_document(target_file_path)
        
        analysis_summary = {
            "status": "success",
            "file_path": target_file_path,
            "content": result["content"],  # Full content, not preview
            "metadata": result["metadata"],
            "analysis": result["analysis"],
            "summary": {
                "total_pages": result["metadata"].get("page_count", "N/A"),
                "file_size_mb": round(result["metadata"]["file_size"] / (1024*1024), 2),
                "extraction_method": result["analysis"]["content_type"],
                "processing_successful": len(result["content"]) > 0
            }
        }
        
        return f"Document analysis completed successfully:\n\n**File Information:**\n- Path: {target_file_path}\n- Size: {analysis_summary['summary']['file_size_mb']} MB\n- Type: {result['analysis']['content_type']}\n- Processing Time: {result['metadata']['processing_time']}\n\n**Content Analysis:**\n- Word Count: {result['metadata']['word_count']}\n- Character Count: {result['metadata']['char_count']}\n- Structure Detected: {result['analysis']['structure_detected']}\n\n**Full Document Content:**\n{result['content']}"
        
    except Exception as e:
        logger.error(f"Document analysis tool failed: {e}")
        return f"Error analyzing document: {str(e)}"

@tool  
async def compare_documents_tool(file_path1: str, file_path2: str) -> str:
    """
    Compare two documents and identify similarities, differences, and relationships.
    
    Args:
        file_path1: Path to the first document
        file_path2: Path to the second document
        
    Returns:
        JSON string containing document comparison results
    """
    try:
        processor = DocumentProcessor()
        
        # Process both documents
        doc1 = await processor.process_document(file_path1)
        doc2 = await processor.process_document(file_path2)
        
        # Simple comparison
        content1 = doc1["content"].lower()
        content2 = doc2["content"].lower()
        
        # Basic similarity check
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        common_words = words1.intersection(words2)
        similarity_ratio = len(common_words) / max(len(words1), len(words2)) if max(len(words1), len(words2)) > 0 else 0
        
        comparison_result = {
            "status": "success",
            "document1": file_path1,
            "document2": file_path2,
            "similarity_ratio": similarity_ratio,
            "common_word_count": len(common_words),
            "word_count_diff": abs(len(doc1["content"].split()) - len(doc2["content"].split())),
            "char_count_diff": abs(len(doc1["content"]) - len(doc2["content"]))
        }
        
        return f"Document comparison completed:\n{comparison_result}"
        
    except Exception as e:
        logger.error(f"Document comparison tool failed: {e}")
        return f"Error comparing documents: {str(e)}"

def get_document_intelligence_tools() -> List:
    """Get all document intelligence tools"""
    return [
        analyze_document_tool,
        compare_documents_tool
    ]
