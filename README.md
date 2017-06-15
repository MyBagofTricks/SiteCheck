# SiteCheck
Simple scanner to check ip status

## Requires:
- Linux environment
- Python3
-- httplib2
-- google-api-python-client
-- oauth2client

## Instructions
1. Rename sitecheck.config.json.example to sitecheck.config.json
2. Replace dummy fields with your data
3. Run 'emailer.py' to trigger OAuth2 and generate tokens
4. Run 'sitecheck.py'

## TO DO
- [ ] Adjust timeouts
- [ ] Add port selection
- [ ] Revamp email text
