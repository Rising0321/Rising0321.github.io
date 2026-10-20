import copy
import hashlib
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from update_talks import Client, UpstreamError, collection_videos, refresh


class FakeClient:
    def __init__(self, pages, stats=None):
        self.pages = iter(pages)
        self.stats = stats or {}

    def get(self, path, **params):
        if path.endswith("/view"):
            value = self.stats.get(params["bvid"], UpstreamError("unavailable"))
        else:
            value = next(self.pages)
        if isinstance(value, Exception):
            raise value
        return value


def video(bvid, views):
    return {"bvid": bvid, "stat": {"view": views}}


def page(items, total):
    return {"archives": items, "page": {"total": total}}


class StatsTests(unittest.TestCase):
    @patch("update_talks.time.time", return_value=1700000000)
    def test_wbi_signing_sorts_and_filters_parameters(self, clock):
        client = Client()
        client.wbi_key = "test-key"
        signed = client.sign({"z": "a!b", "a": 2})
        query = "a=2&wts=1700000000&z=ab"
        self.assertEqual(signed["w_rid"], hashlib.md5((query + "test-key").encode()).hexdigest())
        self.assertEqual(signed["z"], "ab")

    def test_video_uses_current_metadata_endpoint(self):
        client = Mock()
        client.get.return_value = {"stat": {"view": 12, "like": 0, "favorite": 4}}
        talk = {"bvid": "example"}
        success, errors = refresh(talk, client, "now")
        client.get.assert_called_once_with("/x/web-interface/wbi/view", bvid="example")
        self.assertTrue(success)
        self.assertFalse(errors)
        self.assertEqual(talk["likes"], 0)
        self.assertEqual(talk["stats_status"], "fresh")

    def test_pagination_and_deduplication(self):
        client = FakeClient([page([video("a", 5), video("b", 7)], 3),
                             page([video("b", 7), video("c", 9)], 3)])
        self.assertEqual(len(collection_videos(client, {
            "kind": "season", "mid": 1, "collection_id": 2})), 3)

    def test_incomplete_collection_keeps_previous_totals(self):
        talk = {"kind": "series", "mid": 1, "collection_id": 2, "views": 100}
        success, errors = refresh(talk, FakeClient([
            page([video("a", 5)], 2), page([], 2)]), "now")
        self.assertFalse(success)
        self.assertTrue(errors)
        self.assertEqual(talk["views"], 100)

    def test_partial_engagement_does_not_publish_partial_sum(self):
        talk = {"kind": "season", "mid": 1, "collection_id": 2, "likes": 80}
        client = FakeClient([page([video("a", 5), video("b", 7)], 2)],
                            {"a": {"stat": {"view": 5, "like": 2, "favorite": 3}}})
        success, errors = refresh(talk, client, "now")
        self.assertTrue(success)
        self.assertTrue(errors)
        self.assertEqual(talk["views"], 12)
        self.assertEqual(talk["likes"], 80)
        self.assertNotIn("favorites", talk)
        self.assertEqual(talk["stats_status"], "partial")

    def test_complete_collection_sums_all_metrics(self):
        for kind in ("series", "season"):
            talk = {"kind": kind, "mid": 1, "collection_id": 2}
            client = FakeClient([page([video("a", 5), video("b", 7)], 2)],
                                {key: {"stat": {"view": 5, "like": 2, "favorite": 3}}
                                 for key in ("a", "b")})
            success, errors = refresh(talk, client, "now")
            self.assertTrue(success)
            self.assertFalse(errors)
            self.assertEqual((talk["views"], talk["likes"], talk["favorites"]), (12, 4, 6))

    def test_failure_preserves_video_stats(self):
        talk = {"bvid": "a", "views": 100, "likes": 5, "favorites": 8}
        original = copy.deepcopy(talk)
        refresh(talk, FakeClient([]), "now")
        for key, value in original.items():
            self.assertEqual(talk[key], value)
        self.assertEqual(talk["stats_status"], "stale")

    @patch("update_talks.time.sleep")
    @patch("update_talks.urllib.request.urlopen")
    def test_412_stops_repeated_requests(self, urlopen, sleep):
        urlopen.side_effect = HTTPError("url", 412, "blocked", {}, None)
        client = Client()
        for bvid in ("a", "b"):
            with self.assertRaises(UpstreamError):
                client.get("/x/web-interface/wbi/view", bvid=bvid)
        self.assertEqual(urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
