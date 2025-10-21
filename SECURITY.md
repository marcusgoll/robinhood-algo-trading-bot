# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately to help protect users.

**DO NOT** open a public GitHub issue for security vulnerabilities.

### How to Report

1. **Email**: Contact the maintainer at marcusgoll@gmail.com
2. **GitHub Security Advisory**: Use GitHub's [private vulnerability reporting](https://github.com/marcusgoll/robinhood-algo-trading-bot/security/advisories/new)

### What to Include

Please include:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if available)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Fix Timeline**: Critical vulnerabilities will be addressed within 7 days
- **Disclosure**: After a fix is released, we'll publicly disclose the vulnerability

## Security Best Practices for Users

### Never Commit Credentials

This project uses environment variables for sensitive data:

- **DO NOT** commit `.env` files to git
- **DO NOT** commit `config.json` to git
- **DO NOT** commit `.robinhood.pickle` session files
- **DO NOT** hardcode credentials in any source files

### Robinhood API Security

1. **Enable 2FA**: Always enable two-factor authentication on your Robinhood account
2. **Use Paper Trading First**: Test strategies in paper trading mode before using real money
3. **Secure Your Credentials**:
   - Store credentials in `.env` file (gitignored)
   - Use strong, unique passwords
   - Rotate credentials if compromised
4. **Monitor API Activity**: Regularly review your Robinhood account for unauthorized activity

### Configuration Security

- Review `config.json` settings before running
- Start with small position sizes in live trading
- Enable all circuit breakers (daily loss limits, consecutive losses)
- Use minimal API permissions

### Dependency Security

- Regularly update dependencies: `pip install --upgrade -r requirements.txt`
- Run security scans: `bandit -r src/`
- Check for known vulnerabilities: `pip-audit` (if available)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Known Security Considerations

### Robinhood API

- This bot uses unofficial Robinhood API wrapper (`robin_stocks`)
- Robinhood may change their API without notice
- Session tokens expire and require re-authentication

### Local Storage

- Session tokens stored in `.robinhood.pickle` (gitignored)
- Trade logs contain sensitive information (gitignored)
- Ensure proper file permissions on sensitive files

### Risk Management

- Always test strategies thoroughly in paper trading
- Never invest more than you can afford to lose
- Understand that past performance doesn't guarantee future results

## Disclaimer

This software is provided "as is" without warranty. Users are responsible for:

- Their own trading decisions
- Tax reporting and compliance
- Securing their credentials and API keys
- Understanding and accepting all risks

**This is not financial advice.**
