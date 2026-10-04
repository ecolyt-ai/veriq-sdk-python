# veriq-sdk

Official Python SDK for the [Veriq](https://veriq.ecolyt.ai) API (beta).

```bash
pip install veriq-sdk
```

```python
import os
from veriq import VeriqClient

client = VeriqClient(api_key=os.environ["VERIQ_API_KEY"])
response = client.search("what is retrieval augmented generation", include_answer=True)
print(response.answer)
```

Documentation: https://veriq.ecolyt.ai/docs/
