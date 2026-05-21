from app.services.legal.legal_ingestion_service import ingest_traffic_law_documents


if __name__ == "__main__":
    result = ingest_traffic_law_documents()
    print(
        "provider={provider} run_id={run_id} inserted_documents={inserted_documents} inserted_chunks={inserted_chunks}".format(
            **result
        )
    )
