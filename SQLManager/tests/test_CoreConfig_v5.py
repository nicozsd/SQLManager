import os
import sys
import types
import unittest

sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
sys.modules.setdefault("pymysql", types.ModuleType("pymysql"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from SQLManager.CoreConfig import CoreConfig


class TestCoreConfigV5(unittest.TestCase):
    def setUp(self):
        CoreConfig.reset()

    def test_cache_backend_and_analytics_roundtrip(self):
        CoreConfig.configure(
            db_server='server',
            db_database='database',
            db_user='user',
            db_password='password',
            data_pulse_cache_backend='memory',
            data_pulse_cache_namespace='bi',
            load_from_env=False,
        )
        CoreConfig.configure_analytics({
            'enabled': True,
            'url_prefix': 'analytics',
            'cache_ttl': 180,
        })

        cache_config = CoreConfig.get_cache_config()
        analytics_config = CoreConfig.get_analytics_config()

        self.assertEqual(cache_config['backend'], 'memory')
        self.assertEqual(cache_config['namespace'], 'bi')
        self.assertTrue(analytics_config['enabled'])
        self.assertEqual(analytics_config['url_prefix'], 'analytics')
        self.assertEqual(analytics_config['cache_ttl'], 180)


if __name__ == '__main__':
    unittest.main()