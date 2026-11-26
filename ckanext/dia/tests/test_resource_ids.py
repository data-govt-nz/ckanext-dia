import unittest

from ckanext.dia.harvester.resource_ids import copy_resource_ids


class TestCopyResourceIds(unittest.TestCase):

    def test_matches_on_url_name_and_format(self):
        existing = [{'id': 'a', 'url': 'http://x/1', 'name': 'n', 'format': 'CSV'}]
        new = [{'url': 'http://x/1', 'name': 'n', 'format': 'CSV'}]
        self.assertEqual(copy_resource_ids(existing, new), 1)
        self.assertEqual(new[0]['id'], 'a')

    def test_falls_back_to_url_when_name_and_format_change(self):
        existing = [{'id': 'a', 'url': 'http://x/1', 'name': 'old', 'format': 'CSV'}]
        new = [{'url': 'http://x/1', 'name': 'new', 'format': 'XLS'}]
        copy_resource_ids(existing, new)
        self.assertEqual(new[0]['id'], 'a')

    def test_prefers_exact_match_over_url_only(self):
        existing = [
            {'id': 'a', 'url': 'http://x/1', 'name': 'one', 'format': 'CSV'},
            {'id': 'b', 'url': 'http://x/1', 'name': 'two', 'format': 'CSV'},
        ]
        new = [{'url': 'http://x/1', 'name': 'two', 'format': 'CSV'},
               {'url': 'http://x/1', 'name': 'one', 'format': 'CSV'}]
        copy_resource_ids(existing, new)
        self.assertEqual([r['id'] for r in new], ['b', 'a'])

    def test_each_existing_resource_matched_once(self):
        existing = [{'id': 'a', 'url': 'http://x/1', 'name': 'n', 'format': 'CSV'}]
        new = [{'url': 'http://x/1', 'name': 'n', 'format': 'CSV'},
               {'url': 'http://x/1', 'name': 'n', 'format': 'CSV'}]
        self.assertEqual(copy_resource_ids(existing, new), 1)
        self.assertEqual(new[0]['id'], 'a')
        self.assertNotIn('id', new[1])

    def test_unmatched_resource_gets_no_id(self):
        existing = [{'id': 'a', 'url': 'http://x/1', 'name': 'n', 'format': 'CSV'}]
        new = [{'url': 'http://x/2', 'name': 'n', 'format': 'CSV'}]
        self.assertEqual(copy_resource_ids(existing, new), 0)
        self.assertNotIn('id', new[0])

    def test_existing_id_on_new_resource_is_kept(self):
        existing = [{'id': 'a', 'url': 'http://x/1', 'name': 'n', 'format': 'CSV'}]
        new = [{'id': 'z', 'url': 'http://x/1', 'name': 'n', 'format': 'CSV'}]
        self.assertEqual(copy_resource_ids(existing, new), 0)
        self.assertEqual(new[0]['id'], 'z')


if __name__ == '__main__':
    unittest.main()
