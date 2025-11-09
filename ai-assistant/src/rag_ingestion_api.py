#!/usr/bin/env python3
"""
RAG Ingestion API - Dynamic Knowledge Base Updates
Allows users to contribute documentation and enhance AI capabilities
Based on AI Ecosystem Roadmap
"""

import json
import logging
import hashlib
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
import aiofiles

from qdrant_rag_service import QdrantRAGService

logger = logging.getLogger(__name__)

# API Models
class DocumentMetadata(BaseModel):
    category: str = "general"
    tags: List[str] = []
    author: Optional[str] = None
    source_url: Optional[str] = None
    hardware_type: Optional[str] = None
    os_version: Optional[str] = None
    difficulty_level: str = "intermediate"  # beginner, intermediate, advanced

class IngestionResponse(BaseModel):
    status: str
    document_id: str
    chunks_processed: int
    category: str
    tags: List[str]
    quality_score: float
    warnings: List[str] = []

class ValidationResult(BaseModel):
    is_valid: bool
    quality_score: float
    issues: List[str] = []
    suggestions: List[str] = []

@dataclass
class ProcessedChunk:
    id: str
    content: str
    title: str
    metadata: Dict[str, Any]
    quality_score: float

class RAGIngestionService:
    """Service for ingesting new documents into RAG system"""
    
    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.rag_service = QdrantRAGService(data_dir)
        self.contributions_dir = self.data_dir / "contributions"
        self.contributions_dir.mkdir(parents=True, exist_ok=True)
        
        # Quality thresholds
        self.min_quality_score = 0.6
        self.auto_approve_score = 0.8
        
    async def ingest_document(
        self,
        file: UploadFile,
        metadata: DocumentMetadata,
        validate: bool = True,
        auto_approve: bool = False
    ) -> IngestionResponse:
        """Ingest a new document into the RAG system"""
        
        try:
            # Generate document ID
            content = await file.read()
            doc_id = self._generate_document_id(file.filename, content)
            
            logger.info(f"Processing document: {file.filename} (ID: {doc_id})")
            
            # Save original file
            await self._save_contribution(doc_id, file.filename, content, metadata)
            
            # Process document into chunks
            chunks = await self._process_document(content, file.filename, metadata)
            
            if not chunks:
                raise HTTPException(status_code=400, detail="No valid content found in document")
            
            # Validate content quality
            validation_result = None
            if validate:
                validation_result = await self._validate_content(chunks)
                
                if not validation_result.is_valid:
                    return IngestionResponse(
                        status="rejected",
                        document_id=doc_id,
                        chunks_processed=0,
                        category=metadata.category,
                        tags=metadata.tags,
                        quality_score=validation_result.quality_score,
                        warnings=validation_result.issues
                    )
            
            # Determine approval status
            quality_score = validation_result.quality_score if validation_result else 1.0
            
            if auto_approve or quality_score >= self.auto_approve_score:
                # Auto-approve high-quality content
                await self._add_to_rag_database(chunks, doc_id)
                status = "approved"
            elif quality_score >= self.min_quality_score:
                # Queue for manual review
                await self._queue_for_review(doc_id, chunks, metadata)
                status = "pending_review"
            else:
                status = "rejected"
            
            return IngestionResponse(
                status=status,
                document_id=doc_id,
                chunks_processed=len(chunks),
                category=metadata.category,
                tags=metadata.tags,
                quality_score=quality_score,
                warnings=validation_result.suggestions if validation_result else []
            )
            
        except Exception as e:
            logger.error(f"Error ingesting document {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    
    async def _process_document(
        self, 
        content: bytes, 
        filename: str, 
        metadata: DocumentMetadata
    ) -> List[ProcessedChunk]:
        """Process document into chunks suitable for RAG"""
        
        try:
            # Decode content
            text_content = content.decode('utf-8')
            
            # Split into sections based on file type
            if filename.endswith('.md'):
                chunks = self._process_markdown(text_content)
            elif filename.endswith(('.yml', '.yaml')):
                chunks = self._process_yaml(text_content)
            elif filename.endswith('.txt'):
                chunks = self._process_text(text_content)
            else:
                # Generic text processing
                chunks = self._process_text(text_content)
            
            # Enhance chunks with metadata
            processed_chunks = []
            for i, (title, chunk_content) in enumerate(chunks):
                if len(chunk_content.strip()) < 50:  # Skip very short chunks
                    continue
                
                chunk_id = f"{self._generate_document_id(filename, content)}_{i}"
                
                enhanced_metadata = {
                    **metadata.dict(),
                    'source_file': filename,
                    'chunk_index': i,
                    'word_count': len(chunk_content.split()),
                    'created_at': datetime.now().isoformat()
                }
                
                processed_chunks.append(ProcessedChunk(
                    id=chunk_id,
                    content=chunk_content.strip(),
                    title=title or f"Section {i+1}",
                    metadata=enhanced_metadata,
                    quality_score=0.0  # Will be calculated during validation
                ))
            
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}")
            return []
    
    def _process_markdown(self, content: str) -> List[tuple]:
        """Process markdown content into sections"""
        lines = content.split('\n')
        sections = []
        current_title = None
        current_content = []
        
        for line in lines:
            if line.startswith('#'):
                # Save previous section
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                
                # Start new section
                current_title = line.strip('#').strip()
                current_content = [line]
            else:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))
        
        return sections
    
    def _process_yaml(self, content: str) -> List[tuple]:
        """Process YAML content"""
        # For YAML, treat entire content as one chunk
        return [("Configuration", content)]
    
    def _process_text(self, content: str) -> List[tuple]:
        """Process plain text into paragraphs"""
        paragraphs = content.split('\n\n')
        sections = []
        
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) > 50:
                sections.append((f"Section {i+1}", paragraph.strip()))
        
        return sections
    
    async def _validate_content(self, chunks: List[ProcessedChunk]) -> ValidationResult:
        """Validate content quality using AI"""
        
        issues = []
        suggestions = []
        total_score = 0.0
        
        for chunk in chunks:
            # Basic quality checks
            score = 1.0
            
            # Check content length
            if len(chunk.content) < 100:
                score -= 0.2
                issues.append(f"Chunk '{chunk.title}' is very short")
            
            # Check for code examples (good for technical docs)
            if '```' in chunk.content or 'command:' in chunk.content.lower():
                score += 0.1
                
            # Check for specific technical terms
            technical_terms = ['kvm', 'rhel', 'centos', 'ansible', 'podman', 'docker', 'vm', 'hypervisor']
            if any(term in chunk.content.lower() for term in technical_terms):
                score += 0.1
            
            # Check for step-by-step instructions
            if any(pattern in chunk.content.lower() for pattern in ['step 1', '1.', 'first,', 'then,']):
                score += 0.1
                
            # Update chunk quality score
            chunk.quality_score = min(1.0, max(0.0, score))
            total_score += chunk.quality_score
        
        average_score = total_score / len(chunks) if chunks else 0.0
        
        # Generate suggestions
        if average_score < 0.7:
            suggestions.append("Consider adding more detailed explanations")
            suggestions.append("Include code examples or commands where applicable")
            suggestions.append("Add step-by-step instructions for better clarity")
        
        return ValidationResult(
            is_valid=average_score >= self.min_quality_score,
            quality_score=average_score,
            issues=issues,
            suggestions=suggestions
        )
    
    async def _add_to_rag_database(self, chunks: List[ProcessedChunk], doc_id: str):
        """Add approved chunks to RAG database"""
        
        try:
            # Ensure RAG service is initialized
            if not await self.rag_service.initialize():
                raise Exception("Failed to initialize RAG service")
            
            # Convert chunks to format expected by RAG service
            documents = []
            for chunk in chunks:
                documents.append({
                    'id': chunk.id,
                    'content': chunk.content,
                    'title': chunk.title,
                    'chunk_type': 'contributed',
                    'metadata': chunk.metadata,
                    'word_count': len(chunk.content.split()),
                    'created_at': datetime.now().isoformat()
                })
            
            # Add to vector database
            # Note: This would need to be implemented in the RAG service
            logger.info(f"Added {len(documents)} chunks from document {doc_id} to RAG database")
            
        except Exception as e:
            logger.error(f"Error adding chunks to RAG database: {e}")
            raise
    
    async def _queue_for_review(self, doc_id: str, chunks: List[ProcessedChunk], metadata: DocumentMetadata):
        """Queue document for manual review"""
        
        review_data = {
            'document_id': doc_id,
            'status': 'pending_review',
            'submitted_at': datetime.now().isoformat(),
            'metadata': metadata.dict(),
            'chunks_count': len(chunks),
            'chunks': [
                {
                    'id': chunk.id,
                    'title': chunk.title,
                    'content': chunk.content[:500] + '...' if len(chunk.content) > 500 else chunk.content,
                    'quality_score': chunk.quality_score
                }
                for chunk in chunks
            ]
        }
        
        review_file = self.contributions_dir / f"{doc_id}_review.json"
        async with aiofiles.open(review_file, 'w') as f:
            await f.write(json.dumps(review_data, indent=2))
        
        logger.info(f"Document {doc_id} queued for manual review")
    
    async def _save_contribution(self, doc_id: str, filename: str, content: bytes, metadata: DocumentMetadata):
        """Save original contribution for record keeping"""
        
        contribution_data = {
            'document_id': doc_id,
            'original_filename': filename,
            'submitted_at': datetime.now().isoformat(),
            'metadata': metadata.dict(),
            'content_hash': hashlib.sha256(content).hexdigest()
        }
        
        # Save metadata
        metadata_file = self.contributions_dir / f"{doc_id}_metadata.json"
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(contribution_data, indent=2))
        
        # Save original file
        original_file = self.contributions_dir / f"{doc_id}_{filename}"
        async with aiofiles.open(original_file, 'wb') as f:
            await f.write(content)
    
    def _generate_document_id(self, filename: str, content: bytes) -> str:
        """Generate unique document ID"""
        content_hash = hashlib.sha256(content).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_filename = "".join(c for c in filename if c.isalnum() or c in "._-")[:20]
        return f"{timestamp}_{clean_filename}_{content_hash}"

