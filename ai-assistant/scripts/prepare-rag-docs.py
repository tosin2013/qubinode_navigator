#!/usr/bin/env python3
"""
Documentation RAG Preparation Script
Analyzes and structures existing documentation for RAG embedding integration
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
"""

import os
import json
import yaml
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import re
from datetime import datetime

@dataclass
class DocumentChunk:
    """Represents a chunk of documentation for RAG processing"""
    id: str
    source_file: str
    title: str
    content: str
    chunk_type: str  # 'markdown', 'yaml', 'code', 'adr', 'config'
    metadata: Dict[str, Any]
    word_count: int
    created_at: str

class DocumentationAnalyzer:
    """Analyzes and prepares documentation for RAG integration"""
    
    def __init__(self, project_root: str = "/root/qubinode_navigator"):
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "ai-assistant" / "data" / "rag-docs"
        self.chunks: List[DocumentChunk] = []
        
        # Document type patterns
        self.doc_patterns = {
            'adr': r'docs/adrs/.*\.md$',
            'research': r'docs/.*research.*\.md$',
            'vault': r'docs/.*vault.*\.md$',
            'config': r'.*\.(yml|yaml)$',
            'readme': r'README\.md$',
            'implementation': r'IMPLEMENTATION-PLAN\.md$',
            'prd': r'PRD\.md$'
        }
        
    def analyze_project_docs(self) -> Dict[str, Any]:
        """Analyze all documentation in the project"""
        print("🔍 Analyzing project documentation structure...")
        
        analysis = {
            'total_files': 0,
            'by_type': {},
            'by_directory': {},
            'file_list': []
        }
        
        # Find all documentation files
        doc_extensions = ['.md', '.rst', '.txt', '.yml', '.yaml']
        
        for ext in doc_extensions:
            files = list(self.project_root.rglob(f'*{ext}'))
            for file_path in files:
                if self._should_include_file(file_path):
                    rel_path = file_path.relative_to(self.project_root)
                    doc_type = self._classify_document(str(rel_path))
                    
                    file_info = {
                        'path': str(rel_path),
                        'type': doc_type,
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    
                    analysis['file_list'].append(file_info)
                    analysis['by_type'][doc_type] = analysis['by_type'].get(doc_type, 0) + 1
                    
                    dir_name = str(rel_path.parent)
                    analysis['by_directory'][dir_name] = analysis['by_directory'].get(dir_name, 0) + 1
        
        analysis['total_files'] = len(analysis['file_list'])
        return analysis
    
    def _should_include_file(self, file_path: Path) -> bool:
        """Determine if a file should be included in RAG processing"""
        # Skip certain directories and files
        skip_patterns = [
            '/.git/',
            '/_site/',
            '/node_modules/',
            '/.pytest_cache/',
            '__pycache__',
            '.pyc',
            'test_',
            '.tmp'
        ]
        
        path_str = str(file_path)
        return not any(pattern in path_str for pattern in skip_patterns)
    
    def _classify_document(self, file_path: str) -> str:
        """Classify document type based on path patterns"""
        for doc_type, pattern in self.doc_patterns.items():
            if re.search(pattern, file_path, re.IGNORECASE):
                return doc_type
        
        # Default classification based on extension
        if file_path.endswith('.md'):
            return 'markdown'
        elif file_path.endswith(('.yml', '.yaml')):
            return 'config'
        elif file_path.endswith('.rst'):
            return 'restructured_text'
        else:
            return 'text'
    
    def process_markdown_file(self, file_path: Path) -> List[DocumentChunk]:
        """Process a markdown file into chunks"""
        chunks = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            rel_path = file_path.relative_to(self.project_root)
            
            # Split by headers for better chunking
            sections = self._split_markdown_by_headers(content)
            
            for i, (title, section_content) in enumerate(sections):
                if len(section_content.strip()) < 50:  # Skip very short sections
                    continue
                
                chunk_id = hashlib.md5(f"{rel_path}_{i}_{title}".encode()).hexdigest()[:12]
                
                metadata = {
                    'section_index': i,
                    'file_type': 'markdown',
                    'document_type': self._classify_document(str(rel_path)),
                    'relative_path': str(rel_path)
                }
                
                chunk = DocumentChunk(
                    id=chunk_id,
                    source_file=str(rel_path),
                    title=title or f"Section {i+1}",
                    content=section_content.strip(),
                    chunk_type='markdown',
                    metadata=metadata,
                    word_count=len(section_content.split()),
                    created_at=datetime.now().isoformat()
                )
                
                chunks.append(chunk)
                
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
        
        return chunks
    
    def _split_markdown_by_headers(self, content: str) -> List[tuple]:
        """Split markdown content by headers"""
        lines = content.split('\n')
        sections = []
        current_title = None
        current_content = []
        
        for line in lines:
            # Check for markdown headers
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
    
    def process_yaml_file(self, file_path: Path) -> List[DocumentChunk]:
        """Process YAML configuration files"""
        chunks = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            rel_path = file_path.relative_to(self.project_root)
            
            # Parse YAML to extract structure
            try:
                yaml_data = yaml.safe_load(content)
                description = self._extract_yaml_description(yaml_data, file_path)
            except:
                description = f"Configuration file: {file_path.name}"
            
            chunk_id = hashlib.md5(str(rel_path).encode()).hexdigest()[:12]
            
            metadata = {
                'file_type': 'yaml',
                'document_type': self._classify_document(str(rel_path)),
                'relative_path': str(rel_path),
                'config_category': self._categorize_config(file_path)
            }
            
            chunk = DocumentChunk(
                id=chunk_id,
                source_file=str(rel_path),
                title=description,
                content=content,
                chunk_type='yaml',
                metadata=metadata,
                word_count=len(content.split()),
                created_at=datetime.now().isoformat()
            )
            
            chunks.append(chunk)
            
        except Exception as e:
            print(f"⚠️  Error processing YAML {file_path}: {e}")
        
        return chunks
    
    def _extract_yaml_description(self, yaml_data: Any, file_path: Path) -> str:
        """Extract meaningful description from YAML data"""
        if isinstance(yaml_data, dict):
            # Look for common description fields
            for key in ['description', 'name', 'title', 'summary']:
                if key in yaml_data:
                    return f"{file_path.name}: {yaml_data[key]}"
        
        return f"Configuration: {file_path.name}"
    
    def _categorize_config(self, file_path: Path) -> str:
        """Categorize configuration files"""
        path_str = str(file_path).lower()
        
        if 'inventory' in path_str or 'group_vars' in path_str:
            return 'inventory'
        elif 'ansible' in path_str:
            return 'ansible'
        elif 'vault' in path_str:
            return 'vault'
        elif 'ai-assistant' in path_str:
            return 'ai_config'
        else:
            return 'general'
    
    def process_all_documents(self) -> None:
        """Process all documents in the project"""
        print("📚 Processing all documentation files...")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process markdown files
        md_files = list(self.project_root.rglob('*.md'))
        for md_file in md_files:
            if self._should_include_file(md_file):
                chunks = self.process_markdown_file(md_file)
                self.chunks.extend(chunks)
        
        # Process YAML files
        yaml_files = list(self.project_root.rglob('*.yml')) + list(self.project_root.rglob('*.yaml'))
        for yaml_file in yaml_files:
            if self._should_include_file(yaml_file):
                chunks = self.process_yaml_file(yaml_file)
                self.chunks.extend(chunks)
        
        print(f"✅ Processed {len(self.chunks)} document chunks")
    
    def save_processed_chunks(self) -> None:
        """Save processed chunks to JSON files"""
        print("💾 Saving processed document chunks...")
        
        # Save all chunks
        chunks_data = [asdict(chunk) for chunk in self.chunks]
        chunks_file = self.output_dir / "document_chunks.json"
        
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        # Save chunks by type
        by_type = {}
        for chunk in self.chunks:
            chunk_type = chunk.metadata.get('document_type', 'unknown')
            if chunk_type not in by_type:
                by_type[chunk_type] = []
            by_type[chunk_type].append(asdict(chunk))
        
        for doc_type, type_chunks in by_type.items():
            type_file = self.output_dir / f"chunks_{doc_type}.json"
            with open(type_file, 'w', encoding='utf-8') as f:
                json.dump(type_chunks, f, indent=2, ensure_ascii=False)
        
        # Save metadata summary
        summary = {
            'total_chunks': len(self.chunks),
            'chunks_by_type': {k: len(v) for k, v in by_type.items()},
            'total_words': sum(chunk.word_count for chunk in self.chunks),
            'processed_at': datetime.now().isoformat(),
            'output_files': {
                'all_chunks': str(chunks_file.relative_to(self.project_root)),
                'by_type': {k: str((self.output_dir / f"chunks_{k}.json").relative_to(self.project_root)) 
                           for k in by_type.keys()}
            }
        }
        
        summary_file = self.output_dir / "processing_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(self.chunks)} chunks to {self.output_dir}")
        print(f"📊 Summary: {summary['total_words']} total words across {len(by_type)} document types")

def main():
    """Main execution function"""
    print("🚀 Starting Documentation RAG Preparation")
    print("=" * 50)
    
    analyzer = DocumentationAnalyzer()
    
    # Analyze project structure
    analysis = analyzer.analyze_project_docs()
    print(f"📈 Found {analysis['total_files']} documentation files")
    print(f"📂 Document types: {', '.join(analysis['by_type'].keys())}")
    
    # Process all documents
    analyzer.process_all_documents()
    
    # Save processed chunks
    analyzer.save_processed_chunks()
    
    print("\n🎉 RAG documentation preparation complete!")
    print(f"📁 Output directory: {analyzer.output_dir}")
    print("\n📋 Next steps:")
    print("  1. Review processed chunks in ai-assistant/data/rag-docs/")
    print("  2. Integrate with vector database (ChromaDB)")
    print("  3. Test RAG retrieval with AI assistant")

if __name__ == "__main__":
    main()
