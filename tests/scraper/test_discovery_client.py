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
