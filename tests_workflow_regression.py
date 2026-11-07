"""Workflow regression tests. Uses temporary SQLite files and no live user data."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from fastapi import HTTPException
import database
import main
from models import ItemCreate, ItemUpdate, OrderAction, OrderCreate, RedeemRequest, ReviewAction


class WorkflowRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='campus-workflow-test-')
        self.original_db, self.original_uploads = database.DB_PATH, main.UPLOAD_DIR
        database.DB_PATH = Path(self.temp.name) / 'campus.db'
        main.UPLOAD_DIR = Path(self.temp.name) / 'uploads'
        database.init_db()
        main.refresh_category_cache()
        with database.db_session() as conn:
            people = [dict(r) for r in conn.execute('SELECT * FROM users ORDER BY id')]
        self.admin, self.seller, self.buyer, self.other = people[:4]

    def tearDown(self):
        database.DB_PATH, main.UPLOAD_DIR = self.original_db, self.original_uploads
        main.refresh_category_cache()
        self.temp.cleanup()

    def reserve(self):
        item = main.create_item(ItemCreate(title='Workflow item', category='教材', price=12), self.seller)
        order = main.create_order(OrderCreate(item_id=item['id']), self.buyer)
        return item, order

    def row(self, table, id):
        with database.db_session() as conn:
            return dict(conn.execute(f'SELECT * FROM {table} WHERE id = ?', (id,)).fetchone())

    def test_restart_preserves_cancelled_seed_reservation(self):
        main.cancel_order(1, OrderAction(), self.seller)
        self.assertEqual(self.row('items', 1)['status'], 'available')
        database.init_db()
        database.init_db()
        self.assertEqual(self.row('items', 1)['status'], 'available')
        self.assertEqual(self.row('orders', 1)['status'], 'cancelled')

    def test_reserved_item_cannot_be_edited_or_owner_removed(self):
        item, order = self.reserve()
        for action in [lambda: main.update_item(item['id'], ItemUpdate(title='Changed terms'), self.seller), lambda: main.offshelf_own_item(item['id'], self.seller)]:
            with self.assertRaises(HTTPException) as error: action()
            self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(self.row('items', item['id'])['title'], item['title'])
        self.assertEqual(self.row('orders', order['id'])['status'], 'reserved')

    def test_moderation_cancels_active_order_and_restore_allows_new_order(self):
        item, order = self.reserve()
        main.confirm_order(order['id'], OrderAction(), self.seller)
        main.admin_offshelf(item['id'], self.admin)
        self.assertEqual(self.row('orders', order['id'])['status'], 'cancelled')
        self.assertEqual(self.row('items', item['id'])['status'], 'offshelf')
        with self.assertRaises(HTTPException):
            main.complete_order(order['id'], OrderAction(pickup_code=order['pickup_code']), self.seller)
        main.admin_restore(item['id'], self.admin)
        new = main.create_order(OrderCreate(item_id=item['id']), self.other)
        self.assertNotEqual(new['id'], order['id'])

    def test_rejection_cancels_order_and_keeps_item_hidden(self):
        item, order = self.reserve()
        main.admin_review_item(item['id'], ReviewAction(approve=False, note='请核实描述'), self.admin)
        self.assertEqual(self.row('orders', order['id'])['status'], 'cancelled')
        self.assertEqual(self.row('items', item['id'])['review_status'], 'rejected')
        self.assertEqual(main.market_counts('Workflow item'), {})
        with self.assertRaises(HTTPException):
            main.create_order(OrderCreate(item_id=item['id']), self.other)

    def test_legacy_offshelf_order_cancellation_does_not_relist(self):
        item, order = self.reserve()
        with database.db_session() as conn:
            conn.execute("UPDATE items SET status = 'offshelf' WHERE id = ?", (item['id'],))
        main.cancel_order(order['id'], OrderAction(), self.buyer)
        self.assertEqual(self.row('items', item['id'])['status'], 'offshelf')

    def test_wrong_code_rolls_back_and_duplicate_completion_cannot_add_rewards(self):
        item, order = self.reserve()
        main.confirm_order(order['id'], OrderAction(), self.seller)
        before = self.row('users', self.seller['id'])['points']
        with self.assertRaises(HTTPException):
            main.complete_order(order['id'], OrderAction(pickup_code='wrong'), self.seller)
        self.assertEqual(self.row('orders', order['id'])['status'], 'confirmed')
        main.complete_order(order['id'], OrderAction(pickup_code=order['pickup_code']), self.seller)
        with self.assertRaises(HTTPException):
            main.complete_order(order['id'], OrderAction(pickup_code=order['pickup_code']), self.seller)
        self.assertEqual(self.row('items', item['id'])['cycle_count'], 1)
        self.assertEqual(self.row('users', self.seller['id'])['points'], before + 20)
        with self.assertRaises(HTTPException): main.admin_offshelf(item['id'], self.admin)
        with self.assertRaises(HTTPException): main.offshelf_own_item(item['id'], self.seller)

    def test_closed_order_hides_counterparty_contact(self):
        item, order = self.reserve()
        with database.db_session() as conn:
            conn.execute("UPDATE users SET contact = 'private-contact' WHERE id = ?", (self.seller['id'],))
        active = main.list_orders(self.buyer, 'buy')
        self.assertEqual(next(o for o in active if o['id'] == order['id'])['counterparty_contact'], 'private-contact')
        main.cancel_order(order['id'], OrderAction(), self.buyer)
        closed = next(o for o in main.list_orders(self.buyer, 'buy') if o['id'] == order['id'])
        self.assertIsNone(closed['counterparty_contact'])
        self.assertIsNone(closed['counterparty_name'])

    def test_concurrent_completion_only_rewards_once(self):
        item, order = self.reserve()
        main.confirm_order(order['id'], OrderAction(), self.seller)
        before = self.row('users', self.seller['id'])['points']
        def complete(user):
            try:
                main.complete_order(order['id'], OrderAction(pickup_code=order['pickup_code']), user)
                return 200
            except HTTPException as error: return error.status_code
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(complete, [self.seller, self.seller]))
        self.assertCountEqual(results, [200, 400])
        self.assertEqual(self.row('users', self.seller['id'])['points'], before + 20)
        self.assertEqual(self.row('items', item['id'])['cycle_count'], 1)

    def test_completion_and_moderation_cannot_produce_conflicting_states(self):
        item, order = self.reserve()
        main.confirm_order(order['id'], OrderAction(), self.seller)
        def invoke(fn):
            try: fn()
            except HTTPException as error: self.assertEqual(error.status_code, 400)
        with ThreadPoolExecutor(2) as pool:
            list(pool.map(invoke, [lambda: main.complete_order(order['id'], OrderAction(pickup_code=order['pickup_code']), self.seller), lambda: main.admin_offshelf(item['id'], self.admin)]))
        pair = (self.row('orders', order['id'])['status'], self.row('items', item['id'])['status'])
        self.assertIn(pair, [('completed', 'completed'), ('cancelled', 'offshelf')])

    def test_pickup_code_visible_only_to_active_order_buyer(self):
        item, order = self.reserve()
        self.assertTrue(order['pickup_code'])
        def find(user):
            return next(o for o in main.list_orders(user, None) if o['id'] == order['id'])
        self.assertEqual(find(self.buyer)['pickup_code'], order['pickup_code'])
        self.assertIsNone(find(self.seller)['pickup_code'])
        confirmed = main.confirm_order(order['id'], OrderAction(), self.seller)
        self.assertIsNone(confirmed['pickup_code'])
        self.assertEqual(find(self.buyer)['pickup_code'], order['pickup_code'])
        admin_order = next(o for o in main.admin_orders(self.admin, None, 200, 0) if o['id'] == order['id'])
        self.assertIsNone(admin_order['pickup_code'])
        # A nonparticipant has neither the order nor its credential.
        self.assertFalse(any(o['id'] == order['id'] for o in main.list_orders(self.other, None)))
        completed = main.complete_order(order['id'], OrderAction(pickup_code=order['pickup_code']), self.seller)
        self.assertIsNone(completed['pickup_code'])
        self.assertIsNone(find(self.buyer)['pickup_code'])
        self.assertIsNone(find(self.seller)['pickup_code'])
        second, cancelled_order = self.reserve()
        cancelled = main.cancel_order(cancelled_order['id'], OrderAction(), self.buyer)
        self.assertIsNone(cancelled['pickup_code'])

    def test_buyer_and_admin_cannot_complete_even_with_correct_code(self):
        item, order = self.reserve()
        main.confirm_order(order['id'], OrderAction(), self.seller)
        before = self.row('users', self.seller['id'])['points']
        for user in [self.buyer, self.other, self.admin]:
            with self.assertRaises(HTTPException) as error:
                main.complete_order(order['id'], OrderAction(pickup_code=order['pickup_code']), user)
            self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.row('orders', order['id'])['status'], 'confirmed')
        self.assertEqual(self.row('items', item['id'])['cycle_count'], 0)
        self.assertEqual(self.row('users', self.seller['id'])['points'], before)

    def test_policy_upgrade_rotates_exposed_codes_once(self):
        item, order = self.reserve()
        with database.db_session() as conn:
            conn.execute("DELETE FROM app_metadata WHERE key = 'pickup_policy'")
            conn.execute("UPDATE orders SET pickup_code = 'GC-OLD123' WHERE id = ?", (order['id'],))
        database.init_db()
        rotated = self.row('orders', order['id'])['pickup_code']
        self.assertNotEqual(rotated, 'GC-OLD123')
        database.init_db()
        self.assertEqual(self.row('orders', order['id'])['pickup_code'], rotated)
        main.confirm_order(order['id'], OrderAction(), self.seller)
        with self.assertRaises(HTTPException) as error:
            main.complete_order(order['id'], OrderAction(pickup_code='GC-OLD123'), self.seller)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(self.row('orders', order['id'])['status'], 'confirmed')
        main.complete_order(order['id'], OrderAction(pickup_code=rotated), self.seller)

    def test_redemption_receipt_is_private_and_survives_product_deletion(self):
        result = main.redeem(RedeemRequest(product_id=2), self.seller)
        receipts = main.my_redemptions(self.seller)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]['pickup_code'], result.pickup_code)
        self.assertEqual(main.my_redemptions(self.other), [])
        with database.db_session() as conn: conn.execute('DELETE FROM products WHERE id = 2')
        receipt = main.my_redemptions(self.seller)[0]
        self.assertIsNone(receipt['product_id'])
        self.assertEqual(receipt['product_name'], '食堂 5 元代金券')
        self.assertEqual(receipt['cost_points'], 60)

    def test_insufficient_points_leaves_no_receipt_or_stock_change(self):
        stock = self.row('products', 5)['stock']
        points = self.row('users', self.other['id'])['points']
        with self.assertRaises(HTTPException): main.redeem(RedeemRequest(product_id=5), self.other)
        self.assertEqual(main.my_redemptions(self.other), [])
        self.assertEqual(self.row('products', 5)['stock'], stock)
        self.assertEqual(self.row('users', self.other['id'])['points'], points)

    def test_concurrent_last_stock_creates_one_receipt(self):
        with database.db_session() as conn:
            conn.execute('UPDATE products SET stock = 1 WHERE id = 2')
        before = sum(self.row('users', u['id'])['points'] for u in [self.seller, self.buyer])
        def buy(user):
            try:
                main.redeem(RedeemRequest(product_id=2), user)
                return 200
            except HTTPException as error: return error.status_code
        with ThreadPoolExecutor(2) as pool: results = list(pool.map(buy, [self.seller, self.buyer]))
        self.assertCountEqual(results, [200, 400])
        self.assertEqual(self.row('products', 2)['stock'], 0)
        self.assertEqual(sum(len(main.my_redemptions(u)) for u in [self.seller, self.buyer]), 1)
        self.assertEqual(sum(self.row('users', u['id'])['points'] for u in [self.seller, self.buyer]), before - 60)


if __name__ == '__main__':
    unittest.main(verbosity=2)
