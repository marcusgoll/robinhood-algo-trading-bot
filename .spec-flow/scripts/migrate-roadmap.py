#!/usr/bin/env python3
"""
migrate-roadmap.py - Migrate roadmap.md features to GitHub Issues

This script parses the roadmap.md file and creates GitHub Issues for features
in the Next and Backlog sections (skipping Shipped features).
"""

import re
import subprocess
import sys
from typing import Dict, List, Optional

# ANSI colors - using ASCII for Windows compatibility
GREEN = '[32m'
YELLOW = '[33m'
BLUE = '[34m'
RED = '[31m'
NC = '[0m'  # No Color


def run_gh_command(args: List[str]) -> tuple[bool, str]:
    """Run gh CLI command and return success status and output."""
    try:
        result = subprocess.run(
            ['gh'] + args,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout.strip()
    except FileNotFoundError:
        print(f"[ERROR] gh CLI not found. Please install it first.")
        sys.exit(1)


def parse_roadmap(file_path: str) -> Dict[str, List[Dict]]:
    """Parse roadmap.md and extract features by section."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = {
        'Next': [],
        'Later': [],
        'Backlog': []
    }

    # Find each section
    for section_name in sections.keys():
        # Match section header and content until next ## header
        pattern = rf'^## {section_name}\s*$.*?(?=^## |\Z)'
        section_match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

        if not section_match:
            continue

        section_content = section_match.group(0)

        # Extract individual features (### slug)
        feature_pattern = r'^### ([\w-]+)\s*$(.*?)(?=^### |\Z)'
        features = re.finditer(feature_pattern, section_content, re.MULTILINE | re.DOTALL)

        for feature_match in features:
            slug = feature_match.group(1)
            feature_text = feature_match.group(2).strip()

            # Extract metadata
            title_match = re.search(r'^\s*-\s+\*\*Title\*\*:\s*(.+?)$', feature_text, re.MULTILINE)
            area_match = re.search(r'^\s*-\s+\*\*Area\*\*:\s*(\w+)', feature_text, re.MULTILINE)
            impact_match = re.search(r'^\s*-\s+\*\*Impact\*\*:\s*(\d+)', feature_text, re.MULTILINE)
            effort_match = re.search(r'^\s*-\s+\*\*Effort\*\*:\s*(\d+)', feature_text, re.MULTILINE)
            confidence_match = re.search(r'^\s*-\s+\*\*Confidence\*\*:\s*(0\.\d+)', feature_text, re.MULTILINE)
            score_match = re.search(r'\(Score:\s*([\d.]+)\)', feature_text)
            summary_match = re.search(r'^\s*-\s+\*\*Summary\*\*:\s*(.+?)$', feature_text, re.MULTILINE)

            # Extract requirements
            req_match = re.search(r'^\s*-\s+\*\*Requirements\*\*:\s*$(.*?)(?=^\s*-\s+\*\*[A-Z]|\Z)', feature_text, re.MULTILINE | re.DOTALL)
            requirements = []
            if req_match:
                req_text = req_match.group(1).strip()
                # Extract bullet points
                requirements = [line.strip() for line in req_text.split('\n') if line.strip().startswith('-')]

            feature = {
                'slug': slug,
                'title': title_match.group(1) if title_match else slug.replace('-', ' ').title(),
                'area': area_match.group(1).lower() if area_match else 'infra',
                'impact': int(impact_match.group(1)) if impact_match else 3,
                'effort': int(effort_match.group(1)) if effort_match else 3,
                'confidence': float(confidence_match.group(1)) if confidence_match else 0.7,
                'score': float(score_match.group(1)) if score_match else 0.0,
                'summary': summary_match.group(1) if summary_match else '',
                'requirements': requirements,
                'section': section_name
            }

            sections[section_name].append(feature)

    return sections


def create_github_issue(feature: Dict, dry_run: bool = False) -> tuple[bool, Optional[str]]:
    """Create a GitHub issue for a feature."""
    slug = feature['slug']
    title = feature['title']
    section = feature['section']

    # Build issue body
    body_parts = []

    # ICE frontmatter
    impact = feature['impact']
    effort = feature['effort']
    confidence = feature['confidence']
    score = feature['score'] or (impact * confidence / effort)

    body_parts.append(f"**Slug**: `{slug}`")
    body_parts.append(f"**ICE Score**: {score:.2f} (Impact: {impact}, Effort: {effort}, Confidence: {confidence})")
    body_parts.append("")

    if feature['summary']:
        body_parts.append(f"**Summary**: {feature['summary']}")
        body_parts.append("")

    # Requirements
    if feature['requirements']:
        body_parts.append("## Requirements")
        body_parts.append("")
        for req in feature['requirements']:
            body_parts.append(req)
        body_parts.append("")
    else:
        body_parts.append("## Requirements")
        body_parts.append("")
        body_parts.append("- [ ] To be defined")
        body_parts.append("")

    # Check for spec directory
    try:
        result = subprocess.run(
            ['find', 'specs', '-type', 'd', '-name', f'*{slug}*'],
            capture_output=True,
            text=True,
            check=False
        )
        spec_dirs = [d for d in result.stdout.strip().split('\n') if d]
        if spec_dirs:
            body_parts.append("## Spec")
            body_parts.append("")
            body_parts.append(f"See: `{spec_dirs[0]}/spec.md`")
            body_parts.append("")
    except:
        pass

    body_parts.append("---")
    body_parts.append("*Migrated from roadmap.md*")

    body = '\n'.join(body_parts)

    # Build labels
    area = feature['area']
    labels = [
        'type:feature',
        f'status:{section.lower()}',
        f'area:{area}'
    ]

    # Add size label based on effort
    if effort == 1:
        labels.append('size:small')
    elif effort <= 3:
        labels.append('size:medium')
    elif effort == 4:
        labels.append('size:large')
    else:
        labels.append('size:xl')

    if dry_run:
        print(f"{BLUE}[DRY RUN]{NC} Would create: {title}")
        print(f"  Labels: {', '.join(labels)}")
        print(f"  Score: {score:.2f}")
        return True, None

    # Create issue using gh CLI
    args = [
        'issue', 'create',
        '--title', title,
        '--body', body,
        '--label', ','.join(labels)
    ]

    success, output = run_gh_command(args)

    if success:
        # Extract issue number from URL
        issue_number = output.split('/')[-1] if '/' in output else None
        return True, issue_number
    else:
        return False, None


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate roadmap.md to GitHub Issues')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without creating')
    args = parser.parse_args()

    # Check gh auth
    success, _ = run_gh_command(['auth', 'status'])
    if not success:
        print(f"[ERROR] GitHub CLI not authenticated")
        print("\nPlease run: gh auth login")
        sys.exit(1)

    print(f"{GREEN}OK{NC} GitHub CLI authenticated")

    # Parse roadmap
    roadmap_file = '.spec-flow/memory/roadmap.md'
    try:
        sections = parse_roadmap(roadmap_file)
    except FileNotFoundError:
        print(f"[ERROR] Roadmap file not found: {roadmap_file}")
        sys.exit(1)

    print(f"[OK] Found roadmap: {roadmap_file}")
    print()

    if args.dry_run:
        print(f"{YELLOW}DRY RUN MODE - No issues will be created{NC}")
        print()

    print("=" * 60)
    print("Migrating Roadmap to GitHub Issues")
    print("=" * 60)
    print()

    # Process each section
    total = 0
    created = 0
    skipped = 0
    errors = 0

    for section_name in ['Next', 'Later', 'Backlog']:
        features = sections[section_name]
        if not features:
            continue

        print(f"\n{BLUE}## {section_name}{NC} ({len(features)} features)")
        print()

        for feature in features:
            total += 1
            slug = feature['slug']
            title = feature['title']

            # Check if issue already exists
            check_args = ['issue', 'list', '--search', f'{slug} in:title', '--json', 'number', '--jq', 'length']
            success, count = run_gh_command(check_args)

            if success and count and int(count) > 0:
                print(f"{YELLOW}SKIP{NC} Skipped: {title} (already exists)")
                skipped += 1
                continue

            # Create issue
            success, issue_num = create_github_issue(feature, dry_run=args.dry_run)

            if success:
                if args.dry_run:
                    created += 1
                else:
                    print(f"{GREEN}OK{NC} Created #{issue_num}: {title}")
                    created += 1
            else:
                print(f"{RED}X{NC} Failed: {title}")
                errors += 1

    print()
    print("=" * 60)
    print(f"{GREEN}MIGRATION SUMMARY{NC}")
    print("=" * 60)
    print(f"Total features: {total}")
    print(f"Created: {created}")
    print(f"Skipped (existing): {skipped}")
    print(f"Errors: {errors}")
    print()

    if args.dry_run:
        print("Run without --dry-run to create issues")
    elif created > 0:
        print(f"View issues: gh issue list --label type:feature")

    sys.exit(0 if errors == 0 else 1)


if __name__ == '__main__':
    main()
