# Security Reference

Detailed descriptions for each Domain 2 check.

## 1. Secrets management

Look for: any string that looks like a key, token, password, or connection
string that is NOT loaded from an environment variable or secret store.

Search the codebase for these patterns (automatic fail if found):
```
grep -r "sk-" .          # OpenAI keys
grep -r "Bearer " .      # hardcoded auth headers
grep -r "password=" .    # hardcoded passwords
grep -r "token=" .       # hardcoded tokens
grep -r "postgresql://" . # connection strings with credentials
grep -r "AccountKey=" .  # Azure storage keys
```

Good pattern:
```python
import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

kv = SecretClient(vault_url=os.environ["KEY_VAULT_URL"],
                  credential=DefaultAzureCredential())
api_key = kv.get_secret("OPENAI-API-KEY").value
```

## 2. Prompt injection protection

Beyond delimiter isolation (covered in action-safety.md), look for:

- Maximum length enforcement on raw_text before prompt injection
- Stripping or escaping of XML/HTML tags that could break prompt structure
- Rejection of messages that contain known injection patterns

```python
# GOOD
MAX_MESSAGE_LENGTH = 2000

def sanitise_for_prompt(text: str) -> str:
    text = text[:MAX_MESSAGE_LENGTH]
    # Escape XML tags that could break prompt delimiters
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text
```

## 3. LLM response as untrusted input

The LLM response must never be executed directly (eval, exec, subprocess).
Look for any of these patterns — automatic fail:

```python
eval(llm_response)           # FAIL
exec(llm_response)           # FAIL
subprocess.run(llm_response) # FAIL
os.system(llm_response)      # FAIL
```

Also check: does the code pass LLM output through a strict parser before
using any field? (See action-safety.md #5 for schema validation)

## 4. Bot token minimum permissions

For Microsoft Teams (Azure Bot Service), check the Azure AD app registration
permissions. Required minimum:
- ChannelMessage.Send — post replies
- ChannelMessage.Read.All — read messages (Application permission)

Red flags:
- Directory.ReadWrite.All — far too broad
- User.ReadWrite.All — not needed
- Files.ReadWrite.All — not needed

For Slack: check the OAuth scopes in the app manifest. Should be limited to
`chat:write`, `channels:history`, `channels:read`.

## 5. Jira API token scope

The Jira API token should only be able to:
- Create issues in the ops project
- Add comments to issues
- Read issue details

It should NOT have:
- Admin privileges
- Access to other projects
- User management permissions

Check: is the token a personal API token (scoped to one user) or a service
account token? Service account is preferred for production.

## 6. Outbound webhook URL validation

Before posting a reply to Teams, verify the service_url comes from a known
Microsoft domain.

```python
# GOOD
ALLOWED_SERVICE_URL_HOSTS = {
    "smba.trafficmanager.net",
    "smba.trafficmanager.net",
    "teams.microsoft.com",
}

from urllib.parse import urlparse

def validate_service_url(url: str) -> bool:
    host = urlparse(url).netloc
    return any(host.endswith(allowed) for allowed in ALLOWED_SERVICE_URL_HOSTS)
```

If the service_url is taken directly from the incoming activity and used
without validation, a malicious actor could redirect bot replies to an
arbitrary endpoint.
