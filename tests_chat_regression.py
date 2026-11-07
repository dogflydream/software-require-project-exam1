"""Conversation permissions, persistence, pagination and privacy regressions."""
from concurrent.futures import ThreadPoolExecutor
import unittest
from fastapi import HTTPException
from pydantic import ValidationError
import database
import main
from models import MessageCreate, MessageRead, ProfileUpdate, OrderAction, ItemUpdate
import tests_workflow_regression as workflow

class ChatRegression(unittest.TestCase):
    setUp = workflow.WorkflowRegression.setUp
    tearDown = workflow.WorkflowRegression.tearDown
    reserve = workflow.WorkflowRegression.reserve
    row = workflow.WorkflowRegression.row

    def message(self, order, user, text='明天下午图书馆门口交接可以吗？', nonce='message-0001'):
        return main.send_message(order['id'], MessageCreate(content=text, client_nonce=nonce), user)

    def history(self, order, user, before=0, after=0, limit=50):
        return main.order_messages(order['id'], user, before, after, limit)

    def test_contact_retired_and_legacy_data_cleared(self):
        with self.assertRaises(ValidationError): ProfileUpdate.model_validate({'contact':'private'})
        with database.db_session() as conn:
            conn.execute('ALTER TABLE users ADD COLUMN contact TEXT')
            conn.execute("UPDATE users SET contact = 'legacy-private'")
            conn.execute("DELETE FROM app_metadata WHERE key = 'contact_retired'")
        database.init_db()
        self.assertIsNone(self.row('users', self.seller['id'])['contact'])
        summary = main.my_summary(self.row('users', self.seller['id']))
        self.assertNotIn('contact', summary['user'])
        self.assertNotIn('password_hash', summary['user'])

    def test_public_profile_does_not_expose_pending_item_content(self):
        item, order = self.reserve()
        main.cancel_order(order['id'], OrderAction(), self.seller)
        main.update_item(item['id'], ItemUpdate(description='private review content'), self.seller)
        profile = main.user_profile(self.seller['id'])
        self.assertFalse(any(i['id'] == item['id'] for i in profile['items']))

    def test_only_participants_can_read_send_or_mark_read(self):
        item, order = self.reserve()
        message = self.message(order, self.buyer)
        for stranger in [self.other, self.admin]:
            self.assertFalse(any(c['order_id'] == order['id'] for c in main.conversations(stranger)))
            for action in [lambda: self.history(order, stranger), lambda: self.message(order, stranger), lambda: main.read_messages(order['id'], MessageRead(last_message_id=message['id']), stranger)]:
                with self.assertRaises(HTTPException) as error: action()
                self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(self.history(order, self.seller)['messages'][0]['sender_id'], self.buyer['id'])

    def test_unread_counts_and_read_cursor_never_move_backwards(self):
        item, order = self.reserve()
        one = self.message(order, self.buyer)
        two = self.message(order, self.buyer, '可以下午三点见', 'message-0002')
        def unread(user): return next(c for c in main.conversations(user) if c['order_id'] == order['id'])['unread_count']
        self.assertEqual(unread(self.seller), 2)
        self.assertEqual(unread(self.buyer), 0)
        main.read_messages(order['id'], MessageRead(last_message_id=two['id']), self.seller)
        main.read_messages(order['id'], MessageRead(last_message_id=one['id']), self.seller)
        self.assertEqual(unread(self.seller), 0)
        item2, other_order = self.reserve()
        other = self.message(other_order, self.buyer)
        with self.assertRaises(HTTPException): main.read_messages(order['id'], MessageRead(last_message_id=other['id']), self.seller)

    def test_retry_and_concurrent_retry_do_not_duplicate_message(self):
        item, order = self.reserve()
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.message(order, self.buyer), range(2)))
        self.assertEqual(results[0]['id'], results[1]['id'])
        self.assertEqual(len(self.history(order, self.buyer)['messages']), 1)
        with self.assertRaises(HTTPException) as error: self.message(order, self.buyer, 'changed payload')
        self.assertEqual(error.exception.status_code, 409)

    def test_cursor_pagination_preserves_order_without_duplicates(self):
        item, order = self.reserve()
        with database.db_session() as conn:
            conn.executemany('INSERT INTO order_messages (order_id,sender_id,content,client_nonce) VALUES (?,?,?,?)', [(order['id'],self.buyer['id'],str(n),f'bulk-{n:08}') for n in range(120)])
        newest = self.history(order, self.seller)
        self.assertEqual([m['content'] for m in newest['messages']], [str(n) for n in range(70,120)])
        self.assertTrue(newest['has_more'])
        older = self.history(order,self.seller,before=newest['messages'][0]['id'])
        self.assertEqual([m['content'] for m in older['messages']], [str(n) for n in range(20,70)])
        incremental = self.history(order,self.seller,after=older['messages'][-1]['id'])
        self.assertEqual([m['id'] for m in incremental['messages']], [m['id'] for m in newest['messages']])

    def test_closed_order_readonly_and_history_survives_restart(self):
        item, order = self.reserve()
        message = self.message(order,self.buyer)
        main.cancel_order(order['id'],OrderAction(),self.seller)
        with self.assertRaises(HTTPException) as error: self.message(order,self.seller,nonce='message-0002')
        self.assertEqual(error.exception.status_code,400)
        database.init_db()
        self.assertEqual(self.history(order,self.buyer)['messages'][0]['id'],message['id'])

    def test_message_validation_and_rate_limit(self):
        for content in ['   ', 'x'*1001]:
            with self.assertRaises(ValidationError): MessageCreate(content=content,client_nonce='validate-0001')
        item, order = self.reserve()
        for n in range(20): self.message(order,self.buyer,str(n),f'rate-{n:08}')
        with self.assertRaises(HTTPException) as error: self.message(order,self.buyer,'too fast','rate-over-0001')
        self.assertEqual(error.exception.status_code,429)
        # Retries remain idempotent even when the rate limit has been reached.
        self.assertEqual(self.message(order,self.buyer,'0','rate-00000000')['content'],'0')

if __name__ == '__main__': unittest.main(verbosity=2)
