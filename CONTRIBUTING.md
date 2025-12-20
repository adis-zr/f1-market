# Contributing to F1 Market

Thank you for your interest in contributing to F1 Market! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style Guide](#code-style-guide)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. We expect all contributors to:

- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### Local Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/f1-market.git
   cd f1-market
   ```

3. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/f1-market.git
   ```

4. **Set up the development environment**

   Follow the [Setup Guide](docs/dev/SETUP.md) for detailed instructions.

   Quick version:
   ```bash
   # Backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Frontend
   cd frontend
   npm install
   cd ..
   ```

5. **Run tests** to verify your setup
   ```bash
   pytest
   ```

---

## Development Workflow

### 1. Create a Branch

Always create a feature branch from `main`:

```bash
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests

### 2. Make Changes

- Write clean, readable code
- Follow the code style guide (below)
- Add tests for new functionality
- Update documentation if needed

### 3. Run Tests

Before committing, ensure all tests pass:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run frontend linting
cd frontend && npm run lint
```

### 4. Commit Your Changes

Write clear, concise commit messages:

```bash
git add .
git commit -m "Add feature: description of what you did"
```

**Commit message format:**

```
<type>: <short description>

<optional longer description>

<optional footer>
```

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting, missing semicolons, etc.
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

Examples:
```
feat: add price history chart to market detail page

fix: prevent negative share quantities in buy orders

docs: update API reference with new endpoints

test: add unit tests for bonding curve calculations
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Code Style Guide

### Python (Backend)

We follow [PEP 8](https://pep8.org/) with some additions:

**General:**
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)
- Use double quotes for strings
- Add docstrings to functions and classes

**Type Hints:**
Type hints are encouraged but not required:
```python
def buy_shares(user_id: int, market_id: int, quantity: Decimal) -> dict:
    """Buy shares in a market."""
    ...
```

**Imports:**
```python
# Standard library
import os
from decimal import Decimal

# Third-party
from flask import Blueprint, jsonify
from sqlalchemy import func

# Local
from db import db, Market
from services.market_service import MarketService
```

**Docstrings:**
```python
def calculate_cost(supply: Decimal, quantity: Decimal, a: Decimal, b: Decimal) -> Decimal:
    """
    Calculate the cost to buy shares using bonding curve.

    Args:
        supply: Current supply
        quantity: Number of shares to buy
        a: Bonding curve slope
        b: Bonding curve baseline

    Returns:
        Total cost as Decimal
    """
    ...
```

### TypeScript/React (Frontend)

**General:**
- Use TypeScript for all new code
- Use functional components with hooks
- Use named exports (not default exports)

**File Structure:**
```typescript
// Imports (grouped and sorted)
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Market } from '@/api/types';

// Types/Interfaces
interface Props {
  marketId: number;
}

// Component
export function MarketCard({ marketId }: Props) {
  // Hooks
  const [shares, setShares] = useState(0);
  const { data, isLoading } = useQuery(...);

  // Handlers
  const handleBuy = () => {
    ...
  };

  // Render
  return (
    ...
  );
}
```

**Naming:**
- Components: PascalCase (`MarketCard.tsx`)
- Hooks: camelCase with `use` prefix (`useMarket.ts`)
- Utilities: camelCase (`formatPrice.ts`)
- Types: PascalCase (`MarketData`)

**Styling:**
- Use Tailwind CSS utility classes
- Extract repeated patterns into components
- Avoid inline styles

### Git Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor" not "Moves cursor")
- Keep the first line under 72 characters
- Reference issues in the footer when applicable

---

## Pull Request Process

### Before Submitting

1. **Ensure tests pass:** `pytest`
2. **Ensure linting passes:** `cd frontend && npm run lint`
3. **Update documentation** if you changed behavior
4. **Rebase on latest main** to avoid merge conflicts

### PR Template

When you create a PR, include:

```markdown
## Summary
Brief description of what this PR does.

## Changes
- List of specific changes
- Another change
- Another change

## Testing
- How you tested this
- What test cases you added

## Related Issues
Fixes #123
```

### Review Process

1. **Automated checks** run on your PR
2. **Code review** by maintainers
3. **Address feedback** by pushing more commits
4. **Approval and merge** by a maintainer

### What We Look For

- Code quality and readability
- Test coverage for new features
- Documentation updates
- No breaking changes (unless discussed)
- Follows code style guide

---

## Reporting Issues

### Bug Reports

When reporting a bug, include:

1. **Description:** What happened?
2. **Expected behavior:** What should have happened?
3. **Steps to reproduce:**
   1. Go to...
   2. Click on...
   3. See error
4. **Environment:**
   - OS (macOS, Windows, Linux)
   - Browser (if frontend issue)
   - Python version (if backend issue)
5. **Logs/Screenshots:** If applicable

### Security Issues

For security vulnerabilities, please email the maintainers directly instead of creating a public issue.

---

## Feature Requests

We welcome feature suggestions! When proposing a feature:

1. **Check existing issues** to avoid duplicates
2. **Describe the feature** in detail
3. **Explain the use case** - why is this needed?
4. **Consider alternatives** - are there other ways to solve this?

Use the "enhancement" label for feature requests.

---

## Project Structure

Key directories for contributors:

```
f1-market/
├── api/                # API routes (Flask blueprints)
├── auth/               # Authentication (OTP)
├── db/                 # Database models
├── pricing/            # Bonding curve pricing
├── services/           # Business logic
├── tests/              # Test suite
├── frontend/
│   ├── src/
│   │   ├── api/       # API client
│   │   ├── components/ # React components
│   │   ├── hooks/      # Custom hooks
│   │   ├── pages/      # Route pages
│   │   └── lib/        # Utilities
│   └── ...
└── docs/               # Documentation
```

See [Architecture Guide](docs/dev/ARCHITECTURE.md) for more details.

---

## Documentation

When contributing to documentation:

- **Developer docs:** `docs/dev/` - Technical guides
- **User docs:** `docs/user/` - End-user guides
- **API docs:** `docs/dev/API_REFERENCE.md`

Keep documentation:
- Up to date with code changes
- Clear and concise
- Well-organized with headings
- Including examples where helpful

---

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Search closed issues for similar questions
3. Open a new issue with the "question" label

Thank you for contributing!
