# AI Business Analyst - Contributing Guidelines

Thank you for considering contributing to the AI Business Analyst project! This document provides guidelines and instructions for contributing.

## 🚀 Quick Start for Contributors

1. **Fork the repository**
2. **Clone your fork**: `git clone https://github.com/YOUR_USERNAME/ai-business-analyst.git`
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Set up development environment** (see below)
5. **Make your changes**
6. **Test thoroughly**
7. **Submit a pull request**

## 🛠️ Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (optional but recommended)

### Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m uvicorn api.main:app --reload
```

### Frontend Setup (TODO - when implemented)
```bash
cd web
npm install
npm run dev
```

### Docker Development
```bash
# Build and run with hot reload
docker-compose up --build

# Run tests
docker-compose exec analyst pytest
```

## 📋 Code Standards

### Python Code
- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Maximum line length: 88 characters (Black default)

**Example:**
```python
async def analyze_question(
    question: str,
    context: Optional[Dict[str, str]] = None
) -> AnalysisResult:
    """
    Analyze a business question using autonomous agent.
    
    Args:
        question: Natural language business question
        context: Optional business context dictionary
        
    Returns:
        AnalysisResult with answer, confidence, and metadata
    """
    pass
```

### Testing
- Write tests for all new features
- Maintain >80% code coverage
- Use pytest for backend tests
- Mock external services (LLMs, databases)

Run tests:
```bash
pytest --cov=agent --cov=api
```

### Git Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Newsroom module for market intelligence
fix: resolve SQL injection vulnerability in executor
docs: update README with installation instructions
refactor: simplify agent state management
test: add unit tests for model router
chore: update dependencies to latest versions
```

## 🎯 Areas We Need Help

### High Priority
- [ ] **Frontend Development**: React + TypeScript implementation
- [ ] **Database Connectors**: Snowflake, BigQuery, Redshift adapters
- [ ] **Memory System**: pgvector integration for persistent learning
- [ ] **Security**: PII masking, row-level access control
- [ ] **Testing**: Comprehensive test suite

### Good First Issues
Look for issues labeled [`good first issue`](https://github.com/timilehin-dev/ai-business-analyst/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

### Advanced Contributions
- MCP server implementation
- What-if simulation engine
- Automated data quality checks
- Helm charts for Kubernetes deployment
- Connector marketplace infrastructure

## 🔒 Security Guidelines

When contributing:
1. **Never commit API keys or secrets**
2. **Default to read-only operations**
3. **Validate all user inputs**
4. **Sanitize SQL queries before execution**
5. **Respect air-gap mode configuration**

Report security vulnerabilities privately to security@timilehin.dev

## 📝 Pull Request Process

1. **Update documentation** if adding/changing features
2. **Add tests** for new functionality
3. **Ensure CI passes** (tests, linting, type checking)
4. **Squash commits** into logical units
5. **Request review** from maintainers

PR Template:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How did you test this?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No security concerns
```

## 💬 Communication

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and ideas
- **Discord**: Real-time chat (link TBD)

## 🏆 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Annual contributor spotlight (blog post)

## 📄 License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

---

**Questions?** Open an issue or join our Discord!