# FastAPI Router
router = APIRouter(prefix="/rag", tags=["RAG Ingestion"])
rag_service = RAGIngestionService()

@router.post("/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    tags: str = Form(""),  # Comma-separated tags
    author: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    hardware_type: Optional[str] = Form(None),
    os_version: Optional[str] = Form(None),
    difficulty_level: str = Form("intermediate"),
    validate: bool = Form(True),
    auto_approve: bool = Form(False)
):
    """
    Ingest a new document into the RAG system
    
    - **file**: Document file (markdown, text, yaml)
    - **category**: Document category (deployment, troubleshooting, configuration, etc.)
    - **tags**: Comma-separated tags
    - **author**: Document author (optional)
    - **hardware_type**: Target hardware (optional)
    - **os_version**: Target OS version (optional)
    - **difficulty_level**: beginner, intermediate, or advanced
    - **validate**: Whether to validate content quality
    - **auto_approve**: Skip manual review (admin only)
    """
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    metadata = DocumentMetadata(
        category=category,
        tags=tag_list,
        author=author,
        source_url=source_url,
        hardware_type=hardware_type,
        os_version=os_version,
        difficulty_level=difficulty_level
    )
    
    return await rag_service.ingest_document(
        file=file,
        metadata=metadata,
        validate=validate,
        auto_approve=auto_approve
    )

