#!/usr/bin/env python3
"""
Qubinode Navigator Log Analysis CLI

Command-line interface for automated log analysis and error resolution.
Provides intelligent analysis of deployment logs with AI-powered recommendations.
"""

import sys
import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.log_analyzer import LogAnalyzer


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def print_analysis_summary(report: Dict[str, Any]):
    """Print formatted analysis summary"""
    print("\n" + "="*80)
    print("🔍 QUBINODE NAVIGATOR LOG ANALYSIS REPORT")
    print("="*80)
    
    # Session Summary
    session = report['session_summary']
    print(f"\n📋 DEPLOYMENT SESSION")
    print(f"   Session ID: {session['session_id']}")
    print(f"   Playbook: {session['playbook']}")
    print(f"   Duration: {session.get('end_time', 'In Progress')}")
    print(f"   Tasks: {session['successful_tasks']}/{session['total_tasks']} successful")
    print(f"   Failure Rate: {session['performance_metrics'].get('failure_rate', 0):.1f}%")
    
    # Error Analysis
    error_analysis = report['error_analysis']
    print(f"\n🚨 ERROR ANALYSIS")
    print(f"   Patterns Identified: {error_analysis['patterns_identified']}")
    
    if error_analysis['pattern_details']:
        print("   Error Patterns:")
        for pattern in error_analysis['pattern_details']:
            severity_icon = {
                'critical': '🔴',
                'high': '🟠', 
                'medium': '🟡',
                'low': '🟢'
            }.get(pattern['severity'], '⚪')
            
            print(f"     {severity_icon} {pattern['description']}")
            print(f"        Severity: {pattern['severity'].upper()}")
            print(f"        Frequency: {pattern['frequency']}")
    
    # Recommendations
    recommendations = report['recommendations']
    print(f"\n💡 RESOLUTION RECOMMENDATIONS ({len(recommendations)} found)")
    
    for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
        confidence_icon = "🎯" if rec['confidence'] > 0.8 else "📋" if rec['confidence'] > 0.6 else "⚠️"
        
        print(f"\n   {confidence_icon} Recommendation #{i}")
        print(f"      Type: {rec['resolution_type'].upper()}")
        print(f"      Confidence: {rec['confidence']:.1%}")
        print(f"      Estimated Time: {rec['estimated_time']}")
        print(f"      Risk Level: {rec['risk_level'].upper()}")
        print(f"      Steps:")
        for step in rec['steps'][:3]:  # Show first 3 steps
            print(f"        • {step}")
        if len(rec['steps']) > 3:
            print(f"        ... and {len(rec['steps']) - 3} more steps")
    
    # AI Analysis
    if report.get('ai_analysis'):
        print(f"\n🤖 AI ANALYSIS")
        ai_text = report['ai_analysis']
        # Truncate long AI responses
        if len(ai_text) > 500:
            ai_text = ai_text[:500] + "..."
        print(f"   {ai_text}")
    
    # Next Steps
    next_steps = report.get('next_steps', [])
    print(f"\n🎯 NEXT STEPS")
    for i, step in enumerate(next_steps, 1):
        print(f"   {i}. {step}")
    
    # Prevention Measures
    prevention = report.get('prevention_measures', [])
    print(f"\n🛡️ PREVENTION MEASURES")
    for measure in prevention[:3]:  # Show top 3
        print(f"   • {measure}")
    
    print("\n" + "="*80)


def print_json_report(report: Dict[str, Any]):
    """Print report in JSON format"""
    print(json.dumps(report, indent=2, default=str))


def print_error_patterns(analyzer: LogAnalyzer):
    """Print known error patterns"""
    print("\n" + "="*60)
    print("🔍 KNOWN ERROR PATTERNS")
    print("="*60)
    
    for pattern_id, pattern in analyzer.error_patterns.items():
        severity_icon = {
            'critical': '🔴',
            'high': '🟠', 
            'medium': '🟡',
            'low': '🟢'
        }.get(pattern.severity, '⚪')
        
        print(f"\n{severity_icon} {pattern.pattern_id}")
        print(f"   Type: {pattern.error_type}")
        print(f"   Severity: {pattern.severity.upper()}")
        print(f"   Description: {pattern.description}")
        print(f"   Frequency: {pattern.frequency}")
        print(f"   Pattern: {pattern.pattern_regex}")


async def analyze_logs_command(args):
    """Execute log analysis command"""
    # Initialize analyzer
    analyzer = LogAnalyzer(ai_assistant_url=args.ai_url)
    
    # Check if log file exists
    if not Path(args.log_file).exists():
        print(f"❌ Error: Log file not found: {args.log_file}")
        return 1
    
    print(f"🔍 Analyzing deployment logs: {args.log_file}")
    
    try:
        # Run analysis
        report = await analyzer.analyze_log_file(args.log_file)
        
        if 'error' in report:
            print(f"❌ Analysis failed: {report['error']}")
            return 1
        
        # Output results
        if args.format == 'json':
            print_json_report(report)
        else:
            print_analysis_summary(report)
        
        # Save report if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n📄 Report saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1


def list_patterns_command(args):
    """Execute list patterns command"""
    analyzer = LogAnalyzer(ai_assistant_url=args.ai_url)
    print_error_patterns(analyzer)
    return 0


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Automated Log Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze deployment logs
  python3 analyze_logs.py analyze /tmp/qubinode_deployment.log
  
  # Analyze with JSON output
  python3 analyze_logs.py analyze /tmp/qubinode_deployment.log --format json
  
  # Save analysis report
  python3 analyze_logs.py analyze /tmp/qubinode_deployment.log --output report.json
  
  # List known error patterns
  python3 analyze_logs.py patterns
        """
    )
    
    parser.add_argument(
        '--ai-url',
        default='http://localhost:8080',
        help='AI Assistant service URL (default: http://localhost:8080)'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze deployment log file'
    )
    analyze_parser.add_argument(
        'log_file',
        help='Path to deployment log file'
    )
    analyze_parser.add_argument(
        '--format',
        choices=['summary', 'json'],
        default='summary',
        help='Output format (default: summary)'
    )
    analyze_parser.add_argument(
        '--output',
        help='Save analysis report to file'
    )
    
    # Patterns command
    patterns_parser = subparsers.add_parser(
        'patterns',
        help='List known error patterns'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(args.log_level)
    
    try:
        if args.command == 'analyze':
            return await analyze_logs_command(args)
        elif args.command == 'patterns':
            return list_patterns_command(args)
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
