# Contributing to Kubernetes Resource Monitor

First off, thank you for considering contributing to this project! 🎉

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check the [issue list](https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard/issues) to see if the problem has already been reported.

**When you create a bug report, please include:**
- A clear and descriptive title
- Steps to reproduce the behavior
- Expected vs actual behavior
- Your environment details (OS, Docker version, Kubernetes version)
- Screenshots if applicable

### 💡 Suggesting Enhancements

Enhancement suggestions are welcome! Please open an issue with:
- A clear and descriptive title
- A detailed description of the suggested enhancement
- Explanation of why this enhancement would be useful

### 🔧 Pull Requests

1. **Fork the repository** and create your branch from `master`
2. **Make your changes** following our coding standards
3. **Test your changes** - ensure all tests pass
4. **Update documentation** if needed
5. **Submit a pull request**

## Development Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-username/fastapi-k8s-resource-dashboard.git
cd fastapi-k8s-resource-dashboard

# 2. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 3. Start development environment
./start.sh

# 4. Run tests
make test

# 5. Check code quality
make lint
```

## Coding Standards

- **Python**: Follow PEP 8, use type hints
- **JavaScript**: Use modern ES6+ syntax, consistent formatting
- **Documentation**: Update README.md and code comments as needed
- **Commits**: Use clear, descriptive commit messages

## Project Structure

```
├── app/                    # FastAPI application
│   ├── api/               # API routes
│   ├── core/              # Configuration and database
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   └── static/            # Frontend assets
├── k8s/                   # Kubernetes manifests
├── docs/                  # Documentation and screenshots
└── tests/                 # Test files
```

## Testing

- Write tests for new features
- Ensure existing tests pass
- Test with different Kubernetes and Prometheus setups

## Questions?

Feel free to open an issue for questions or join the discussion in existing issues.

Thank you for contributing! 🙏