Generate `sample_ohlcv.json` once, locally, with:

```bash
python -c "
from technical_analyst.data.providers.yfinance_provider import YFinanceProvider
import json
s = YFinanceProvider().fetch('AAPL', '1d', 120)
json.dump(s.model_dump(mode='json'), open('tests/fixtures/sample_ohlcv.json', 'w'))
"
```

Commit the generated file so tests run offline for everyone.
