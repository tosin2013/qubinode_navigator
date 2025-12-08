#!/usr/bin/env python3
"""
RAG CLI Tool - Simple command-line interface for RAG operations
Designed to be called by MCP tools for reliable RAG interactions

Usage:
    rag-cli.py ingest <file> [--category=<cat>] [--tags=<tags>] [--auto-approve]
    rag-cli.py query <query> [--max-results=<n>]
    rag-cli.py stats
    rag-cli.py list
    rag-cli.py health
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add src directory to path
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir / "src"))


def get_rag_service():
    """Get or create RAG service instance.

    Uses Qdrant RAG service (current implementation per ADR-0027/ADR-0049).
    Target: PgVector per ADR-0049 Phase 1.
    """
    try:
        from qdrant_rag_service import QdrantRAGService

        data_dir = os.getenv("RAG_DATA_DIR", "/app/data")
        return QdrantRAGService(data_dir)
    except ImportError:
        return None


def cmd_ingest(args):
    """Ingest a document into RAG."""
    # Resolve path to absolute for consistent handling
    file_path = Path(args.file).resolve()

    if not file_path.exists():
        print(json.dumps({"status": "error", "message": f"File not found: {file_path}"}))
        return 1

    if file_path.is_dir():
        print(json.dumps({"status": "error", "message": f"Path is a directory, not a file: {file_path}"}))
        return 1

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Failed to read file: {e}"}))
        return 1

    # Process document into chunks
    chunks = []
    if file_path.suffix == ".md":
        # Split markdown by headers
        lines = content.split("\n")
        current_title = file_path.stem
        current_content = []

        for line in lines:
            if line.startswith("#"):
                if current_content:
                    chunks.append({"title": current_title, "content": "\n".join(current_content).strip()})
                current_title = line.strip("#").strip()
                current_content = [line]
            else:
                current_content.append(line)

        if current_content:
            chunks.append({"title": current_title, "content": "\n".join(current_content).strip()})
    else:
        # Single chunk for non-markdown
        chunks.append({"title": file_path.stem, "content": content})

    # Filter out empty/short chunks
    chunks = [c for c in chunks if len(c["content"].strip()) >= 50]

    if not chunks:
        print(json.dumps({"status": "error", "message": "No valid content found in document"}))
        return 1

    # Calculate quality score
    total_score = 0
    for chunk in chunks:
        score = 1.0
        if len(chunk["content"]) < 100:
            score -= 0.2
        if "```" in chunk["content"]:
            score += 0.1
        technical_terms = ["kvm", "rhel", "centos", "ansible", "podman", "docker", "vm", "kcli"]
        if any(term in chunk["content"].lower() for term in technical_terms):
            score += 0.1
        if any(p in chunk["content"].lower() for p in ["step 1", "1.", "first,", "then,"]):
            score += 0.1
        total_score += min(1.0, max(0.0, score))

    quality_score = total_score / len(chunks)

    # Output result
    result = {
        "status": "approved" if args.auto_approve or quality_score >= 0.8 else "pending_review",
        "file": str(file_path),
        "chunks_processed": len(chunks),
        "category": args.category or "general",
        "tags": args.tags.split(",") if args.tags else [],
        "quality_score": round(quality_score, 2),
        "chunks": [{"title": c["title"], "words": len(c["content"].split())} for c in chunks],
    }

    print(json.dumps(result, indent=2))
    return 0


def cmd_query(args):
    """Query RAG for documents."""
    rag = get_rag_service()

    if rag is None:
        print(json.dumps({"status": "error", "message": "RAG service not available. Install qdrant-client."}))
        return 1

    try:
        import asyncio

        async def do_query():
            # Initialize if needed
            if hasattr(rag, "initialize"):
                await rag.initialize()

            results = await rag.search_documents(query=args.query, n_results=args.max_results)
            return results

        results = asyncio.run(do_query())

        output = {"status": "success", "query": args.query, "total_results": len(results), "results": []}

        for r in results:
            output["results"].append(
                {"title": getattr(r, "title", "Unknown"), "content": getattr(r, "content", str(r))[:500], "score": round(getattr(r, "score", 0.0), 3), "source": getattr(r, "source_file", "Unknown")}
            )

        print(json.dumps(output, indent=2))
        return 0

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 1


def cmd_stats(args):
    """Get RAG statistics."""
    # Check contributions directory
    data_dir = Path(os.getenv("RAG_DATA_DIR", "/app/data"))
    contributions_dir = data_dir / "contributions"

    stats = {
        "status": "success",
        "data_directory": str(data_dir),
        "contributions_directory": str(contributions_dir),
        "contributions_exist": contributions_dir.exists(),
        "total_contributions": 0,
        "pending_reviews": 0,
        "categories": {},
    }

    if contributions_dir.exists():
        metadata_files = list(contributions_dir.glob("*_metadata.json"))
        review_files = list(contributions_dir.glob("*_review.json"))

        stats["total_contributions"] = len(metadata_files)
        stats["pending_reviews"] = len(review_files)

        for mf in metadata_files:
            try:
                with open(mf) as f:
                    data = json.load(f)
                    cat = data.get("metadata", {}).get("category", "unknown")
                    stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
            except Exception:
                pass

    # Check RAG service
    rag = get_rag_service()
    stats["rag_service_available"] = rag is not None

    print(json.dumps(stats, indent=2))
    return 0


def cmd_list(args):
    """List RAG contributions."""
    data_dir = Path(os.getenv("RAG_DATA_DIR", "/app/data"))
    contributions_dir = data_dir / "contributions"

    result = {"status": "success", "contributions": []}

    if contributions_dir.exists():
        for mf in sorted(contributions_dir.glob("*_metadata.json"), reverse=True):
            try:
                with open(mf) as f:
                    data = json.load(f)
                    result["contributions"].append(
                        {
                            "document_id": data.get("document_id"),
                            "filename": data.get("original_filename"),
                            "submitted_at": data.get("submitted_at"),
                            "category": data.get("metadata", {}).get("category"),
                        }
                    )
            except Exception:
                pass

    result["total"] = len(result["contributions"])
    print(json.dumps(result, indent=2))
    return 0


def cmd_batch_ingest(args):
    """Batch ingest multiple documents into RAG using glob patterns."""
    import glob as glob_module

    pattern = args.pattern
    base_path = Path(args.base_path).resolve() if args.base_path else Path.cwd()

    # Support both glob patterns and directory paths
    if Path(pattern).is_dir():
        # If pattern is a directory, find all markdown files
        files = list(Path(pattern).resolve().glob("**/*.md" if args.recursive else "*.md"))
    else:
        # Use glob pattern
        if args.recursive and "**" not in pattern:
            # Make pattern recursive if flag set but no ** in pattern
            pattern = f"**/{pattern}"
        files = [Path(f).resolve() for f in glob_module.glob(str(base_path / pattern), recursive=args.recursive)]

    if not files:
        print(json.dumps({"status": "error", "message": f"No files found matching pattern: {pattern}"}))
        return 1

    # Filter to only files (not directories)
    files = [f for f in files if f.is_file()]

    results = {
        "status": "success",
        "pattern": pattern,
        "base_path": str(base_path),
        "total_files": len(files),
        "processed": 0,
        "approved": 0,
        "pending": 0,
        "errors": 0,
        "files": [],
    }

    for file_path in sorted(files):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            results["errors"] += 1
            results["files"].append({"file": str(file_path), "status": "error", "message": str(e)})
            continue

        # Process document into chunks (same logic as cmd_ingest)
        chunks = []
        if file_path.suffix == ".md":
            lines = content.split("\n")
            current_title = file_path.stem
            current_content = []

            for line in lines:
                if line.startswith("#"):
                    if current_content:
                        chunks.append({"title": current_title, "content": "\n".join(current_content).strip()})
                    current_title = line.strip("#").strip()
                    current_content = [line]
                else:
                    current_content.append(line)

            if current_content:
                chunks.append({"title": current_title, "content": "\n".join(current_content).strip()})
        else:
            chunks.append({"title": file_path.stem, "content": content})

        # Filter out empty/short chunks
        chunks = [c for c in chunks if len(c["content"].strip()) >= 50]

        if not chunks:
            results["files"].append({"file": str(file_path), "status": "skipped", "message": "No valid content"})
            continue

        # Calculate quality score
        total_score = 0
        for chunk in chunks:
            score = 1.0
            if len(chunk["content"]) < 100:
                score -= 0.2
            if "```" in chunk["content"]:
                score += 0.1
            technical_terms = ["kvm", "rhel", "centos", "ansible", "podman", "docker", "vm", "kcli"]
            if any(term in chunk["content"].lower() for term in technical_terms):
                score += 0.1
            if any(p in chunk["content"].lower() for p in ["step 1", "1.", "first,", "then,"]):
                score += 0.1
            total_score += min(1.0, max(0.0, score))

        quality_score = total_score / len(chunks)
        status = "approved" if args.auto_approve or quality_score >= 0.8 else "pending_review"

        results["processed"] += 1
        if status == "approved":
            results["approved"] += 1
        else:
            results["pending"] += 1

        results["files"].append(
            {
                "file": str(file_path),
                "status": status,
                "chunks": len(chunks),
                "quality_score": round(quality_score, 2),
            }
        )

    print(json.dumps(results, indent=2))
    return 0 if results["errors"] == 0 else 1


def cmd_health(args):
    """Check RAG system health."""
    health = {"status": "healthy", "checks": {}}

    # Check data directory
    data_dir = Path(os.getenv("RAG_DATA_DIR", "/app/data"))
    health["checks"]["data_directory"] = {"path": str(data_dir), "exists": data_dir.exists(), "writable": os.access(data_dir, os.W_OK) if data_dir.exists() else False}

    # Check RAG service
    rag = get_rag_service()
    health["checks"]["rag_service"] = {"available": rag is not None, "type": type(rag).__name__ if rag else None}

    # Check embedding service
    embedding_url = os.getenv("QUBINODE_EMBEDDING_SERVICE_URL", "http://localhost:8891")
    health["checks"]["embedding_service"] = {"url": embedding_url, "configured": True}

    # Overall status
    if not health["checks"]["rag_service"]["available"]:
        health["status"] = "degraded"
    if not health["checks"]["data_directory"]["exists"]:
        health["status"] = "unhealthy"

    print(json.dumps(health, indent=2))
    return 0 if health["status"] == "healthy" else 1


def main():
    parser = argparse.ArgumentParser(
        description="RAG CLI Tool for Qubinode AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ingest /path/to/doc.md --category=deployment --tags=vm,kcli
  %(prog)s query "How to deploy a VM with kcli?" --max-results=5
  %(prog)s stats
  %(prog)s list
  %(prog)s health
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a document into RAG")
    ingest_parser.add_argument("file", help="Path to the document file")
    ingest_parser.add_argument("--category", default="general", help="Document category")
    ingest_parser.add_argument("--tags", help="Comma-separated tags")
    ingest_parser.add_argument("--auto-approve", action="store_true", help="Auto-approve document")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query RAG for documents")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument("--max-results", type=int, default=5, help="Maximum results")

    # Batch ingest command
    batch_parser = subparsers.add_parser("batch-ingest", help="Batch ingest multiple documents using glob patterns")
    batch_parser.add_argument("pattern", help="Glob pattern or directory path (e.g., 'docs/adrs/*.md' or 'adr-*.md')")
    batch_parser.add_argument("--base-path", help="Base path for glob pattern (default: current directory)")
    batch_parser.add_argument("--category", default="general", help="Document category for all files")
    batch_parser.add_argument("--tags", help="Comma-separated tags for all files")
    batch_parser.add_argument("--auto-approve", action="store_true", help="Auto-approve all documents")
    batch_parser.add_argument("--recursive", "-r", action="store_true", help="Recursively search directories")

    # Stats command
    subparsers.add_parser("stats", help="Get RAG statistics")

    # List command
    subparsers.add_parser("list", help="List RAG contributions")

    # Health command
    subparsers.add_parser("health", help="Check RAG system health")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    commands = {"ingest": cmd_ingest, "query": cmd_query, "batch-ingest": cmd_batch_ingest, "stats": cmd_stats, "list": cmd_list, "health": cmd_health}

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
