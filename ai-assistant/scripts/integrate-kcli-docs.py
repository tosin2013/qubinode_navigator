#!/usr/bin/env python3
"""
KCLI Documentation Integration Script

Fetches kcli documentation from https://kcli.readthedocs.io and integrates
it into the AI assistant RAG system for infrastructure guidance.
"""

import sys
import json
import hashlib
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class KcliDocChunk:
    """Represents a chunk of kcli documentation"""

    id: str
    source_url: str
    title: str
    content: str
    section: str
    chunk_type: str  # 'overview', 'tutorial', 'reference', 'example'
    metadata: Dict[str, Any]
    word_count: int
    created_at: str


class KcliDocumentationIntegrator:
    """Integrates kcli documentation into AI assistant RAG system"""

    def __init__(self):
        self.repo_url = "https://github.com/karmab/kcli.git"
        self.output_dir = Path(__file__).parent.parent / "data" / "rag-docs"
        self.chunks: List[KcliDocChunk] = []
        self.temp_dir = None

        # Documentation files to process from the repository
        self.doc_files = [
            "README.md",
            "docs/index.md",
            "docs/installation.md",
            "docs/usage.md",
            "docs/plans.md",
            "docs/vms.md",
            "docs/kubernetes.md",
            "docs/openshift.md",
            "docs/providers.md",
            "docs/networking.md",
            "docs/storage.md",
            "docs/troubleshooting.md",
            "docs/examples.md",
        ]

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch_documentation(self) -> Dict[str, Any]:
        """Clone kcli repository and read documentation files"""

        print("🔍 Cloning kcli repository from GitHub...")

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="kcli_docs_")

        try:
            # Clone the repository
            print(f"  Cloning {self.repo_url}...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", self.repo_url, self.temp_dir],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")

            print(f"  Repository cloned to {self.temp_dir}")

            # Read documentation files
            fetched_docs = {}
            repo_path = Path(self.temp_dir)

            for doc_file in self.doc_files:
                file_path = repo_path / doc_file

                if file_path.exists():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        section_name = file_path.stem  # Get filename without extension

                        fetched_docs[section_name] = {
                            "file_path": str(file_path),
                            "relative_path": doc_file,
                            "content": content,
                            "size": len(content),
                            "type": "markdown" if file_path.suffix == ".md" else "text",
                        }

                        print(f"  ✅ Read {doc_file} ({len(content)} chars)")

                    except Exception as e:
                        print(f"  ❌ Failed to read {doc_file}: {e}")
                        continue
                else:
                    print(f"  ⚠️  File not found: {doc_file}")

            print(f"✅ Successfully read {len(fetched_docs)} documentation files")
            return fetched_docs

        except Exception as e:
            print(f"❌ Failed to clone repository: {e}")
            return {}

    def cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")

    def parse_markdown_content(self, content: str, section: str, file_path: str) -> List[KcliDocChunk]:
        """Parse Markdown content into structured chunks"""

        chunks = []

        # Extract title from first H1 or use filename
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        page_title = title_match.group(1).strip() if title_match else f"KCLI {section.title()}"

        # Split content by headers (# ## ### etc.)
        sections = self._split_markdown_by_headers(content)

        # If no sections found, create one large section
        if not sections:
            if len(content.strip()) > 100:
                sections = [(page_title, content)]

        print(f"    Found {len(sections)} sections to process")

        for i, (header, section_content) in enumerate(sections):
            print(f"      Section {i}: '{header}' ({len(section_content)} chars)")

            if len(section_content.strip()) < 50:  # Skip very short sections
                print(f"        Skipping - too short ({len(section_content.strip())} chars)")
                continue

            # Clean content (basic markdown cleanup)
            clean_content = self._clean_markdown_content(section_content)

            print(f"        Cleaned content: {len(clean_content)} chars")

            if len(clean_content.strip()) < 50:
                print(f"        Skipping after cleaning - too short ({len(clean_content.strip())} chars)")
                continue

            chunk_id = hashlib.md5(f"{file_path}_{section}_{i}_{header}".encode()).hexdigest()[:12]

            # Determine chunk type based on content
            chunk_type = self._determine_chunk_type(header, clean_content, section)

            chunk = KcliDocChunk(
                id=chunk_id,
                source_url=f"https://github.com/karmab/kcli/blob/main/{file_path}",
                title=f"{page_title}: {header}" if header else page_title,
                content=clean_content,
                section=section,
                chunk_type=chunk_type,
                metadata={
                    "section_index": i,
                    "page_title": page_title,
                    "header": header,
                    "source": "kcli_github",
                    "file_path": file_path,
                },
                word_count=len(clean_content.split()),
                created_at=datetime.now().isoformat(),
            )

            chunks.append(chunk)
            print(f"        ✅ Created chunk: {chunk.title}")

        return chunks

    def _split_markdown_by_headers(self, content: str) -> List[tuple]:
        """Split Markdown content by headers (# ## ### etc.)"""

        # Find all markdown headers and their positions
        lines = content.split("\n")
        headers = []

        for i, line in enumerate(lines):
            # Match markdown headers (# ## ### etc.)
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                headers.append((level, title, i))

        if not headers:
            # No headers found, return entire content
            return [("", content)]

        sections = []

        for i, (level, title, line_num) in enumerate(headers):
            # Find content until next header of same or higher level
            start_line = line_num + 1

            if i + 1 < len(headers):
                end_line = headers[i + 1][2]
            else:
                end_line = len(lines)

            section_content = "\n".join(lines[start_line:end_line])
            sections.append((title, section_content))

        return sections

    def _clean_markdown_content(self, content: str) -> str:
        """Clean markdown content while preserving structure"""

        # Remove excessive whitespace but preserve structure
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)  # Multiple newlines
        content = re.sub(r"[ \t]+", " ", content)  # Multiple spaces

        # Clean up common markdown artifacts
        content = re.sub(r"```[a-zA-Z]*\n", "```\n", content)  # Clean code block language specifiers

        return content.strip()

    def _split_by_headers(self, html_content: str) -> List[tuple]:
        """Split HTML content by headers (h1, h2, h3, etc.)"""

        # Find all headers and their positions
        header_pattern = r"<h([1-6])[^>]*>(.*?)</h\1>"
        headers = []

        for match in re.finditer(header_pattern, html_content, re.IGNORECASE | re.DOTALL):
            level = int(match.group(1))
            title = self._clean_html_content(match.group(2))
            start_pos = match.end()
            headers.append((level, title, start_pos))

        if not headers:
            # No headers found, return entire content
            clean_content = self._clean_html_content(html_content)
            return [("", clean_content)]

        sections = []

        for i, (level, title, start_pos) in enumerate(headers):
            # Find content until next header of same or higher level
            if i + 1 < len(headers):
                next_start = headers[i + 1][2]
                content = html_content[start_pos : html_content.rfind("<h", 0, next_start)]
            else:
                content = html_content[start_pos:]

            sections.append((title, content))

        return sections

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content to extract plain text"""

        # Remove script and style elements
        html_content = re.sub(
            r"<script[^>]*>.*?</script>",
            "",
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        html_content = re.sub(
            r"<style[^>]*>.*?</style>",
            "",
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove HTML comments
        html_content = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)

        # Convert common HTML entities
        html_entities = {
            "&lt;": "<",
            "&gt;": ">",
            "&amp;": "&",
            "&quot;": '"',
            "&apos;": "'",
            "&nbsp;": " ",
            "&mdash;": "—",
            "&ndash;": "–",
        }

        for entity, char in html_entities.items():
            html_content = html_content.replace(entity, char)

        # Remove HTML tags but preserve some structure
        # Convert some tags to text equivalents
        html_content = re.sub(r"<br[^>]*>", "\n", html_content, flags=re.IGNORECASE)
        html_content = re.sub(r"<p[^>]*>", "\n\n", html_content, flags=re.IGNORECASE)
        html_content = re.sub(r"</p>", "", html_content, flags=re.IGNORECASE)
        html_content = re.sub(r"<li[^>]*>", "\n• ", html_content, flags=re.IGNORECASE)

        # Remove all remaining HTML tags
        html_content = re.sub(r"<[^>]+>", "", html_content)

        # Clean up whitespace
        html_content = re.sub(r"\n\s*\n\s*\n", "\n\n", html_content)  # Multiple newlines
        html_content = re.sub(r"[ \t]+", " ", html_content)  # Multiple spaces
        html_content = html_content.strip()

        return html_content

    def _determine_chunk_type(self, header: str, content: str, section: str) -> str:
        """Determine the type of documentation chunk"""

        header_lower = header.lower()
        content_lower = content.lower()

        # Check for examples
        if any(keyword in header_lower for keyword in ["example", "sample", "demo"]):
            return "example"

        if any(keyword in content_lower for keyword in ["kcli create", "kcli deploy", "$ kcli"]):
            return "example"

        # Check for tutorials/guides
        if any(keyword in header_lower for keyword in ["tutorial", "guide", "walkthrough", "getting started"]):
            return "tutorial"

        # Check for reference material
        if any(keyword in header_lower for keyword in ["reference", "api", "options", "parameters"]):
            return "reference"

        # Check for troubleshooting
        if any(keyword in header_lower for keyword in ["troubleshoot", "debug", "error", "problem"]):
            return "troubleshooting"

        # Default based on section
        if section in ["examples"]:
            return "example"
        elif section in ["installation", "usage"]:
            return "tutorial"
        elif section in ["troubleshooting"]:
            return "troubleshooting"
        else:
            return "overview"

    def process_documentation(self, fetched_docs: Dict[str, Any]) -> List[KcliDocChunk]:
        """Process fetched documentation into chunks"""

        print("📝 Processing kcli documentation into chunks...")

        all_chunks = []

        for section, doc_data in fetched_docs.items():
            print(f"  Processing {section}...")

            if doc_data["type"] == "markdown":
                chunks = self.parse_markdown_content(doc_data["content"], section, doc_data["relative_path"])
            else:
                # Handle other file types if needed
                print(f"    Skipping non-markdown file: {doc_data['type']}")
                continue

            all_chunks.extend(chunks)
            print(f"    Created {len(chunks)} chunks")

        self.chunks = all_chunks
        print(f"✅ Total chunks created: {len(all_chunks)}")

        return all_chunks

    def save_chunks(self) -> str:
        """Save chunks to JSON file for RAG integration"""

        output_file = self.output_dir / "chunks_kcli.json"

        chunks_data = [asdict(chunk) for chunk in self.chunks]

        with open(output_file, "w") as f:
            json.dump(chunks_data, f, indent=2, default=str)

        print(f"💾 Saved {len(chunks_data)} kcli chunks to {output_file}")

        # Update processing summary
        summary_file = self.output_dir / "processing_summary.json"

        if summary_file.exists():
            with open(summary_file, "r") as f:
                summary = json.load(f)
        else:
            summary = {
                "total_chunks": 0,
                "chunks_by_type": {},
                "total_words": 0,
                "output_files": {"by_type": {}},
            }

        # Add kcli chunks to summary
        kcli_chunks = len(chunks_data)
        kcli_words = sum(chunk["word_count"] for chunk in chunks_data)

        summary["chunks_by_type"]["kcli"] = kcli_chunks
        summary["total_chunks"] = summary.get("total_chunks", 0) + kcli_chunks
        summary["total_words"] = summary.get("total_words", 0) + kcli_words
        summary["output_files"]["by_type"]["kcli"] = str(output_file)
        summary["processed_at"] = datetime.now().isoformat()

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        return str(output_file)

    def generate_integration_summary(self) -> Dict[str, Any]:
        """Generate summary of kcli integration"""

        chunk_types = {}
        sections = {}

        for chunk in self.chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
            sections[chunk.section] = sections.get(chunk.section, 0) + 1

        return {
            "total_chunks": len(self.chunks),
            "total_words": sum(chunk.word_count for chunk in self.chunks),
            "chunk_types": chunk_types,
            "sections": sections,
            "integration_date": datetime.now().isoformat(),
            "source": "https://kcli.readthedocs.io/en/latest/",
            "status": "completed",
        }


def main():
    """Main execution"""

    print("🚀 Starting kcli documentation integration...")

    integrator = KcliDocumentationIntegrator()

    try:
        # Fetch documentation
        fetched_docs = integrator.fetch_documentation()

        if not fetched_docs:
            print("❌ No documentation fetched. Exiting.")
            return 1

        # Process into chunks
        chunks = integrator.process_documentation(fetched_docs)

        if not chunks:
            print("❌ No chunks created. Exiting.")
            return 1

        # Save chunks
        output_file = integrator.save_chunks()

        # Generate summary
        summary = integrator.generate_integration_summary()

        print("\n📊 Integration Summary:")
        print(f"  Total chunks: {summary['total_chunks']}")
        print(f"  Total words: {summary['total_words']:,}")
        print(f"  Chunk types: {summary['chunk_types']}")
        print(f"  Sections: {summary['sections']}")
        print(f"  Output file: {output_file}")

        print("\n✅ KCLI documentation integration completed successfully!")
        print("🤖 AI assistant now has access to comprehensive kcli documentation")

        return 0

    except Exception as e:
        print(f"❌ Integration failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        # Always cleanup temporary directory
        integrator.cleanup()


if __name__ == "__main__":
    exit(main())
