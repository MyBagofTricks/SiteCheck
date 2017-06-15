# SiteCheck
Simple scanner to check ip status

## Requires:
- Linux environment
- Gmail account 
- Python3
  - httplib2
  - google-api-python-client
  - oauth2client

## Instructions
1. Generate your Google API client secret file and save it to the same directory as this script [More details here](https://developers.google.com/adwords/api/docs/guides/authentication#installed)
2. Rename sitecheck.config.json.example to sitecheck.config.json and replace dummy fields with your data
3. Run 'emailer.py' to trigger OAuth2 and generate tokens
4. Run 'sitecheck.py'

## TO DO
- [ ] Adjust timeouts
- [ ] Add port selection
- [ ] Revamp email text
