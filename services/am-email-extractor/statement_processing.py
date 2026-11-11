import logging
import os
import uuid

import kafka_producer
from portfolio_asset_mapper import holdings_for_portfolio_event

logger = logging.getLogger(__name__)


def publish_extract_to_kafka(
    *,
    broker,
    user_id,
    holdings,
    portfolio_id,
    as_of_date=None,
    as_of_ts=None,
    authorization=None,
    file_path=None,
    password=None,
    jwt_claims=None,
):
    """
    Single holdings event for legacy brokers; CDSL/NPS fan-out on same am-portfolio topic.

    Returns (kafka_ok: bool, identity_match: str|None).
    """
    from brokers._common.identity_match import (
        cas_holder_from_doc,
        nps_holder_from_doc,
        profile_from_jwt,
        resolve_identity_match,
    )

    producer = kafka_producer.get_producer()
    profile_email, profile_name, profile_pan = profile_from_jwt(jwt_claims)

    if broker == "cdsl" and file_path:
        from brokers.cdsl.extractor import extract_document
        from brokers.cdsl.fanout import fanout_messages

        doc = extract_document(file_path, password)
        holder_email, holder_name, holder_pan = cas_holder_from_doc(doc)
        identity_match = resolve_identity_match(
            profile_email=profile_email,
            profile_name=profile_name,
            doc_email=holder_email,
            doc_name=holder_name,
            profile_pan=profile_pan,
            doc_pan=holder_pan,
        )
        messages = fanout_messages(
            doc,
            user_id=user_id,
            as_of_date=as_of_date or doc.as_of_date,
            timestamp=as_of_ts,
            identity_match=identity_match,
            holder_name=holder_name,
            holder_email=holder_email,
            holder_pan=holder_pan,
        )
        ok = True
        for msg in messages:
            ok = producer.send_payload(msg) and ok
        return ok, identity_match

    if broker == "nps" and file_path:
        from brokers.nps.extractor import extract_document
        from brokers.nps.fanout import fanout_messages

        doc = extract_document(file_path, password)
        holder_email, holder_name, holder_pan = nps_holder_from_doc(doc)
        identity_match = resolve_identity_match(
            profile_email=profile_email,
            profile_name=profile_name,
            doc_email=holder_email,
            doc_name=holder_name,
            profile_pan=profile_pan,
            doc_pan=holder_pan,
        )
        messages = fanout_messages(
            doc,
            user_id=user_id,
            timestamp=as_of_ts,
            identity_match=identity_match,
            holder_name=holder_name,
            holder_email=holder_email,
            holder_pan=holder_pan,
        )
        ok = True
        for msg in messages:
            ok = producer.send_payload(msg) and ok
        return ok, identity_match

    process_id = str(uuid.uuid4())
    equities, mutual_funds = holdings_for_portfolio_event(
        holdings, broker, authorization=authorization
    )
    ok = producer.send_update_event(
        process_id=process_id,
        user_id=user_id,
        broker=broker,
        portfolio_id=portfolio_id,
        equities=equities,
        mutual_funds=mutual_funds,
        as_of_date=as_of_date,
        timestamp=as_of_ts,
    )
    return ok, None


def publish_and_observe(
    *,
    broker,
    user_id,
    holdings,
    portfolio_id,
    as_of_date=None,
    as_of_ts=None,
    authorization=None,
    file_path=None,
    password=None,
    jwt_claims=None,
    mongo_db=None,
):
    """Publish extract to Kafka and emit structured observability logs."""
    kafka_ok, identity_match = publish_extract_to_kafka(
        broker=broker,
        user_id=user_id,
        holdings=holdings,
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        as_of_ts=as_of_ts,
        authorization=authorization,
        file_path=file_path,
        password=password,
        jwt_claims=jwt_claims,
    )
    broker_addr = os.environ.get('KAFKA_BOOTSTRAP_SERVERS') or os.environ.get(
        'SPRING_KAFKA_BOOTSTRAP_SERVERS', 'unknown'
    )
    logger.info(
        "extract_publish broker=%s db=%s holdings_count=%s mongo_id=%s kafka_ok=%s identity_match=%s kafka_bootstrap=%s",
        broker,
        mongo_db,
        len(holdings or []),
        portfolio_id,
        kafka_ok,
        identity_match,
        broker_addr,
    )
    return kafka_ok, identity_match
