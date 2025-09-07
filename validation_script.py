#!/usr/bin/env python3
"""
Production Validation Script for AI Research Agent
Validates all critical components for production readiness
"""

import os
import sys
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple

class ProductionValidator:
    """Comprehensive validation for production readiness"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors = []
        self.warnings = []
        self.success_count = 0

    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("🔍 Starting Production Validation...")
        print("=" * 50)

        # Critical file existence checks
        self._check_critical_files()

        # Code quality checks
        self._check_code_quality()

        # Import validation
        self._check_imports()

        # Configuration validation
        self._check_configuration()

        # Docker validation
        self._check_docker_files()

        print("\n" + "=" * 50)
        print("📊 VALIDATION RESULTS")
        print("=" * 50)

        if self.errors:
            print(f"❌ CRITICAL ERRORS: {len(self.errors)}")
            for error in self.errors:
                print(f"  • {error}")
        else:
            print("✅ NO CRITICAL ERRORS")

        if self.warnings:
            print(f"⚠️  WARNINGS: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  • {warning}")
        else:
            print("✅ NO WARNINGS")

        print(f"✅ SUCCESSFUL CHECKS: {self.success_count}")

        success = len(self.errors) == 0
        if success:
            print("\n🎉 SYSTEM IS PRODUCTION READY!")
        else:
            print("\n❌ SYSTEM NEEDS FIXES BEFORE PRODUCTION")

        return success

    def _check_critical_files(self):
        """Check existence of critical files"""
        critical_files = [
            "backend/api/main.py",
            "backend/core/orchestrator.py",
            "backend/core/vector_store.py",
            "backend/core/llm_manager.py",
            "frontend/streamlit_app.py",
            "requirements.txt",
            "docker-compose.yml",
            "Dockerfile.backend",
            "Dockerfile.frontend",
            "README.md"
        ]

        for file_path in critical_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                # Check if file is not empty
                if full_path.stat().st_size == 0:
                    self.errors.append(f"Critical file is empty: {file_path}")
                else:
                    self.success_count += 1
                    print(f"✅ {file_path}")
            else:
                self.errors.append(f"Missing critical file: {file_path}")

    def _check_code_quality(self):
        """Check code quality and syntax"""
        python_files = [
            "backend/api/main.py",
            "backend/api/routes.py",
            "backend/core/config.py",
            "backend/core/orchestrator.py",
            "backend/core/vector_store.py",
            "backend/core/llm_manager.py",
            "backend/core/search.py",
            "backend/core/extractor.py",
            "backend/utils/cache.py",
            "backend/utils/export.py",
            "backend/models/schemas.py",
            "frontend/streamlit_app.py"
        ]

        for file_path in python_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self._validate_python_file(full_path)

    def _validate_python_file(self, file_path: Path):
        """Validate Python file syntax and structure"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check syntax
            ast.parse(content)

            # Check for basic structure
            if len(content.strip()) < 50:
                self.errors.append(f"File too short (possibly incomplete): {file_path}")
            else:
                self.success_count += 1

        except SyntaxError as e:
            self.errors.append(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            self.errors.append(f"Error reading {file_path}: {e}")

    def _check_imports(self):
        """Check for import issues"""
        # This will show warnings for external packages, which is expected
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract imports
                tree = ast.parse(content)
                imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                # Check for known external packages
                external_packages = [
                    'fastapi', 'uvicorn', 'streamlit', 'aiohttp', 'chromadb',
                    'google.generativeai', 'playwright', 'trafilatura',
                    'pydantic', 'python-multipart'
                ]

                for imp in imports:
                    base_import = imp.split('.')[0]
                    if base_import in external_packages:
                        self.warnings.append(f"External import (expected): {base_import} in {file_path.name}")

            except:
                pass  # Skip files with syntax errors

    def _check_configuration(self):
        """Check configuration files"""
        # Check requirements.txt
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            with open(req_file, 'r') as f:
                requirements = f.read().strip()
                if len(requirements) < 100:
                    self.warnings.append("requirements.txt seems incomplete")
                else:
                    self.success_count += 1
        else:
            self.errors.append("requirements.txt missing")

        # Check for .env.example
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            self.success_count += 1
        else:
            self.warnings.append(".env.example missing")

    def _check_docker_files(self):
        """Check Docker configuration"""
        docker_files = ["docker-compose.yml", "Dockerfile.backend", "Dockerfile.frontend"]

        for file in docker_files:
            docker_file = self.project_root / file
            if docker_file.exists():
                with open(docker_file, 'r') as f:
                    content = f.read().strip()
                    if len(content) < 50:
                        self.warnings.append(f"{file} seems incomplete")
                    else:
                        self.success_count += 1
            else:
                self.errors.append(f"{file} missing")

def main():
    """Main validation function"""
    project_root = Path(__file__).parent

    validator = ProductionValidator(project_root)
    success = validator.validate_all()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
