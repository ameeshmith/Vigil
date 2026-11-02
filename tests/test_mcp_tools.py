import pytest
from unittest.mock import patch, AsyncMock
from mcp_server.openfda_client import OpenFDAClient
from mcp_server.pubmed_client import PubMedClient

@pytest.mark.asyncio
async def test_search_faers_reactions_success():
    client = OpenFDAClient()
    mock_data = {
        "results": [
            {"term": "RHABDOMYOLYSIS", "count": 1250},
            {"term": "MYOPATHY", "count": 890}
        ]
    }
    with patch.object(client, "_fetch_with_backoff", new=AsyncMock(return_value=(200, mock_data, "https://api.fda.gov/mock_url"))):
        result = await client.search_faers_reactions("ATORVASTATIN", limit=5)
        assert result["status"] == "success"
        assert result["count_reactions"] == 2
        assert result["reactions"][0]["reaction"] == "RHABDOMYOLYSIS"
        assert result["reactions"][0]["count"] == 1250
        assert "source_url" in result

@pytest.mark.asyncio
async def test_search_faers_reactions_brand_fallback():
    client = OpenFDAClient()
    # First query (generic) fails with 404, second query (brand) succeeds
    mock_success = {
        "results": [
            {"term": "PANCREATITIS", "count": 450}
        ]
    }
    calls = []
    async def mock_fetch(url, params):
        calls.append(params.get("search", ""))
        if "generic_name" in params.get("search", ""):
            return 404, {"results": []}, "https://api.fda.gov/generic_fail"
        return 200, mock_success, "https://api.fda.gov/brand_success"

    with patch.object(client, "_fetch_with_backoff", side_effect=mock_fetch):
        result = await client.search_faers_reactions("OZEMPIC", limit=5)
        assert result["status"] == "success"
        assert result["reactions"][0]["reaction"] == "PANCREATITIS"
        assert len(calls) >= 2

@pytest.mark.asyncio
async def test_get_faers_totals():
    client = OpenFDAClient()
    async def mock_fetch(url, params):
        search = params.get("search", "")
        if "_exists_:safetyreportid" in search:
            return 200, {"meta": {"results": {"total": 10000000}}}, "url_total"
        elif "AND" in search:
            return 200, {"meta": {"results": {"total": 500}}}, "url_both"
        elif "reactionmeddrapt" in search:
            return 200, {"meta": {"results": {"total": 20000}}}, "url_rxn"
        else:
            return 200, {"meta": {"results": {"total": 50000}}}, "url_drug"

    with patch.object(client, "_fetch_with_backoff", side_effect=mock_fetch):
        res = await client.get_faers_totals("SIMVASTATIN", "RHABDOMYOLYSIS")
        assert res["status"] == "success"
        assert res["a"] == 500
        assert res["b"] == 50000 - 500 # 49500
        assert res["c"] == 20000 - 500 # 19500
        assert res["d"] == 10000000 - (500 + 49500 + 19500)
        assert len(res["source_urls"]) >= 4

@pytest.mark.asyncio
async def test_check_reaction_in_label_found():
    client = OpenFDAClient()
    mock_label = {
        "results": [{
            "boxed_warning": ["WARNING: Risk of thyroid C-cell tumors."],
            "warnings_and_precautions": ["Cases of pancreatitis have been reported in clinical trials."],
            "adverse_reactions": ["Nausea, vomiting, diarrhea, abdominal pain."]
        }]
    }
    with patch.object(client, "_fetch_with_backoff", new=AsyncMock(return_value=(200, mock_label, "https://api.fda.gov/label_mock"))):
        res = await client.check_reaction_in_label("SEMAGLUTIDE", "Pancreatitis")
        assert res["is_in_label"] is True
        assert res["section"] == "warnings_and_precautions"
        assert "pancreatitis" in res["snippet"].lower()
        assert len(res["snippet"]) <= 500

@pytest.mark.asyncio
async def test_check_reaction_in_label_not_found():
    client = OpenFDAClient()
    mock_label = {
        "results": [{
            "boxed_warning": [],
            "warnings_and_precautions": ["Mild headache and dizziness."],
            "adverse_reactions": ["Dry mouth."]
        }]
    }
    with patch.object(client, "_fetch_with_backoff", new=AsyncMock(return_value=(200, mock_label, "https://api.fda.gov/label_mock"))):
        res = await client.check_reaction_in_label("TESTDRUG", "Stevens-Johnson Syndrome")
        assert res["is_in_label"] is False
        assert res["section"] == "None"

@pytest.mark.asyncio
async def test_search_pubmed_mock():
    client = PubMedClient()
    mock_xml = """<?xml version="1.0"?>
    <!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>31234567</PMID>
          <Article>
            <ArticleTitle>Association of Statin Use with Rhabdomyolysis.</ArticleTitle>
            <Abstract>
              <AbstractText>We investigated rhabdomyolysis incidence in patients taking statins.</AbstractText>
            </Abstract>
            <Journal>
              <JournalIssue>
                <PubDate><Year>2023</Year></PubDate>
              </JournalIssue>
            </Journal>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        # 1st call: esearch, 2nd call: efetch
        mock_esearch_resp = AsyncMock()
        mock_esearch_resp.status_code = 200
        mock_esearch_resp.json = lambda: {"esearchresult": {"idlist": ["31234567"]}}

        mock_efetch_resp = AsyncMock()
        mock_efetch_resp.status_code = 200
        mock_efetch_resp.text = mock_xml

        mock_get.side_effect = [mock_esearch_resp, mock_efetch_resp]

        res = await client.search_pubmed("statin rhabdomyolysis", max_results=2)
        assert res["count"] == 1
        assert res["articles"][0]["pmid"] == "31234567"
        assert "Rhabdomyolysis" in res["articles"][0]["title"]
        assert "31234567" in res["articles"][0]["url"]

