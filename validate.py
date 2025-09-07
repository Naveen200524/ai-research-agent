#!/usr/bin/env python3
"""
Production Validation Script for AI Research Agent
"""

import os
import ast
import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple

class CodebaseValidator:
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.errors = []
        self.warnings = []
        self.valid_files = []

    def validate_python_syntax(self, filepath: Path) -> Tuple[bool, str]:
        """Validate Python file syntax"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()

            # Check for truncation indicators
            truncation_patterns = [
                '...',
                '# rest of',
                '# TODO:',
                '# continue',
                '# more code',
                '# remaining',
                'pass  # implement'
            ]

            for pattern in truncation_patterns:
                if pattern in source.lower():
                    return False, f"Possible truncation: '{pattern}' found"

            # Parse AST
            ast.parse(source)

            # Check for complete class/function definitions
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.body or (len(node.body) == 1 and isinstance(node.body[0], ast.Pass)):
                        return False, f"Empty function: {node.name}"

            return True, "Valid"

        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Error: {e}"

    def validate_imports(self, filepath: Path) -> List[str]:
        """Check if all imports are valid"""
        issues = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        # Check if module should be in requirements
                        if not module_name.startswith(('backend', 'core', 'api', 'models', 'utils')):
                            # This is an external import
                            issues.append(f"External import: {module_name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module and not node.module.startswith('.'):
                        if not node.module.startswith(('backend', 'core', 'api', 'models', 'utils')):
                            issues.append(f"External import: {node.module}")

        except Exception as e:
            issues.append(f"Import check failed: {e}")

        return issues

    def validate_requirements(self) -> Tuple[bool, List[str]]:
        """Validate requirements.txt"""
        req_file = self.root / 'requirements.txt'
        if not req_file.exists():
            return False, ["requirements.txt not found"]

        required_packages = [
            'fastapi',
            'uvicorn',
            'streamlit',
            'duckduckgo-search',
            'google-generativeai',
            'openai',
            'chromadb',
            'trafilatura',
            'playwright',
            'reportlab',
            'aiohttp',
            'pydantic'
        ]

        with open(req_file, 'r') as f:
            content = f.read().lower()

        missing = []
        for package in required_packages:
            if package not in content:
                missing.append(package)

        return len(missing) == 0, missing

    def validate_docker_files(self) -> Dict[str, bool]:
        """Validate Docker configuration"""
        results = {}

        # Check docker-compose.yml
        compose_file = self.root / 'docker-compose.yml'
        if compose_file.exists():
            try:
                with open(compose_file, 'r') as f:
                    content = f.read()
                    results['docker-compose'] = (
                        'services:' in content and
                        'backend:' in content and
                        'frontend:' in content
                    )
            except:
                results['docker-compose'] = False
        else:
            results['docker-compose'] = False

        # Check Dockerfiles
        for dockerfile in ['Dockerfile.backend', 'Dockerfile.frontend']:
            df_path = self.root / dockerfile
            if df_path.exists():
                with open(df_path, 'r') as f:
                    content = f.read()
                    results[dockerfile] = (
                        'FROM python:' in content and
                        'WORKDIR' in content and
                        'CMD' in content
                    )
            else:
                results[dockerfile] = False

        return results

    def validate_api_endpoints(self) -> Dict[str, bool]:
        """Check if all required API endpoints exist"""
        routes_file = self.root / 'backend' / 'api' / 'routes.py'
        if not routes_file.exists():
            return {}

        with open(routes_file, 'r') as f:
            content = f.read()

        endpoints = {
            'POST /research': '@router.post("/research"' in content,
            'GET /status': '@router.get("/status' in content,
            'GET /research': '@router.get("/research' in content,
            'GET /export': '@router.get("/export' in content,
        }

        return endpoints

    def run_full_validation(self) -> Dict:
        """Run complete validation suite"""
        report = {
            'valid': True,
            'python_files': {},
            'requirements': {},
            'docker': {},
            'api_endpoints': {},
            'structure': {},
            'errors': [],
            'warnings': []
        }

        # Check directory structure
        required_dirs = [
            'backend/api',
            'backend/core',
            'backend/models',
            'backend/utils',
            'frontend',
            'data'
        ]

        for dir_path in required_dirs:
            full_path = self.root / dir_path
            report['structure'][dir_path] = full_path.exists()
            if not full_path.exists():
                report['errors'].append(f"Missing directory: {dir_path}")
                report['valid'] = False

        # Validate Python files
        for py_file in self.root.rglob('*.py'):
            if '__pycache__' not in str(py_file):
                relative_path = py_file.relative_to(self.root)
                is_valid, message = self.validate_python_syntax(py_file)

                report['python_files'][str(relative_path)] = {
                    'valid': is_valid,
                    'message': message
                }

                if not is_valid:
                    report['errors'].append(f"{relative_path}: {message}")
                    report['valid'] = False

                # Check imports
                import_issues = self.validate_imports(py_file)
                if import_issues:
                    report['warnings'].extend([f"{relative_path}: {issue}" for issue in import_issues])

        # Validate requirements
        req_valid, missing = self.validate_requirements()
        report['requirements']['valid'] = req_valid
        report['requirements']['missing'] = missing
        if not req_valid:
            report['errors'].append(f"Missing packages in requirements.txt: {missing}")
            report['valid'] = False

        # Validate Docker files
        report['docker'] = self.validate_docker_files()
        for file, valid in report['docker'].items():
            if not valid:
                report['errors'].append(f"Invalid or missing: {file}")
                report['valid'] = False

        # Validate API endpoints
        report['api_endpoints'] = self.validate_api_endpoints()
        for endpoint, exists in report['api_endpoints'].items():
            if not exists:
                report['errors'].append(f"Missing API endpoint: {endpoint}")
                report['valid'] = False

        return report

def main():
    """Run validation and generate report"""
    validator = CodebaseValidator('.')
    report = validator.run_full_validation()

    # Print summary
    print("=" * 60)
    print("AI RESEARCH AGENT - PRODUCTION VALIDATION REPORT")
    print("=" * 60)

    if report['valid']:
        print("✅ CODEBASE IS PRODUCTION READY!")
    else:
        print("❌ CODEBASE HAS ISSUES!")

    print(f"\nPython Files Validated: {len(report['python_files'])}")
    print(f"Errors Found: {len(report['errors'])}")
    print(f"Warnings Found: {len(report['warnings'])}")

    if report['errors']:
        print("\n🔴 ERRORS:")
        for error in report['errors']:
            print(f"  - {error}")

    if report['warnings']:
        print("\n🟡 WARNINGS:")
        for warning in report['warnings'][:10]:  # Show first 10
            print(f"  - {warning}")

    # Generate detailed report
    with open('validation_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("\n📊 Detailed report saved to: validation_report.json")

    # Exit with appropriate code
    sys.exit(0 if report['valid'] else 1)

if __name__ == "__main__":
    main()
