"""A reviewed PostgreSQL deparser rewrite cannot hide another schema change."""

from verify_observation_backup import canonical_constraints


def test_exact_reviewed_rewrite_is_accepted():
    rule = {
        "table_name": "fills",
        "constraint_name": "status_check",
        "source": "source expression",
        "restored": "equivalent expression",
    }
    row = {
        "table_name": "fills",
        "constraint_name": "status_check",
        "definition": "equivalent expression",
    }
    assert canonical_constraints([row], [rule])[0]["definition"] == "source expression"
    assert row["definition"] == "equivalent expression"


def test_other_constraint_or_expression_is_never_normalized():
    rule = {
        "table_name": "fills",
        "constraint_name": "status_check",
        "source": "source expression",
        "restored": "equivalent expression",
    }
    rows = [
        {
            "table_name": "other",
            "constraint_name": "status_check",
            "definition": "equivalent expression",
        },
        {
            "table_name": "fills",
            "constraint_name": "status_check",
            "definition": "weakened expression",
        },
    ]
    assert canonical_constraints(rows, [rule]) == rows
