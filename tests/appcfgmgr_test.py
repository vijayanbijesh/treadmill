"""
Unit test for appcfgmgr - configuring node apps
"""

import os
import shutil
import tempfile
import time
import unittest

# Disable W0611: Unused import
import tests.treadmill_test_deps  # pylint: disable=W0611

import mock

import treadmill
from treadmill import appcfgmgr
from treadmill import fs


class AppCfgMgrTest(unittest.TestCase):
    """Mock test for treadmill.appcfgmgr.AppCfgMgr."""

    @mock.patch('treadmill.appmgr.AppEnvironment', mock.Mock(autospec=True))
    @mock.patch('treadmill.watchdog.Watchdog', mock.Mock(autospec=True))
    def setUp(self):
        self.root = tempfile.mkdtemp()

        self.cache = os.path.join(self.root, 'cache')
        self.apps = os.path.join(self.root, 'apps')
        self.running = os.path.join(self.root, 'running')
        self.cleanup = os.path.join(self.root, 'cleanup')

        for tmp_dir in [self.cache, self.apps, self.running, self.cleanup]:
            os.mkdir(tmp_dir)

        self.appcfgmgr = appcfgmgr.AppCfgMgr(root=self.root)
        self.appcfgmgr.tm_env.root = self.root
        self.appcfgmgr.tm_env.cache_dir = self.cache
        self.appcfgmgr.tm_env.apps_dir = self.apps
        self.appcfgmgr.tm_env.running_dir = self.running
        self.appcfgmgr.tm_env.cleanup_dir = self.cleanup

    def tearDown(self):
        if self.root and os.path.isdir(self.root):
            shutil.rmtree(self.root)

    @mock.patch('treadmill.appmgr.configure.configure',
                mock.Mock(return_value='/test/foo'))
    @mock.patch('treadmill.appmgr.configure.schedule', mock.Mock())
    def test__configure(self):
        """Tests application configuration event."""
        # Access to a protected member _configure of a client class
        # pylint: disable=W0212

        self.appcfgmgr._configure('foo#1')

        treadmill.appmgr.configure.configure.assert_called_with(
            self.appcfgmgr.tm_env,
            os.path.join(self.cache, 'foo#1'),
        )
        treadmill.appmgr.configure.schedule.assert_called_with(
            '/test/foo',
            os.path.join(self.running, 'foo#1'),
        )

    @mock.patch('treadmill.appmgr.abort.abort', mock.Mock())
    @mock.patch('treadmill.appmgr.configure.configure', mock.Mock())
    @mock.patch('treadmill.fs.rm_safe', mock.Mock())
    def test__configure_failure(self):
        """Tests application configuration failure event."""
        # Access to a protected member _configure of a client class
        # pylint: disable=W0212

        treadmill.appmgr.configure.configure.side_effect = Exception('Boom')

        self.appcfgmgr._configure('foo#1')

        treadmill.appmgr.abort.abort.assert_called_with(
            self.appcfgmgr.tm_env,
            os.path.join(self.cache, 'foo#1'),
            mock.ANY,
        )
        treadmill.fs.rm_safe.assert_called_with(
            os.path.join(self.cache, 'foo#1')
        )

    @mock.patch('treadmill.subproc.check_call', mock.Mock())
    @mock.patch('treadmill.utils.rootdir',
                mock.Mock(return_value='/treadmill'))
    def test__terminate(self):
        """Tests terminate removes /running links.
        """
        # Access to a protected member _terminate of a client class
        # pylint: disable=W0212

        fs.mkdir_safe(os.path.join(self.apps, 'proid.app-0_1234'))
        os.symlink(
            os.path.join(self.apps, 'proid.app-0_1234'),
            os.path.join(self.running, 'proid.app#0'),
        )

        self.appcfgmgr._terminate('proid.app#0')

        self.assertFalse(
            os.path.exists(os.path.join(self.running, 'proid.app#0'))
        )
        self.assertEquals(
            os.readlink(os.path.join(self.cleanup, 'proid.app-0_1234')),
            os.path.join(self.apps, 'proid.app-0_1234')
        )

    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._configure', mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor',
                mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._terminate', mock.Mock())
    @mock.patch('treadmill.appmgr.eventfile_unique_name', mock.Mock())
    def test__synchronize_noop(self):
        """Tests synchronize when there is nothing to do.
        """
        # Access to a protected member _synchronize of a client class
        # pylint: disable=W0212
        def _fake_unique_name(name):
            """Fake container unique name function.
            """
            uniquename = os.path.basename(name)
            uniquename = uniquename.replace('#', '-')
            uniquename += '_1234'
            return uniquename
        treadmill.appmgr.eventfile_unique_name.side_effect = _fake_unique_name
        for app in ('proid.app#0', 'proid.app#1', 'proid.app#2'):
            # Create cache/ entry
            with open(os.path.join(self.cache, app), 'w') as _f:
                pass
            # Create app/ dir
            uniquename = _fake_unique_name(app)
            os.mkdir(os.path.join(self.apps, uniquename))
            # Create running/ symlink
            os.symlink(os.path.join(self.apps, uniquename),
                       os.path.join(self.running, app))

        self.appcfgmgr._synchronize()

        self.assertFalse(treadmill.appcfgmgr.AppCfgMgr._terminate.called)
        # We always configure
        treadmill.appcfgmgr.AppCfgMgr._configure.assert_has_calls(
            [
                mock.call('proid.app#0'),
                mock.call('proid.app#1'),
                mock.call('proid.app#2'),
            ],
            any_order=True
        )
        treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor.assert_called_with(
            instance_names=set(['proid.app#0', 'proid.app#1', 'proid.app#2'])
        )

    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._configure', mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor',
                mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._terminate', mock.Mock())
    @mock.patch('treadmill.appmgr.eventfile_unique_name', mock.Mock())
    def test__synchronize_config(self):
        """Tests synchronize when there are apps to configure.
        """
        # Access to a protected member _synchronize of a client class
        # pylint: disable=W0212

        def _fake_unique_name(name):
            """Fake container unique name function.
            """
            uniquename = os.path.basename(name)
            uniquename = uniquename.replace('#', '-')
            uniquename += '_1234'
            return uniquename
        treadmill.appmgr.eventfile_unique_name.side_effect = _fake_unique_name
        for app in ('proid.app#0', 'proid.app#1', 'proid.app#2'):
            # Create cache/ entry
            with open(os.path.join(self.cache, app), 'w') as _f:
                pass
            uniquename = _fake_unique_name(app)
            os.mkdir(os.path.join(self.apps, uniquename))

        self.appcfgmgr._synchronize()

        treadmill.appcfgmgr.AppCfgMgr._configure.assert_has_calls(
            [
                mock.call('proid.app#0'),
                mock.call('proid.app#1'),
                mock.call('proid.app#2')
            ],
            any_order=True,
        )
        self.assertFalse(treadmill.appcfgmgr.AppCfgMgr._terminate.called)
        treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor.assert_called_with(
            instance_names=set(['proid.app#0', 'proid.app#1', 'proid.app#2'])
        )

    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._configure', mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._terminate', mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor',
                mock.Mock())
    @mock.patch('treadmill.appmgr.eventfile_unique_name', mock.Mock())
    def test__synchronize_term(self):
        """Tests synchronize when there are apps to terminate.
        """
        # Access to a protected member _synchronize of a client class
        # pylint: disable=W0212

        def _fake_unique_name(name):
            """Fake container unique name function.
            """
            uniquename = os.path.basename(name)
            uniquename = uniquename.replace('#', '-')
            uniquename += '_1234'
            return uniquename
        treadmill.appmgr.eventfile_unique_name.side_effect = _fake_unique_name
        for app in ('proid.app#0', 'proid.app#1', 'proid.app#2'):
            # Create app/ dir
            uniquename = _fake_unique_name(app)
            os.mkdir(os.path.join(self.apps, uniquename))
            # Create running/ symlink
            os.symlink(os.path.join(self.apps, uniquename),
                       os.path.join(self.running, app))

        self.appcfgmgr._synchronize()

        self.assertFalse(treadmill.appcfgmgr.AppCfgMgr._configure.called)
        treadmill.appcfgmgr.AppCfgMgr._terminate.assert_has_calls(
            [
                mock.call('proid.app#0'),
                mock.call('proid.app#1'),
                mock.call('proid.app#2')
            ],
            any_order=True,
        )
        treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor.assert_called_with(
            instance_names=set([])
        )

    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._configure', mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor',
                mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._terminate', mock.Mock())
    @mock.patch('treadmill.appmgr.eventfile_unique_name', mock.Mock())
    def test__synchronize_with_files(self):
        """Tests that sync leaves files that are not symlinks as is.
        """
        # Access to a protected member _synchronize of a client class
        # pylint: disable=W0212

        with open(os.path.join(self.running, 'xxx'), 'w') as _f:
            pass

        self.appcfgmgr._synchronize()

        # xxx shouldn't have been touched.
        self.assertTrue(os.path.exists(os.path.join(self.running, 'xxx')))
        self.assertFalse(treadmill.appcfgmgr.AppCfgMgr._terminate.called)
        self.assertFalse(treadmill.appcfgmgr.AppCfgMgr._configure.called)
        treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor.assert_called_with(
            instance_names=set([])
        )

    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._configure', mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor',
                mock.Mock())
    @mock.patch('treadmill.appcfgmgr.AppCfgMgr._terminate', mock.Mock())
    @mock.patch('treadmill.appmgr.eventfile_unique_name', mock.Mock())
    def test__synchronize_broken_link(self):
        """Tests that sync cleans up broken symlinks.
        """
        # Access to a protected member _synchronize of a client class
        # pylint: disable=W0212

        def _fake_unique_name(name):
            """Fake container unique name function.
            """
            uniquename = os.path.basename(name)
            uniquename = uniquename.replace('#', '-')
            uniquename += '_1234'
            return uniquename
        treadmill.appmgr.eventfile_unique_name.side_effect = _fake_unique_name
        # Create cache/ entry
        with open(os.path.join(self.cache, 'foo#1'), 'w') as _f:
            pass
        # Create a broken running/ symlink
        os.symlink(os.path.join(self.apps, 'foo-1_1234'),
                   os.path.join(self.running, 'foo#1'))

        self.appcfgmgr._synchronize()

        self.assertFalse(treadmill.appcfgmgr.AppCfgMgr._terminate.called)
        treadmill.appcfgmgr.AppCfgMgr._configure.assert_called_with(
            'foo#1'
        )
        treadmill.appcfgmgr.AppCfgMgr._refresh_supervisor.assert_called_with(
            instance_names=set(['foo#1'])
        )

    @mock.patch('time.sleep', mock.Mock())
    @mock.patch('treadmill.subproc.call',
                mock.Mock(side_effect=[1, 1, 0, 1, 0]))
    @mock.patch('treadmill.subproc.check_call', mock.Mock())
    def test__refresh_supervisor(self):
        """Check how the supervisor is beeing refreshed.
        """
        # Access to a protected member _refresh_supervisor of a client class
        # pylint: disable=W0212

        self.appcfgmgr._refresh_supervisor(
            instance_names=set(['foo#1', 'bar#2'])
        )

        treadmill.subproc.check_call.assert_has_calls(
            [
                mock.call(
                    [
                        's6-svscanctl',
                        '-an',
                        self.running
                    ]
                ),
                mock.call(
                    [
                        's6-svc',
                        '-uO',
                        os.path.join(self.running, 'foo#1'),
                    ]
                ),
                mock.call(
                    [
                        's6-svc',
                        '-uO',
                        os.path.join(self.running, 'bar#2'),
                    ]
                ),
            ]
        )
        # Make sure we did the right amount of retries
        treadmill.subproc.call.assert_has_calls(
            [
                mock.call(
                    [
                        's6-svok',
                        os.path.join(self.running, 'foo#1'),
                    ]
                ),
                mock.call(
                    [
                        's6-svok',
                        os.path.join(self.running, 'foo#1'),
                    ]
                ),
                mock.call(
                    [
                        's6-svok',
                        os.path.join(self.running, 'foo#1'),
                    ]
                ),
                mock.call(
                    [
                        's6-svok',
                        os.path.join(self.running, 'bar#2'),
                    ]
                ),
                mock.call(
                    [
                        's6-svok',
                        os.path.join(self.running, 'bar#2'),
                    ]
                ),
            ]
        )
        self.assertEqual(
            time.sleep.call_count,
            3
        )


if __name__ == '__main__':
    unittest.main()
