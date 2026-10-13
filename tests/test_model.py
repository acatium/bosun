"""Offline tests: the model validates, bad models are caught, and the deal-room rules decide correctly."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backplane import deal_room  # noqa: E402
from backplane.model import DEFAULT_MODEL, linkml_validate, load, reference_errors  # noqa: E402

MODEL_TEXT = DEFAULT_MODEL.read_text()


def variant(old: str, new: str) -> pathlib.Path:
    assert old in MODEL_TEXT, old
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    handle.write(MODEL_TEXT.replace(old, new, 1))
    handle.close()
    return pathlib.Path(handle.name)


class ModelValidation(unittest.TestCase):
    def test_contoso_model_is_valid(self):
        ok, output = linkml_validate(DEFAULT_MODEL)
        self.assertTrue(ok, output)
        self.assertEqual(reference_errors(load()), [])

    def test_unknown_tag_value_is_rejected(self):
        ok, _ = linkml_validate(variant("sensitivity: Confidential, member_kind: Guest", "sensitivity: TopSecret, member_kind: Guest"))
        self.assertFalse(ok)

    def test_term_without_definition_is_rejected(self):
        ok, _ = linkml_validate(variant('definition: "Net debt / LTM EBITDA, as a multiple."', "unit: x"))
        self.assertFalse(ok)

    def test_unknown_role_is_caught_by_reference_check(self):
        errors = reference_errors(load(variant("role: pe-partner, store: deal-room}", "role: pe-intern, store: deal-room}")))
        self.assertEqual(len(errors), 1)
        self.assertIn("pe-intern", errors[0])


class DealRoomRules(unittest.TestCase):
    model = load()

    def test_partner_may_open(self):
        self.assertEqual(deal_room.check_open(self.model, ["pe-partner", "pe-deal-team"]), "partners-open-deal-rooms")

    def test_associate_may_not_open(self):
        with self.assertRaises(deal_room.Refused):
            deal_room.check_open(self.model, ["pe-deal-team"])

    def test_guest_refused_on_confidential(self):
        with self.assertRaisesRegex(deal_room.Refused, "confidential-no-guests"):
            deal_room.check_member(self.model, "Confidential", "Guest", "someone")

    def test_member_allowed_on_confidential(self):
        deal_room.check_member(self.model, "Confidential", "Member", "someone")

    def test_guest_allowed_on_internal(self):
        deal_room.check_member(self.model, "Internal", "Guest", "someone")

    def test_roles_follow_directory_attributes(self):
        partner = {"department": "Private Equity", "jobTitle": "Partner"}
        analyst = {"department": "Private Equity", "jobTitle": "Analyst"}
        self.assertIn("pe-partner", deal_room.caller_roles(self.model, partner))
        self.assertNotIn("pe-partner", deal_room.caller_roles(self.model, analyst))


if __name__ == "__main__":
    unittest.main()