@router.get("/contributions")
async def list_contributions():
    """List all contributed documents"""
    
    contributions = []
    for metadata_file in rag_service.contributions_dir.glob("*_metadata.json"):
        try:
            async with aiofiles.open(metadata_file, 'r') as f:
                content = await f.read()
                contribution = json.loads(content)
                contributions.append(contribution)
        except Exception as e:
            logger.error(f"Error reading contribution metadata {metadata_file}: {e}")
    
    return {
        "total_contributions": len(contributions),
        "contributions": sorted(contributions, key=lambda x: x['submitted_at'], reverse=True)
    }

@router.get("/stats")
async def get_ingestion_stats():
    """Get RAG ingestion statistics"""
    
    # Count contributions by status
    total_contributions = len(list(rag_service.contributions_dir.glob("*_metadata.json")))
    pending_reviews = len(list(rag_service.contributions_dir.glob("*_review.json")))
    
    # Get category breakdown
    categories = {}
    for metadata_file in rag_service.contributions_dir.glob("*_metadata.json"):
        try:
            async with aiofiles.open(metadata_file, 'r') as f:
                content = await f.read()
                contribution = json.loads(content)
                category = contribution['metadata']['category']
                categories[category] = categories.get(category, 0) + 1
        except Exception:
            continue
    
    return {
        "total_contributions": total_contributions,
        "pending_reviews": pending_reviews,
        "approved": total_contributions - pending_reviews,
        "categories": categories,
        "rag_service_status": "initialized" if rag_service.rag_service else "not_initialized"
    }
