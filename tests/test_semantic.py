"""Offline tests for the semantic model rules the compiler applies."""
import unittest

from backplane.semantic import hide_key_columns, visible_key_columns

RELATIONSHIPS = "relationship f_company\n\tfromColumn: facts.company_id\n\ttoColumn: companies.company_id\n"
FACTS = "table facts\n\n\tcolumn company_id\n\t\tdataType: string\n\n\tcolumn amount\n\t\tdataType: double\n"
COMPANIES = "table companies\n\n\tcolumn company_id\n\t\tisHidden\n\t\tdataType: string\n\n\tcolumn company_name\n\t\tdataType: string\n"


class KeyColumns(unittest.TestCase):
    def parts(self):
        return {"definition/relationships.tmdl": RELATIONSHIPS,
                "definition/tables/facts.tmdl": FACTS, "definition/tables/companies.tmdl": COMPANIES}

    def test_only_visible_relationship_columns_are_reported(self):
        self.assertEqual(visible_key_columns(self.parts()), [("facts", "company_id")])

    def test_hiding_touches_only_the_key_and_is_idempotent(self):
        parts = self.parts()
        self.assertEqual(hide_key_columns(parts), ["facts.company_id"])
        self.assertIn("\tcolumn company_id\n\t\tisHidden\n\t\tdataType: string", parts["definition/tables/facts.tmdl"])
        self.assertNotIn("isHidden", parts["definition/tables/facts.tmdl"].split("column amount")[1])
        self.assertEqual(hide_key_columns(parts), [])
        self.assertEqual(visible_key_columns(parts), [])


if __name__ == "__main__":
    unittest.main()
