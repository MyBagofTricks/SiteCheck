# SiteCheck
Simple scanner to check ip status

## Requires:
- Gmail account 
- Linux environment
- Python3
  - httplib2
  - google-api-python-client
  - oauth2client

## Instructions
1. Generate your Google API client secret file and save it to the same directory as this script as client_secret_email.json [More details here](https://developers.google.com/adwords/api/docs/guides/authentication#installed)
2. Rename sitecheck.config.json.example to sitecheck.config.json and replace dummy fields with your data
3. Run 'emailer.py' to trigger OAuth2 and generate tokens
4. Run 'sitecheck.py'

## TO DO
- [ ] Add Windows support
