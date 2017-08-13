# SiteCheck
Simple scanner to check ip status

## Requires:
- Gmail account 
- Linux environment
- Python 3.6 -- install the following via pip
  - httplib2
  - google-api-python-client
  - oauth2client

## Instructions
1. Generate your Google API client secret file and save it to the same directory as this script as client_secret_email.json [More details here](https://developers.google.com/adwords/api/docs/guides/authentication#installed)
2. Run emailer.py to authenticate with OAuth2. 
    If the machine has no GUI, use another computer to authenticate by running 'python emailer.py --noauth_local_webserver', copying the link to another computer, then entering the generated code.
3. Rename config.ini.example to config.ini, and fill out the fields
4. Run 'python sitecheck.py'
    This program supports multiple arguments. See 'python -h' for more!


## TO DO
- [ ] Add Windows support
