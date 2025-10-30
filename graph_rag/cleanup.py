import os
import sys
import time

from neo4j import GraphDatabase

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings
from logger_factory import get_logger

log = get_logger("graph_rag.cleanup")
driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))

def _qname(name: str) -> str:
	# Backtick-escape an identifier
	return "`" + str(name).replace("`", "") + "`"


def _drop_vector_index(session, name: str):
	if not name:
		return
	# Check whether the specific vector index exists, then drop it
	found = session.run(
		"SHOW INDEXES YIELD name, type WHERE name=$name RETURN name, type",
		name=name,
	).single()
	if found:
		session.run(f"DROP INDEX {_qname(name)} IF EXISTS")
		log.info(f"Dropped vector index: {name}")
	else:
		log.debug(f"Vector index not found: {name}")


def _drop_all_constraints(session):
	# Collect and drop all constraints by name
	result = session.run("SHOW CONSTRAINTS YIELD name RETURN name")
	names = [r["name"] for r in result]
	if not names:
		log.info("No constraints to drop.")
		return
	log.info(f"Dropping {len(names)} constraint(s)...")
	for n in names:
		session.run(f"DROP CONSTRAINT {_qname(n)} IF EXISTS")
		log.debug(f"  - Dropped constraint: {n}")


def _drop_all_indexes(session):
	# Drop all indexes except system-managed LOOKUP indexes
	result = session.run("SHOW INDEXES YIELD name, type RETURN name, type")
	to_drop = []
	for r in result:
		idx_name = r["name"]
		idx_type = r["type"]
		if str(idx_type).upper() == "LOOKUP":
			continue
		to_drop.append(idx_name)
	if not to_drop:
		log.info("No indexes to drop (excluding LOOKUP).")
		return
	log.info(f"Dropping {len(to_drop)} index(es) (excluding LOOKUP)...")
	for idx_name in to_drop:
		session.run(f"DROP INDEX {_qname(idx_name)} IF EXISTS")
		log.debug(f"  - Dropped index: {idx_name}")


def _delete_all_data(session, batch_size: int = 10000, log_every: int = 5) -> int:
	# Delete nodes in batches to avoid memory/timeouts on large graphs
	total = 0
	batches = 0
	while True:
		rec = session.run(
			"""
			MATCH (n)
			WITH n LIMIT $batch
			WITH collect(n) AS batch
			FOREACH (n IN batch | DETACH DELETE n)
			RETURN size(batch) AS c
			""",
			batch=batch_size,
		).single()
		count = rec["c"] if rec else 0
		if count == 0:
			break
		total += count
		batches += 1
		if batches % max(1, log_every) == 0:
			log.info(f"🗑️ Deleted {total:,} nodes so far ({batches} batch(es))...")
	return total


def cleanup():
	start = time.perf_counter()
	log.info(f"Starting cleanup on database '{settings.database}' @ {settings.uri}")
	batch_size = int(os.getenv("DELETE_BATCH_SIZE", "10000"))
	log_every = int(os.getenv("LOG_EVERY_N_BATCHES", "5"))

	with driver.session(database=settings.database) as session:
		# Delete data first for faster schema drops
		t0 = time.perf_counter()
		total = _delete_all_data(session, batch_size=batch_size, log_every=log_every)
		log.info(f"Data deletion finished: {total:,} node(s) removed in {time.perf_counter() - t0:0.2f}s")

		t1 = time.perf_counter()
		_drop_vector_index(session, settings.vector_index)
		log.debug(f"Vector index check/drop completed in {time.perf_counter() - t1:0.2f}s")

		t2 = time.perf_counter()
		_drop_all_constraints(session)
		log.debug(f"Constraints drop completed in {time.perf_counter() - t2:0.2f}s")

		t3 = time.perf_counter()
		_drop_all_indexes(session)
		log.debug(f"Indexes drop completed in {time.perf_counter() - t3:0.2f}s")

	log.info(f"Cleanup completed in {time.perf_counter() - start:0.2f}s")


if __name__ == "__main__":
	try:
		cleanup()
	except Exception as e:
		log.exception("Error occurred during cleanup: %s", e)
	finally:
		driver.close()

