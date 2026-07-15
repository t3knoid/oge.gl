from app.discovery.client import OgeDiscoveryClient


def test_parse_collection_html_filters_to_278_transactions() -> None:
    html = """
    <table>
      <tbody>
        <tr>
          <td>07/01/2026</td>
          <td>President</td>
          <td><a href="/files/trump-278t.pdf">278 Transaction</a></td>
          <td>Trump, Donald J</td>
          <td>White House Office</td>
          <td>n/a</td>
        </tr>
        <tr>
          <td>07/01/2026</td>
          <td>President</td>
          <td>Annual (2026)</td>
          <td>Trump, Donald J</td>
          <td>White House Office</td>
          <td>n/a</td>
        </tr>
      </tbody>
    </table>
    """

    client = OgeDiscoveryClient(base_url="https://www.oge.gov/search")
    records = client.parse_collection_html(html)

    assert len(records) == 1
    assert records[0].type_label == "278 Transaction"
    assert records[0].source_pdf_url == "https://www.oge.gov/files/trump-278t.pdf"


def test_parse_collection_html_rejects_off_domain_pdf_links() -> None:
    html = """
    <table>
      <tbody>
        <tr>
          <td>07/01/2026</td>
          <td>President</td>
          <td><a href="https://evil.example/trump-278t.pdf">278 Transaction</a></td>
          <td>Trump, Donald J</td>
          <td>White House Office</td>
          <td>n/a</td>
        </tr>
      </tbody>
    </table>
    """

    client = OgeDiscoveryClient(base_url="https://www.oge.gov/search")
    records = client.parse_collection_html(html)

    assert len(records) == 1
    assert records[0].source_pdf_url is None


def test_parse_collection_json_filters_to_278_transactions() -> None:
    payload = """
    {
      "recordsTotal": 2,
      "recordsFiltered": 2,
      "data": [
        {
          "date": "07/01/2026",
          "title": "DAEO",
          "type": "278 Transaction (<a href='https://extapps2.oge.gov/201/Presiden.nsf/PAS+Index/ADE89624CD8D7F1D85258E35002DD6B1/$FILE/Sean-McMaster-06.11.2026-278T.pdf'>View PDF</a>)",
          "name": "Pena, Jennifer T",
          "agency": "International Boundary and Water Commission",
          "level": "n/a"
        },
        {
          "date": "07/01/2026",
          "title": "DAEO",
          "type": "Annual (2026)",
          "name": "Pena, Jennifer T",
          "agency": "International Boundary and Water Commission",
          "level": "n/a"
        }
      ]
    }
    """

    client = OgeDiscoveryClient(base_url="https://www.oge.gov/search")
    records = client.parse_collection_json(payload)

    assert len(records) == 1
    assert records[0].filer_name == "Pena, Jennifer T"
    assert (
        records[0].source_pdf_url
        == "https://extapps2.oge.gov/201/Presiden.nsf/PAS+Index/ADE89624CD8D7F1D85258E35002DD6B1/$FILE/Sean-McMaster-06.11.2026-278T.pdf"
    )


def test_parse_collection_json_skips_request_links_without_pdf() -> None:
    payload = """
    {
      "recordsTotal": 1,
      "recordsFiltered": 1,
      "data": [
        {
          "date": "07/01/2026",
          "title": "DAEO",
          "type": "278 Transaction (<a href='https://extapps2.oge.gov/201/Presiden.nsf/201%20Request?OpenForm&Filer=Pena'>Request this Document</a>)",
          "name": "Pena, Jennifer T",
          "agency": "International Boundary and Water Commission",
          "level": "n/a"
        }
      ]
    }
    """

    client = OgeDiscoveryClient(base_url="https://www.oge.gov/search")
    records = client.parse_collection_json(payload)

    assert records == []


def test_extract_json_api_url_from_collection_page() -> None:
    page_html = """
    <script>
      var tableConfig = {
        &quot;ajax&quot;: {
          &quot;url&quot;: &quot;https://extapps2.oge.gov/201/Presiden.nsf/API.xsp/v2/rest&quot;
        }
      };
    </script>
    """

    client = OgeDiscoveryClient()
    assert client._extract_json_api_url(page_html) == "https://extapps2.oge.gov/201/Presiden.nsf/API.xsp/v2/rest"
