# oge.gl

`oge.gl` is a searchable web application for U.S. Office of Government Ethics transaction disclosures.

The detailed product and development documentation lives under [docs/](docs/).

## Documentation

- [Product specification](docs/product-specification.md)
- [Development requirements](docs/development-requirements.md)

## Summary

The application is intended to:

1. Discover public OGE Form 278-T filings.
2. Download and scrape transaction PDFs.
3. Normalize and store filing and transaction data.
4. Expose the data through an API.
5. Provide a searchable frontend for filer, asset, trade type, date, and amount.
