#!/bin/bash
# Update Alpaca watchlist via REST API

WATCHLIST_ID="9029ee65-d3ca-420e-8ba6-3ab2ea0eb5ce"
API_KEY="${ALPACA_API_KEY}"
SECRET_KEY="${ALPACA_SECRET_KEY}"

if [ -z "$API_KEY" ] || [ -z "$SECRET_KEY" ]; then
  echo "❌ ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables required"
  exit 1
fi

# Updated symbols (44 total - removed PWCDF)
SYMBOLS='["BNTX","FHLC","HCA","NVZMY","JAZZ","GIB","NHC","INCY","TRMB","BAESY","ADBE","HOLX","MOH","ZTS","ITRI","WST","MKTX","VEEV","DGX","ICUI","HCSG","IDYA","EXTR","NABZY","BWA","GLPG","SRPT","BKD","TAK","GDS","FLGT","LOB","PHG","FONR","AVNS","CC","EJPRY","DNLI","EGAN","SEDG","MGIC","CHT","EQNR","CSWC"]'

echo "🔄 Updating Alpaca watchlist: TradingBot-Active"
echo "📊 Total symbols: 44"

# Update watchlist
curl -X PUT \
  -H "APCA-API-KEY-ID: $API_KEY" \
  -H "APCA-API-SECRET-KEY: $SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"TradingBot-Active\", \"symbols\": $SYMBOLS}" \
  "https://paper-api.alpaca.markets/v2/watchlists/$WATCHLIST_ID"

echo ""
echo "✅ Watchlist updated successfully"
