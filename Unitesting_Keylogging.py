import unittest
import unittest.mock as mock
import tempfile
import os
import sqlite3
import json
from datetime import datetime, timedelta
from collections import Counter
from unittest.mock import MagicMock, patch, Mock
import time

# Mock external dependencies
import sys
sys.modules['customtkinter'] = MagicMock()
sys.modules['pynput'] = MagicMock()
sys.modules['pynput.keyboard'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()

# Now import your actual code
from app import (
    DatabaseManager, KeystrokeEvent, SimpleKeylogger, 
    PhantomTapGUI, PhantomTapAuthApp, PHANTOM_GREEN, 
    PHANTOM_GREEN_HOVER, PYNPUT_AVAILABLE
)


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.test_db.name
        self.test_db.close()
        
        # Create a real database manager with temp file
        self.db_manager = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        self.db_manager.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_create_table(self):
        """Test if users table is created"""
        self.db_manager.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        table = self.db_manager.cursor.fetchone()
        self.assertIsNotNone(table)
        self.assertEqual(table[0], 'users')
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password123"
        hashed = self.db_manager.hash_password(password)
        
        self.assertEqual(hashed, self.db_manager.hash_password(password))
        self.assertNotEqual(hashed, self.db_manager.hash_password("different"))
        self.assertEqual(len(hashed), 64)
    
    def test_register_user_success(self):
        """Test successful user registration"""
        result = self.db_manager.register_user("testuser", "password123")
        self.assertTrue(result)
        
        self.db_manager.cursor.execute(
            "SELECT * FROM users WHERE username='testuser'"
        )
        user = self.db_manager.cursor.fetchone()
        self.assertIsNotNone(user)
        self.assertEqual(user[1], "testuser")
    
    def test_register_user_duplicate(self):
        """Test registration with duplicate username"""
        self.db_manager.register_user("testuser", "password123")
        result = self.db_manager.register_user("testuser", "differentpass")
        self.assertFalse(result)
    
    def test_verify_login_success(self):
        """Test successful login verification"""
        self.db_manager.register_user("testuser", "password123")
        result = self.db_manager.verify_login("testuser", "password123")
        self.assertTrue(result)
    
    def test_verify_login_failure_wrong_password(self):
        """Test login with wrong password"""
        self.db_manager.register_user("testuser", "password123")
        result = self.db_manager.verify_login("testuser", "wrongpassword")
        self.assertFalse(result)
    
    def test_verify_login_failure_nonexistent_user(self):
        """Test login with non-existent user"""
        result = self.db_manager.verify_login("nonexistent", "password123")
        self.assertFalse(result)


class TestKeystrokeEvent(unittest.TestCase):
    """Test cases for KeystrokeEvent class"""
    
    def setUp(self):
        self.fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value = self.fixed_time
            self.event = KeystrokeEvent("a")
    
    def test_event_creation(self):
        """Test keystroke event initialization"""
        self.assertEqual(self.event.key, "a")
        self.assertEqual(self.event.timestamp, self.fixed_time)
        self.assertEqual(self.event.session_id, "")
    
    def test_get_formatted_time(self):
        """Test formatted time method"""
        formatted = self.event.get_formatted_time()
        self.assertEqual(formatted, "2024-01-01 12:00:00")
    
    def test_get_time_for_display(self):
        """Test display time method"""
        display_time = self.event.get_time_for_display()
        self.assertEqual(display_time, "12:00:00")


class TestSimpleKeylogger(unittest.TestCase):
    """Test cases for SimpleKeylogger class"""
    
    def setUp(self):
        self.keylogger = SimpleKeylogger(buffer_size=10)
        self.fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    
    def tearDown(self):
        if self.keylogger.is_logging:
            self.keylogger.stop()
    
    @patch('app.PYNPUT_AVAILABLE', True)
    @patch('app.keyboard.Listener')
    def test_start_logging_success(self, mock_listener):
        """Test successful start of logging"""
        mock_listener.return_value.start = MagicMock()
        
        result = self.keylogger.start("test_session")
        
        self.assertTrue(result)
        self.assertTrue(self.keylogger.is_logging)
        self.assertEqual(self.keylogger.session_name, "test_session")
        self.assertTrue(self.keylogger.session_id.startswith("test_session_"))
        self.assertIsNotNone(self.keylogger.session_start)
        self.assertEqual(self.keylogger.total_keys, 0)
        self.assertEqual(self.keylogger.words_typed, 0)
        mock_listener.assert_called_once()
    
    @patch('app.PYNPUT_AVAILABLE', False)
    def test_start_logging_pynput_not_available(self):
        """Test start logging when pynput is not available"""
        result = self.keylogger.start("test_session")
        self.assertFalse(result)
        self.assertFalse(self.keylogger.is_logging)
    
    def test_stop_logging(self):
        """Test stopping logging"""
        self.keylogger.is_logging = True
        self.keylogger.listener = MagicMock()
        
        self.keylogger.stop()
        
        self.assertFalse(self.keylogger.is_logging)
        self.keylogger.listener.stop.assert_called_once()
    
    def test_clear_logs_when_logging(self):
        """Test clearing logs when logging is active"""
        self.keylogger.is_logging = True
        self.keylogger.buffer = [KeystrokeEvent("a")]
        self.keylogger.total_keys = 10
        self.keylogger.words_typed = 5
        self.keylogger.session_start = datetime.now()
        self.keylogger.session_name = "test"
        self.keylogger.session_id = "test_123"
        
        self.keylogger.clear_logs()
        
        self.assertEqual(self.keylogger.buffer, [])
        self.assertEqual(self.keylogger.total_keys, 0)
        self.assertEqual(self.keylogger.words_typed, 0)
        self.assertIsNotNone(self.keylogger.session_start)
        self.assertNotEqual(self.keylogger.session_name, "")
    
    def test_clear_logs_when_not_logging(self):
        """Test clearing logs when not logging"""
        self.keylogger.is_logging = False
        self.keylogger.buffer = [KeystrokeEvent("a")]
        self.keylogger.total_keys = 10
        self.keylogger.words_typed = 5
        self.keylogger.session_start = datetime.now()
        self.keylogger.session_name = "test"
        self.keylogger.session_id = "test_123"
        
        self.keylogger.clear_logs()
        
        self.assertEqual(self.keylogger.buffer, [])
        self.assertEqual(self.keylogger.total_keys, 0)
        self.assertEqual(self.keylogger.words_typed, 0)
        self.assertIsNone(self.keylogger.session_start)
        self.assertEqual(self.keylogger.session_name, "")
        self.assertEqual(self.keylogger.session_id, "")
    
    def test_convert_key_character(self):
        """Test converting character keys"""
        class MockKey:
            def __init__(self, char):
                self.char = char
        
        mock_key = MockKey('a')
        result = self.keylogger._convert_key(mock_key)
        self.assertEqual(result, 'a')
    
    def test_convert_key_special(self):
        """Test converting special keys"""
        class MockKey:
            def __init__(self, name):
                self.name = name
                self.char = None
        
        mock_key = MockKey('space')
        result = self.keylogger._convert_key(mock_key)
        self.assertEqual(result, '[SPACE]')
    
    def test_convert_key_backspace(self):
        """Test converting backspace"""
        class MockKey:
            def __init__(self):
                self.char = '\x08'
        
        mock_key = MockKey()
        result = self.keylogger._convert_key(mock_key)
        self.assertEqual(result, '[BACKSPACE]')
    
    def test_convert_key_enter(self):
        """Test converting enter"""
        class MockKey:
            def __init__(self):
                self.char = '\n'
        
        mock_key = MockKey()
        result = self.keylogger._convert_key(mock_key)
        self.assertEqual(result, '[ENTER]')
    
    def test_convert_key_tab(self):
        """Test converting tab"""
        class MockKey:
            def __init__(self):
                self.char = '\t'
        
        mock_key = MockKey()
        result = self.keylogger._convert_key(mock_key)
        self.assertEqual(result, '[TAB]')
    
    def test_convert_key_space(self):
        """Test converting space"""
        class MockKey:
            def __init__(self):
                self.char = ' '
        
        mock_key = MockKey()
        result = self.keylogger._convert_key(mock_key)
        self.assertEqual(result, '[SPACE]')
    
    def test_convert_key_unknown(self):
        """Test converting unknown key - based on actual code behavior"""
        class MockKey:
            def __str__(self):
                return "<unknown>"
        
        mock_key = MockKey()
        result = self.keylogger._convert_key(mock_key)
        self.assertEqual(result, '<unknown>')
    
    @patch('app.datetime')
    def test_on_press_normal_key(self, mock_datetime):
        """Test on_press with normal key"""
        self.keylogger.is_logging = True
        mock_datetime.now.return_value = self.fixed_time
        
        class MockKey:
            def __init__(self):
                self.char = 'a'
        
        mock_key = MockKey()
        
        self.keylogger._on_press(mock_key)
        
        self.assertEqual(len(self.keylogger.buffer), 1)
        self.assertEqual(self.keylogger.total_keys, 1)
        self.assertEqual(self.keylogger.key_frequency['a'], 1)
        self.assertEqual(self.keylogger.words_typed, 0)
    
    @patch('app.datetime')
    def test_on_press_space_key(self, mock_datetime):
        """Test on_press with space key"""
        self.keylogger.is_logging = True
        mock_datetime.now.return_value = self.fixed_time
        
        class MockKey:
            def __init__(self):
                self.char = ' '
        
        mock_key = MockKey()
        
        self.keylogger._on_press(mock_key)
        
        self.assertEqual(len(self.keylogger.buffer), 1)
        self.assertEqual(self.keylogger.total_keys, 1)
        self.assertEqual(self.keylogger.key_frequency['[SPACE]'], 1)
        self.assertEqual(self.keylogger.words_typed, 1)
        self.assertTrue(self.keylogger.last_key_was_space)
    
    def test_on_press_not_logging(self):
        """Test on_press when logging is False"""
        self.keylogger.is_logging = False
        initial_buffer_len = len(self.keylogger.buffer)
        
        class MockKey:
            def __init__(self):
                self.char = 'a'
        
        mock_key = MockKey()
        self.keylogger._on_press(mock_key)
        
        self.assertEqual(len(self.keylogger.buffer), initial_buffer_len)
    
    def test_buffer_size_limit(self):
        """Test buffer size limit enforcement"""
        self.keylogger.is_logging = True
        self.keylogger.buffer_size = 3
        
        class MockKey:
            def __init__(self, char):
                self.char = char
        
        for char in ['a', 'b', 'c', 'd', 'e']:
            self.keylogger._on_press(MockKey(char))
        
        self.assertEqual(len(self.keylogger.buffer), 3)
        self.assertEqual([event.key for event in self.keylogger.buffer], ['c', 'd', 'e'])
    
    def test_get_statistics_basic(self):
        """Test getting basic statistics"""
        self.keylogger.total_keys = 100
        self.keylogger.words_typed = 20
        self.keylogger.session_name = "test"
        self.keylogger.session_id = "test_123"
        self.keylogger.session_start = datetime.now() - timedelta(minutes=5)
        self.keylogger.key_frequency = Counter({"a": 50, "b": 30, "c": 20})
        self.keylogger.hourly_activity = [5] * 24
        
        stats = self.keylogger.get_statistics()
        
        self.assertEqual(stats['total_keys'], 100)
        self.assertEqual(stats['words_typed'], 20)
        self.assertEqual(stats['session_name'], "test")
        self.assertEqual(stats['session_id'], "test_123")
        self.assertIn('session_duration', stats)
        self.assertIn('keys_per_minute', stats)
        self.assertIn('words_per_minute', stats)
    
    def test_get_statistics_no_session(self):
        """Test statistics when no session exists"""
        self.keylogger.session_start = None
        
        stats = self.keylogger.get_statistics()
        
        self.assertNotIn('session_duration', stats)
        self.assertNotIn('keys_per_minute', stats)
        self.assertNotIn('words_per_minute', stats)
    
    def test_get_typing_accuracy_perfect(self):
        """Test typing accuracy with no backspaces"""
        self.keylogger.total_keys = 100
        for i in range(100):
            event = KeystrokeEvent('a')
            self.keylogger.buffer.append(event)
        
        accuracy = self.keylogger.get_typing_accuracy()
        self.assertEqual(accuracy, 100.0)
    
    def test_get_typing_accuracy_with_backspaces(self):
        """Test typing accuracy with backspaces"""
        self.keylogger.total_keys = 100
        for i in range(80):
            event = KeystrokeEvent('a')
            self.keylogger.buffer.append(event)
        for i in range(20):
            event = KeystrokeEvent('[BACKSPACE]')
            self.keylogger.buffer.append(event)
        
        accuracy = self.keylogger.get_typing_accuracy()
        expected_accuracy = 100 - (20/100 * 100)
        self.assertEqual(accuracy, 80.0)
    
    def test_get_typing_accuracy_no_keys(self):
        """Test typing accuracy with no keys - matches actual code behavior"""
        self.keylogger.total_keys = 0
        self.keylogger.buffer = []
        
        accuracy = self.keylogger.get_typing_accuracy()
        self.assertEqual(accuracy, 0)
    
    def test_reconstruct_text_simple(self):
        """Test text reconstruction with simple input"""
        events = [
            KeystrokeEvent('H'),
            KeystrokeEvent('e'),
            KeystrokeEvent('l'),
            KeystrokeEvent('l'),
            KeystrokeEvent('o'),
            KeystrokeEvent('[SPACE]'),
            KeystrokeEvent('W'),
            KeystrokeEvent('o'),
            KeystrokeEvent('r'),
            KeystrokeEvent('l'),
            KeystrokeEvent('d'),
            KeystrokeEvent('[ENTER]')
        ]
        self.keylogger.buffer = events
        
        reconstructed = self.keylogger._reconstruct_text()
        self.assertEqual(reconstructed, ['Hello World'])
    
    def test_reconstruct_text_with_backspace(self):
        """Test text reconstruction with backspace - matches actual code behavior"""
        events = [
            KeystrokeEvent('H'),
            KeystrokeEvent('e'),
            KeystrokeEvent('l'),
            KeystrokeEvent('l'),
            KeystrokeEvent('o'),
            KeystrokeEvent('[BACKSPACE]'),
            KeystrokeEvent('p')
        ]
        self.keylogger.buffer = events
        
        reconstructed = self.keylogger._reconstruct_text()
        self.assertEqual(reconstructed, ['Hellp'])
    
    def test_reconstruct_text_with_tab(self):
        """Test text reconstruction with tab"""
        events = [
            KeystrokeEvent('[TAB]'),
            KeystrokeEvent('I'),
            KeystrokeEvent('n'),
            KeystrokeEvent('d'),
            KeystrokeEvent('e'),
            KeystrokeEvent('n'),
            KeystrokeEvent('t')
        ]
        self.keylogger.buffer = events
        
        reconstructed = self.keylogger._reconstruct_text()
        self.assertEqual(reconstructed, ['\tIndent'])
    
    def test_reconstruct_text_multiple_lines(self):
        """Test text reconstruction with multiple lines"""
        events = [
            KeystrokeEvent('L'),
            KeystrokeEvent('i'),
            KeystrokeEvent('n'),
            KeystrokeEvent('e'),
            KeystrokeEvent('1'),
            KeystrokeEvent('[ENTER]'),
            KeystrokeEvent('L'),
            KeystrokeEvent('i'),
            KeystrokeEvent('n'),
            KeystrokeEvent('e'),
            KeystrokeEvent('2')
        ]
        self.keylogger.buffer = events
        
        reconstructed = self.keylogger._reconstruct_text()
        self.assertEqual(reconstructed, ['Line1', 'Line2'])
    
    @patch('builtins.open', new_callable=mock.mock_open)
    @patch('json.dump')
    def test_save_to_json(self, mock_json_dump, mock_open):
        """Test saving to JSON file"""
        self.keylogger.session_name = "test"
        self.keylogger.session_id = "test_123"
        self.keylogger.session_start = datetime(2024, 1, 1, 12, 0, 0)
        self.keylogger.total_keys = 5
        self.keylogger.words_typed = 1
        
        events = [
            KeystrokeEvent('H'),
            KeystrokeEvent('e'),
            KeystrokeEvent('l'),
            KeystrokeEvent('l'),
            KeystrokeEvent('o')
        ]
        for event in events:
            event.timestamp = datetime(2024, 1, 1, 12, 0, 0)
        self.keylogger.buffer = events
        
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            result = self.keylogger.save_to_json("test.json")
        
        self.assertTrue(result)
        mock_open.assert_called_once_with("test.json", 'w', encoding='utf-8')
    
    @patch('builtins.open', new_callable=mock.mock_open)
    def test_save_to_txt(self, mock_open):
        """Test saving to TXT file"""
        self.keylogger.session_name = "test"
        self.keylogger.session_id = "test_123"
        self.keylogger.session_start = datetime(2024, 1, 1, 12, 0, 0)
        self.keylogger.total_keys = 5
        self.keylogger.words_typed = 1
        
        events = [
            KeystrokeEvent('H'),
            KeystrokeEvent('e'),
            KeystrokeEvent('l'),
            KeystrokeEvent('l'),
            KeystrokeEvent('o')
        ]
        self.keylogger.buffer = events
        
        result = self.keylogger.save_to_txt("test.txt")
        
        self.assertTrue(result)
        mock_open.assert_called_once_with("test.txt", 'w', encoding='utf-8')
    
    @patch('builtins.open', new_callable=mock.mock_open)
    def test_save_to_csv(self, mock_open):
        """Test saving to CSV file"""
        self.keylogger.session_name = "test"
        self.keylogger.session_id = "test_123"
        self.keylogger.session_start = datetime(2024, 1, 1, 12, 0, 0)
        self.keylogger.total_keys = 5
        self.keylogger.words_typed = 1
        
        events = [
            KeystrokeEvent('H'),
            KeystrokeEvent('e'),
            KeystrokeEvent('l'),
            KeystrokeEvent('l'),
            KeystrokeEvent('o')
        ]
        self.keylogger.buffer = events
        
        result = self.keylogger.save_to_csv("test.csv")
        
        self.assertTrue(result)
        mock_open.assert_called_once_with("test.csv", 'w', newline='', encoding='utf-8')
    
    def test_get_key_display(self):
        """Test key display method"""
        self.assertEqual(self.keylogger._get_key_display('[SPACE]'), '[SPACE]')
        self.assertEqual(self.keylogger._get_key_display('[ENTER]'), '[ENTER]')
        self.assertEqual(self.keylogger._get_key_display('a'), 'a')
        self.assertEqual(self.keylogger._get_key_display('[CTRL]'), '[CTRL]')


def print_test_summary(test_result):
    """Print a beautiful test summary"""
    print("\n" + "="*60)
    print(" 📊 PHANTOMTAP TEST SUMMARY ")
    print("="*60)
    
    print(f"\n 📋 Test Categories:")
    print(f"    • DatabaseManager Tests: 7 tests")
    print(f"    • KeystrokeEvent Tests: 3 tests")
    print(f"    • SimpleKeylogger Tests: 29 tests")
    
    print(f"\n ✅ RESULTS:")
    print(f"    • Total Tests Run: {test_result.testsRun}")
    print(f"    • Passed: {test_result.testsRun - len(test_result.failures) - len(test_result.errors)}")
    print(f"    • Failed: {len(test_result.failures)}")
    print(f"    • Errors: {len(test_result.errors)}")
    
    if len(test_result.failures) == 0 and len(test_result.errors) == 0:

        print("   ✅✅✅ ALL TESTS PASSED! ✅✅✅")
        
        print("\n   Your PhantomTap keylogger is working perfectly!")
    else:
        print("\n " + "❌"*10)
        print("   ❌ SOME TESTS FAILED! ❌")
        print(" " + "❌"*10)
        
        if test_result.failures:
            print("\n   Failed Tests:")
            for failure in test_result.failures:
                print(f"   • {failure[0]._testMethodName}")
        
        if test_result.errors:
            print("\n   Errors:")
            for error in test_result.errors:
                print(f"   • {error[0]._testMethodName}")
    
    print("\n" + "="*60)
    print(" 🏁 TEST EXECUTION COMPLETE ")
    print("="*60 + "\n")


def run_tests_with_summary():
    """Run tests and print summary"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseManager))
    suite.addTests(loader.loadTestsFromTestCase(TestKeystrokeEvent))
    suite.addTests(loader.loadTestsFromTestCase(TestSimpleKeylogger))
    
    # Run tests with custom result
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print_test_summary(result)
    
    return result


if __name__ == '__main__':
    start_time = time.time()
    result = run_tests_with_summary()
    end_time = time.time()
    
    print(f" ⏱️  Execution Time: {end_time - start_time:.2f} seconds")
    
    # Return appropriate exit code
    sys.exit(0 if result.wasSuccessful() else 1)