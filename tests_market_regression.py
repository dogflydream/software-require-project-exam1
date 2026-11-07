"""Focused regressions for marketplace counts and item image editing.
Run: .venv/Scripts/python.exe tests_market_regression.py
Uses a temporary database and upload directory; no running server required.
"""
import base64
from pathlib import Path
import tempfile
import unittest

import database
import main
from models import ItemCreate, ItemUpdate


class MarketRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='campus-market-test-')
        self.original_db = database.DB_PATH
        self.original_uploads = main.UPLOAD_DIR
        database.DB_PATH = Path(self.temp.name) / 'campus.db'
        main.UPLOAD_DIR = Path(self.temp.name) / 'uploads'
        database.init_db()
        main.refresh_category_cache()
        with database.db_session() as conn:
            self.user = dict(conn.execute("SELECT * FROM users WHERE role != 'admin' LIMIT 1").fetchone())

    def tearDown(self):
        database.DB_PATH = self.original_db
        main.UPLOAD_DIR = self.original_uploads
        main.refresh_category_cache()
        self.temp.cleanup()

    def test_counts_cover_more_than_one_page_and_match_visibility(self):
        with database.db_session() as conn:
            for status, review, count in [('available', 'approved', 205), ('reserved', 'approved', 2), ('completed', 'approved', 1), ('offshelf', 'approved', 1), ('available', 'pending', 1), ('available', 'rejected', 1)]:
                conn.executemany('INSERT INTO items (owner_id, title, category, status, review_status, description) VALUES (?, ?, ?, ?, ?, ?)', [(self.user['id'], 'CountRegression', '教材', status, review, 'unique description') for _ in range(count)])
        self.assertEqual(main.market_counts('CountRegression'), {'教材': 207})
        self.assertEqual(main.market_counts('unique description'), {'教材': 207})
        self.assertEqual(main.market_counts('no-such-item'), {})
        with database.db_session() as conn:
            expected = dict(conn.execute("SELECT category, COUNT(*) FROM items WHERE status IN ('available', 'reserved') AND review_status = 'approved' GROUP BY category").fetchall())
        self.assertEqual(main.market_counts(None), expected)

    def test_upload_and_clear_image_preserve_review_flow(self):
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a6foAAAAASUVORK5CYII=')
        data_url = 'data:image/png;base64,' + base64.b64encode(png + b'\x00' * 1024).decode()
        self.assertGreater(len(data_url), 300)
        created = main.create_item(ItemCreate(title='Image regression', category='教材', image=data_url), self.user)
        image_path = main.UPLOAD_DIR / Path(created['image']).name
        self.assertEqual(image_path.read_bytes(), png + b'\x00' * 1024)
        updated = main.update_item(created['id'], ItemUpdate(image=''), self.user)
        self.assertIsNone(updated['image'])
        self.assertEqual(updated['review_status'], 'pending')
        self.assertEqual(main.market_counts('Image regression'), {})

    def test_upload_limit_and_type_remain_enforced(self):
        from fastapi import HTTPException
        for data_url in ['data:image/svg+xml;base64,PHN2Zz4=', 'data:image/png;base64,broken', 'data:image/png;base64,' + base64.b64encode(b'x' * (main.MAX_IMAGE_BYTES + 1)).decode()]:
            with self.assertRaises(HTTPException) as error:
                main.save_data_url(data_url)
            self.assertEqual(error.exception.status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
