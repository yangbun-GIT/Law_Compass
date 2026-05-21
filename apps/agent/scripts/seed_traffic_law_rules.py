from __future__ import annotations

import os

import psycopg

from app.services.legal.legal_rule_mapper import SCENARIO_MAPPINGS, TRAFFIC_RULES

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")


def main():
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            for code, title, category, description, tags, required, flags in TRAFFIC_RULES:
                cur.execute(
                    """
                    INSERT INTO legal_rules(rule_code,title,category,description,scenario_tags,required_facts,risk_flags)
                    VALUES(%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(rule_code) DO UPDATE
                    SET title=EXCLUDED.title,
                        category=EXCLUDED.category,
                        description=EXCLUDED.description,
                        scenario_tags=EXCLUDED.scenario_tags,
                        required_facts=EXCLUDED.required_facts,
                        risk_flags=EXCLUDED.risk_flags
                    """,
                    (code, title, category, description, tags, required, flags),
                )
            mapping_count = 0
            for scenario_type, rows in SCENARIO_MAPPINGS.items():
                for rule_code, weight in rows:
                    cur.execute(
                        """
                        INSERT INTO scenario_legal_mappings(scenario_type, rule_code, weight)
                        SELECT %s,%s,%s
                        WHERE NOT EXISTS (
                          SELECT 1 FROM scenario_legal_mappings
                          WHERE scenario_type=%s AND rule_code=%s
                        )
                        """,
                        (scenario_type, rule_code, weight, scenario_type, rule_code),
                    )
                    mapping_count += 1
            conn.commit()
    print(f"seeded_rules={len(TRAFFIC_RULES)} seeded_mappings={mapping_count}")


if __name__ == "__main__":
    main()
