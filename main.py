import argparse
import asyncio
import json
import os
from typing import List, Dict, Any
import pandas as pd

from src.validators.dns_http_checker import DomainValidator
from src.scrapers.fetcher import ContentFetcher
from src.extractors.llm_extractor import SchemaExtractor
from src.utils.deduplicator import PipelineDeduplicator

OUTPUT_DIR = "data"


def load_input_urls(input_path: str, url_col: str) -> List[str]:
    """Load URL list from CSV or Parquet file."""
    if input_path.endswith(".csv"):
        df = pd.read_csv(input_path)
    elif input_path.endswith(".parquet") or input_path.endswith(".pq"):
        df = pd.read_parquet(input_path)
    else:
        raise ValueError("Unsupported file format. Please provide a .csv or .parquet file.")

    if url_col not in df.columns:
        raise KeyError(f"Column '{url_col}' not found in input file. Available columns: {list(df.columns)}")

    return df[url_col].dropna().astype(str).tolist()


def save_incremental_results(records: List[Dict[str, Any]], output_path: str, is_first_batch: bool) -> None:
    """Incrementally append processed batch records to JSON or Parquet output file."""
    if not records:
        return

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df_batch = pd.DataFrame(records)

    if output_path.endswith(".csv"):
        mode = "w" if is_first_batch else "a"
        header = is_first_batch
        df_batch.to_csv(output_path, mode=mode, header=header, index=False)

    elif output_path.endswith(".parquet") or output_path.endswith(".pq"):
        if is_first_batch or not os.path.exists(output_path):
            df_batch.to_parquet(output_path, index=False)
        else:
            existing_df = pd.read_parquet(output_path)
            combined_df = pd.concat([existing_df, df_batch], ignore_index=True)
            combined_df.to_parquet(output_path, index=False)

    elif output_path.endswith(".json"):
        existing_records = []
        if not is_first_batch and os.path.exists(output_path):
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_records = json.load(f)
            except json.JSONDecodeError:
                existing_records = []

        existing_records.extend(records)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing_records, f, indent=2)


async def process_batch(
    batch_urls: List[str],
    deduper: PipelineDeduplicator,
    validator: DomainValidator,
    fetcher: ContentFetcher,
    extractor: SchemaExtractor,
    concurrency_limit: int = 10
) -> List[Dict[str, Any]]:
    """Process a single chunk/batch of URLs through the pipeline."""
    # Pre-Processing: Normalize & Deduplicate
    unique_urls = deduper.filter_duplicate_urls(batch_urls)
    if not unique_urls:
        return []

    # Stage 1: Domain & HTTP Status Validation
    validation_results = await validator.validate_batch(unique_urls)
    live_urls = [r["url"] for r in validation_results if r.get("is_valid")]
    if not live_urls:
        return []

    # Stage 2: Scrape & Content Extraction with Concurrency Control
    semaphore = asyncio.Semaphore(concurrency_limit)

    async def fetch_with_semaphore(target_url: str):
        async with semaphore:
            return await fetcher.fetch_page(target_url)

    fetch_tasks = [fetch_with_semaphore(url) for url in live_urls]
    raw_scraped_results = await asyncio.gather(*fetch_tasks)

    scraped_pages = []
    for res in raw_scraped_results:
        if res.get("success") and res.get("content"):
            if deduper.is_duplicate_content(res["content"]):
                print(f"   -> Skipping duplicate content at: {res['url']}")
                continue
            scraped_pages.append(res)

    if not scraped_pages:
        return []

    # Stage 3: LLM Structured Extraction
    batch_records = []
    for page in scraped_pages:
        print(f"   -> Extracting schema for: {page['url']}")
        
        # Extracted with logo and github hints
        extraction = await extractor.extract_async(
            text=page["content"],
            url=page["url"],
            logo_hint=page.get("logo_url"),
            github_hint=page.get("github_url")
        )

        # SAFEGUARD: Skip if extractor returned None (validation failed or Non-AI)
        if not extraction:
            print(f"   ⏩ Skipping {page['url']} (Validation failed or Non-AI)")
            continue

        record = {
            "source_url": page["url"],
            "raw_text_length": len(page.get("content", "")),
            **extraction
        }
        batch_records.append(record)

    return batch_records


async def run_pipeline(
    urls: List[str],
    output_file: str,
    batch_size: int = 50,
    concurrency: int = 10,
    proxy_url: str = None,
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    print("==================================================")
    print("           AI ORBIT - ETL PIPELINE                ")
    print("==================================================\n")

    deduper = PipelineDeduplicator()
    validator = DomainValidator()
    fetcher = ContentFetcher(proxy_url=proxy_url, max_retries=max_retries)
    extractor = SchemaExtractor()

    all_processed_records = []
    total_urls = len(urls)
    num_batches = (total_urls + batch_size - 1) // batch_size

    print(f"📊 Starting pipeline execution across {total_urls} URLs in {num_batches} batch(es)...\n")

    for idx in range(0, total_urls, batch_size):
        batch_num = (idx // batch_size) + 1
        chunk = urls[idx : idx + batch_size]

        print(f"--- Processing Batch {batch_num}/{num_batches} ({len(chunk)} URLs) ---")
        
        batch_results = await process_batch(
            batch_urls=chunk,
            deduper=deduper,
            validator=validator,
            fetcher=fetcher,
            extractor=extractor,
            concurrency_limit=concurrency
        )

        if batch_results:
            save_incremental_results(
                records=batch_results,
                output_path=output_file,
                is_first_batch=(batch_num == 1)
            )
            all_processed_records.extend(batch_results)
            print(f"✅ Batch {batch_num} complete. {len(batch_results)} record(s) appended to {output_file}.\n")
        else:
            print(f"⚠️ Batch {batch_num} produced no active/unique records.\n")

    print("==================================================")
    print("🎉 Pipeline Execution Finished!")
    print(f"📁 Total Output saved to: {output_file}")
    print(f"📈 Total Records Saved: {len(all_processed_records)}")
    print("==================================================")

    return all_processed_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Orbit - Web Scraper & Schema Extractor ETL Pipeline")
    parser.add_argument("--input", "-i", type=str, help="Path to input CSV or Parquet file containing URLs")
    parser.add_argument("--output", "-o", type=str, default="data/processed/processed_companies.csv", help="Output file path (.csv, .parquet, .json)")
    parser.add_argument("--col", type=str, default="url", help="Column name containing target URLs in the input file")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Number of URLs to process per chunk")
    parser.add_argument("--concurrency", "-c", type=int, default=10, help="Maximum concurrent HTTP requests per batch")
    parser.add_argument("--proxy", "-p", type=str, default=None, help="Proxy URL (e.g. 'http://user:pass@proxy.com:8080')")
    parser.add_argument("--retries", "-r", type=int, default=3, help="Max retry attempts for failed requests")

    args = parser.parse_args()

    if args.input:
        target_urls = load_input_urls(args.input, args.col)
    else:
        target_urls = [
            "https://openai.com",
            "https://www.openai.com",
            "https://anthropic.com",
            "https://thisisadeaddomainthatdoesnotexist12345.com",
            "https://google.com"
        ]

    asyncio.run(
        run_pipeline(
            urls=target_urls,
            output_file=args.output,
            batch_size=args.batch_size,
            concurrency=args.concurrency,
            proxy_url=args.proxy,
            max_retries=args.retries
        )
    )
