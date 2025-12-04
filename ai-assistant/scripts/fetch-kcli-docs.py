#!/usr/bin/env python3
"""
kcli Documentation Fetcher for RAG Integration
Fetches and processes kcli documentation from https://kcli.readthedocs.io
for AI Assistant RAG system integration.
"""

import sys
import requests
from pathlib import Path
from datetime import datetime
import json
import hashlib


class KcliDocsFetcher:
    """Fetches and prepares kcli documentation for RAG ingestion"""

    def __init__(self, output_dir: str = "/root/qubinode_navigator/ai-assistant/data/kcli-docs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # kcli documentation sections to fetch
        self.doc_urls = {
            "index": "https://raw.githubusercontent.com/karmab/kcli/main/README.md",
            "installation": "https://raw.githubusercontent.com/karmab/kcli/main/doc/installation.md",
            "usage": "https://raw.githubusercontent.com/karmab/kcli/main/doc/usage.md",
            "plans": "https://raw.githubusercontent.com/karmab/kcli/main/doc/plans.md",
            "vms": "https://raw.githubusercontent.com/karmab/kcli/main/doc/vms.md",
            "networks": "https://raw.githubusercontent.com/karmab/kcli/main/doc/networks.md",
            "storage": "https://raw.githubusercontent.com/karmab/kcli/main/doc/storage.md",
            "examples": "https://raw.githubusercontent.com/karmab/kcli/main/doc/examples.md",
        }

        self.metadata = {
            "source": "kcli",
            "source_url": "https://kcli.readthedocs.io",
            "github_repo": "https://github.com/karmab/kcli",
            "fetched_at": datetime.now().isoformat(),
            "version": "99.0",  # Current installed version
            "purpose": "VM provisioning and lifecycle management for Qubinode Navigator",
        }

    def fetch_documentation(self):
        """Fetch all kcli documentation from GitHub"""
        print("📥 Fetching kcli documentation from GitHub...")

        docs_fetched = []

        for doc_name, url in self.doc_urls.items():
            print(f"   Fetching {doc_name}...")
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    content = response.text

                    # Save raw documentation
                    output_file = self.output_dir / f"{doc_name}.md"
                    output_file.write_text(content)

                    # Create metadata
                    doc_metadata = {
                        **self.metadata,
                        "doc_name": doc_name,
                        "doc_url": url,
                        "word_count": len(content.split()),
                        "char_count": len(content),
                        "doc_hash": hashlib.md5(content.encode()).hexdigest(),
                    }

                    docs_fetched.append(
                        {
                            "name": doc_name,
                            "file": str(output_file),
                            "metadata": doc_metadata,
                        }
                    )

                    print(f"   ✅ {doc_name}: {len(content.split())} words")
                else:
                    print(f"   ⚠️ {doc_name}: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ {doc_name}: {str(e)}")

        # Save fetched docs index
        index_file = self.output_dir / "index.json"
        index_file.write_text(
            json.dumps(
                {
                    "metadata": self.metadata,
                    "documents": docs_fetched,
                    "total_docs": len(docs_fetched),
                },
                indent=2,
            )
        )

        print(f"\n✅ Fetched {len(docs_fetched)} documentation files")
        print(f"📁 Saved to: {self.output_dir}")

        return docs_fetched

    def prepare_for_rag(self, docs_fetched):
        """Prepare fetched docs for RAG ingestion"""
        print("\n📝 Preparing documentation for RAG ingestion...")

        rag_chunks = []

        for doc in docs_fetched:
            doc_file = Path(doc["file"])
            content = doc_file.read_text()

            # Split content into chunks (by headers)
            chunks = self._split_by_headers(content, doc["name"])

            for chunk in chunks:
                rag_chunk = {
                    "id": hashlib.md5(f"{doc['name']}-{chunk['title']}".encode()).hexdigest(),
                    "source": "kcli",
                    "doc_name": doc["name"],
                    "title": chunk["title"],
                    "content": chunk["content"],
                    "metadata": {
                        **doc["metadata"],
                        "section": chunk["title"],
                        "chunk_type": "kcli-documentation",
                    },
                    "word_count": len(chunk["content"].split()),
                }
                rag_chunks.append(rag_chunk)

        # Save RAG-ready chunks
        rag_file = self.output_dir / "rag-chunks.json"
        rag_file.write_text(json.dumps(rag_chunks, indent=2))

        print(f"✅ Created {len(rag_chunks)} RAG chunks")
        print(f"📁 Saved to: {rag_file}")

        # Create summary
        total_words = sum(chunk["word_count"] for chunk in rag_chunks)
        print("\n📊 Summary:")
        print(f"   Total chunks: {len(rag_chunks)}")
        print(f"   Total words: {total_words:,}")
        print(f"   Avg words per chunk: {total_words // len(rag_chunks) if rag_chunks else 0}")

        return rag_chunks

    def _split_by_headers(self, content: str, doc_name: str):
        """Split markdown content by headers"""
        chunks = []
        current_title = doc_name
        current_content = []

        for line in content.split("\n"):
            if line.startswith("#"):
                # Save previous chunk
                if current_content:
                    chunks.append(
                        {
                            "title": current_title,
                            "content": "\n".join(current_content).strip(),
                        }
                    )
                    current_content = []

                # Start new chunk
                current_title = line.lstrip("#").strip()
            else:
                current_content.append(line)

        # Save last chunk
        if current_content:
            chunks.append({"title": current_title, "content": "\n".join(current_content).strip()})

        return chunks


def main():
    """Main execution"""
    print("=" * 70)
    print("kcli Documentation Fetcher for AI Assistant RAG Integration")
    print("=" * 70)
    print()

    fetcher = KcliDocsFetcher()

    # Fetch documentation
    docs_fetched = fetcher.fetch_documentation()

    # Prepare for RAG
    if docs_fetched:
        fetcher.prepare_for_rag(docs_fetched)

        print("\n🎯 Next Steps:")
        print("   1. Review fetched documentation in ai-assistant/data/kcli-docs/")
        print("   2. Ingest RAG chunks into AI Assistant knowledge base")
        print("   3. Test AI Assistant's kcli guidance capabilities")
        print()
        return 0
    else:
        print("\n❌ No documentation fetched. Check network connection and URLs.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
