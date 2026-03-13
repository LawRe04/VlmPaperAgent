import json
import requests
import time
import os
from scholarly import scholarly

def get_author_papers_by_name(author_name: str) -> str:
    """
    Search for a Google Scholar profile by author name and return a list of their papers.
    ...
    """
    try:
        search_query = scholarly.search_author(author_name)
        author = next(search_query, None)
        
        if not author:
            return json.dumps({"error": f"Author '{author_name}' not found on Google Scholar."})

        author = scholarly.fill(author)
        
        papers = []
        for pub in author.get('publications', []):
            title = pub.get('bib', {}).get('title', '')
            if title:
                papers.append({'title': title})
                
        # To avoid overwhelmingly large responses, limit to 100 recent/top papers
        return json.dumps({
            "author_name": author.get('name'),
            "affiliation": author.get('affiliation', ''),
            "papers": papers[:100] 
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch author profile: {str(e)}"})


def _requests_retry_get(url: str, params: dict = None, max_retries: int = 4) -> requests.Response:
    """Helper to perform requests with exponential backoff on 429 Too Many Requests."""
    headers = {}
    s2_api_key = os.environ.get("S2_API_KEY")
    if s2_api_key:
        headers["x-api-key"] = s2_api_key

    for i in range(max_retries):
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 429:
            # Rate limited, back off
            sleep_time = (2 ** i) + 1  # 2s, 3s, 5s, 9s etc.
            print(f"[Semantic Scholar API] Rate limited (429). Retrying in {sleep_time}s...")
            time.sleep(sleep_time)
            continue
        resp.raise_for_status()
        return resp
    # If we exhaust retries and it's still 429, just raise the last one
    resp.raise_for_status()
    return resp

def get_paper_citations(paper_title: str) -> str:
    """
    Given a paper title, search Semantic Scholar for the paper and return its citing papers,
    along with the authors of the citing papers and the exact sentences (contexts) where the 
    original paper was cited.
    """
    try:
        # 1. Search for the paper to get its Semantic Scholar ID
        search_url = f"https://api.semanticscholar.org/graph/v1/paper/search"
        search_params = {
            "query": paper_title,
            "limit": 1,
            "fields": "paperId,title,authors"
        }
        
        search_resp = _requests_retry_get(search_url, params=search_params)
        search_data = search_resp.json()
        
        if not search_data.get('data') or len(search_data['data']) == 0:
            return json.dumps({"error": f"Paper '{paper_title}' not found on Semantic Scholar."})
            
        paper = search_data['data'][0]
        paper_id = paper['paperId']
        found_title = paper['title']
        
        # 2. Get citations for this paper ID
        # We fetch a larger number (e.g., 500) and sort them locally to return the highest-impact ones.
        citation_url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
        citation_params = {
            "fields": "title,authors,contexts,intents,isInfluential,citingPaper.citationCount,citingPaper.authors.name,citingPaper.authors.hIndex",
            "limit": 500 
        }
        
        cit_resp = _requests_retry_get(citation_url, params=citation_params)
        cit_data = cit_resp.json()
        
        raw_citations = []
        for citation in cit_data.get('data', []):
            is_influential = citation.get('isInfluential', False)
            citing_paper = citation.get('citingPaper', {})
            citation_count = citing_paper.get('citationCount', 0)
            
            author_data = citing_paper.get('authors', [])
            authors = [a.get('name') for a in author_data]
            
            # Determine corresponding author h-index (last author in the list)
            corr_author_h_index = 0
            if author_data:
                # Assuming the last author is the corresponding/senior author
                last_author = author_data[-1]
                corr_author_h_index = last_author.get('hIndex', 0) or 0
                
            contexts = citation.get('contexts', [])
            intents = citation.get('intents', [])
            title = citing_paper.get('title', 'Unknown Title')
            
            raw_citations.append({
                "citing_paper_title": title,
                "authors": authors,
                "citation_contexts": contexts,
                "citation_intents": intents,
                "citation_count": citation_count,
                "is_influential": is_influential,
                "corr_author_h_index": corr_author_h_index
            })
            
        # 3. Sort by:
        # 1. corr_author_h_index (descending) - Priority 1
        # 2. citation_count (descending)      - Priority 2
        # 3. is_influential (influential papers first)
        sorted_citations = sorted(
            raw_citations, 
            key=lambda x: (x['corr_author_h_index'], x['citation_count'], x['is_influential']), 
            reverse=True
        )
        
        # Limit to top 200 for the Agent's context
        final_citations = sorted_citations[:400]
            
        return json.dumps({
            "original_paper_title": found_title,
            "citations": final_citations
        }, ensure_ascii=False, indent=2)
        
    except requests.exceptions.HTTPError as e:
        return json.dumps({"error": f"Semantic Scholar API error: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch paper citations: {str(e)}"})
