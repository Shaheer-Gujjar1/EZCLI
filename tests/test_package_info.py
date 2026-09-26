"""Unit tests for 'ez package-info' subcommand and package inspection engine."""

import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.package_info import (
    PackageCandidate,
    PackageSourceInfo,
    collect_local_binary,
    collect_local_dpkg,
    collect_local_flatpak,
    collect_local_npm,
    collect_local_pip,
    collect_local_snap,
    collect_store_apt,
    collect_store_flatpak,
    collect_store_snap,
    detect_package_nature,
    execute_install_action,
    execute_uninstall_action,
    preview_apt_removal_impact,
    render_candidate_chooser,
    render_installed_card,
    render_not_found_card,
    render_store_card,
    resolve_package_info,
    run_cli_package_info,
    run_package_info_hub,
)


class TestPackageInfo(unittest.TestCase):
    def setUp(self):
        self.console = Console(record=True, width=100)

    # --------------------------------------------------------------------------
    # 1. Local Offline Source Collectors
    # --------------------------------------------------------------------------
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_local_dpkg(self, mock_run):
        # Mock exact match for curl
        dpkg_output = "curl\t8.14.1-2\t491\tweb\tinstall ok installed\n"
        mock_run.side_effect = [
            (0, dpkg_output, ""),
            (0, "Description: command line tool\nHomepage: https://curl.se\nMaintainer: Test <test@example.com>\n", ""),
        ]

        sources = collect_local_dpkg("curl")
        self.assertEqual(len(sources), 1)
        src = sources[0]
        self.assertEqual(src.name, "curl")
        self.assertEqual(src.version, "8.14.1-2")
        self.assertTrue(src.is_installed)
        self.assertEqual(src.homepage, "https://curl.se")

    @patch("shutil.which", return_value="/usr/bin/snap")
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_local_snap(self, mock_run, mock_which):
        snap_list_out = (
            "Name    Version   Rev    Tracking       Publisher   Notes\n"
            "core20  20230801  2015   latest/stable  canonical✓  base\n"
            "vlc     3.0.19    3721   latest/stable  videolan✓   -\n"
        )
        mock_run.return_value = (0, snap_list_out, "")

        sources = collect_local_snap("vlc")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "vlc")
        self.assertEqual(sources[0].version, "3.0.19")
        self.assertTrue(sources[0].is_installed)

    @patch("shutil.which", return_value="/usr/bin/flatpak")
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_local_flatpak(self, mock_run, mock_which):
        fp_list_out = "org.videolan.VLC\t3.0.20\t215 MB\tVLC Media Player\tVLC\n"
        mock_run.return_value = (0, fp_list_out, "")

        sources = collect_local_flatpak("vlc")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].app_id, "org.videolan.VLC")
        self.assertEqual(sources[0].version, "3.0.20")
        self.assertTrue(sources[0].is_installed)

    @patch("importlib.metadata.distributions")
    def test_collect_local_pip(self, mock_dists):
        mock_dist = MagicMock()
        mock_dist.metadata = {
            "Name": "requests",
            "Summary": "Python HTTP for Humans.",
            "Home-page": "https://requests.readthedocs.io",
            "Author": "Kenneth Reitz",
        }
        mock_dist.version = "2.31.0"
        mock_dists.return_value = [mock_dist]

        sources = collect_local_pip("requests")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "requests")
        self.assertEqual(sources[0].version, "2.31.0")
        self.assertEqual(sources[0].source_type, "pip")

    @patch("shutil.which", return_value="/usr/bin/npm")
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_local_npm(self, mock_run, mock_which):
        npm_out = '{"dependencies": {"typescript": {"version": "5.3.3"}}}'
        mock_run.return_value = (0, npm_out, "")

        sources = collect_local_npm("typescript")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "typescript")
        self.assertEqual(sources[0].version, "5.3.3")
        self.assertEqual(sources[0].source_type, "npm")

    @patch("shutil.which", return_value="/usr/bin/curl")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.getsize", return_value=310300)
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_local_binary(self, mock_run, mock_sz, mock_isfile, mock_which):
        mock_run.return_value = (0, "curl 8.14.1 (x86_64-pc-linux-gnu)", "")

        sources = collect_local_binary("curl")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "curl")
        self.assertEqual(sources[0].location, "/usr/bin/curl")
        self.assertIn("8.14.1", sources[0].version)

    # --------------------------------------------------------------------------
    # 2. Store & Catalog Collectors
    # --------------------------------------------------------------------------
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_store_apt(self, mock_run):
        apt_show = (
            "Package: vlc\n"
            "Version: 3.0.23-0\n"
            "Size: 109700\n"
            "Section: video\n"
            "Description: multimedia player and streamer\n"
            "Homepage: https://www.videolan.org/vlc/\n"
        )
        mock_run.return_value = (0, apt_show, "")

        sources = collect_store_apt("vlc")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "vlc")
        self.assertEqual(sources[0].version, "3.0.23-0")
        self.assertFalse(sources[0].is_installed)
        self.assertEqual(sources[0].source_type, "apt_store")

    @patch("shutil.which", return_value="/usr/bin/snap")
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_store_snap(self, mock_run, mock_which):
        snap_find_out = (
            "Name    Version  Publisher  Notes  Summary\n"
            "vlc     3.0.19   videolan✓  -      The ultimate media player\n"
        )
        mock_run.return_value = (0, snap_find_out, "")

        sources = collect_store_snap("vlc")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "vlc")
        self.assertFalse(sources[0].is_installed)

    @patch("shutil.which", return_value="/usr/bin/flatpak")
    @patch("ezcli_app.package_info.run_command_safe")
    def test_collect_store_flatpak(self, mock_run, mock_which):
        fp_search_out = "org.videolan.VLC\t3.0.20\tstable\tflathub\tVLC media player\tVLC\n"
        mock_run.return_value = (0, fp_search_out, "")

        sources = collect_store_flatpak("vlc")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "VLC")
        self.assertEqual(sources[0].app_id, "org.videolan.VLC")
        self.assertFalse(sources[0].is_installed)

    # --------------------------------------------------------------------------
    # 3. Nature Classification
    # --------------------------------------------------------------------------
    def test_detect_package_nature_library(self):
        src = PackageSourceInfo(
            source_type="pip",
            source_name="Python Pip",
            source_icon="🐍",
            is_installed=True,
            name="requests",
            section="python",
        )
        nature, icon = detect_package_nature("requests", [src])
        self.assertEqual(nature, "Library")
        self.assertEqual(icon, "📚")

    @patch("shutil.which", return_value="/usr/bin/curl")
    def test_detect_package_nature_cli(self, mock_which):
        src = PackageSourceInfo(
            source_type="binary",
            source_name="Binary",
            source_icon="🖥️",
            is_installed=True,
            name="curl",
        )
        nature, icon = detect_package_nature("curl", [src])
        self.assertEqual(nature, "CLI Tool")
        self.assertEqual(icon, "⌨️")

    def test_detect_package_nature_desktop_flatpak(self):
        src = PackageSourceInfo(
            source_type="flatpak",
            source_name="Flatpak",
            source_icon="🟣",
            is_installed=True,
            name="VLC",
            app_id="org.videolan.VLC",
        )
        nature, icon = detect_package_nature("vlc", [src])
        self.assertEqual(nature, "Desktop App")
        self.assertEqual(icon, "🖥️")

    # --------------------------------------------------------------------------
    # 4. Name Resolution & Loose Matching
    # --------------------------------------------------------------------------
    @patch("ezcli_app.package_info.collect_local_dpkg")
    @patch("ezcli_app.package_info.collect_store_apt")
    @patch("ezcli_app.package_info.collect_store_flatpak")
    @patch("ezcli_app.package_info.collect_store_snap")
    def test_resolve_exact_match(self, mock_snap, mock_fp, mock_apt_store, mock_dpkg):
        mock_dpkg.return_value = [
            PackageSourceInfo(
                source_type="dpkg",
                source_name="APT",
                source_icon="📦",
                is_installed=True,
                name="curl",
                version="8.14.1",
            )
        ]
        mock_apt_store.return_value = [
            PackageSourceInfo(
                source_type="apt_store",
                source_name="APT Repository",
                source_icon="📦",
                is_installed=False,
                name="curl",
                version="8.14.1",
            )
        ]
        mock_fp.return_value = []
        mock_snap.return_value = []

        candidates, store_avail, note = resolve_package_info("curl")
        self.assertTrue(len(candidates) >= 1)
        top = candidates[0]
        self.assertEqual(top.name, "curl")
        self.assertTrue(top.is_installed)
        self.assertGreaterEqual(top.match_score, 100)

    @patch("ezcli_app.package_info.collect_local_dpkg", return_value=[])
    @patch("ezcli_app.package_info.collect_store_apt")
    @patch("ezcli_app.package_info.collect_store_flatpak", return_value=[])
    @patch("ezcli_app.package_info.collect_store_snap", return_value=[])
    def test_resolve_offline_simulation(self, mock_snap, mock_fp, mock_apt, mock_dpkg):
        # Simulate network error on store query
        mock_apt.side_effect = ConnectionError("Network unreachable")

        candidates, store_avail, note = resolve_package_info("nonexistent")
        self.assertFalse(store_avail)
        self.assertIn("failed", note)

    # --------------------------------------------------------------------------
    # 5. UI Cards & Not-Found
    # --------------------------------------------------------------------------
    def test_render_installed_card(self):
        cand = PackageCandidate(
            name="curl",
            nature="CLI Tool",
            nature_icon="⌨️",
            is_installed=True,
            sources=[
                PackageSourceInfo(
                    source_type="dpkg",
                    source_name="APT",
                    source_icon="📦",
                    is_installed=True,
                    version="8.14.1",
                    installed_size="491 KB",
                    location="/usr/bin/curl",
                    summary="command line tool for transferring data",
                )
            ],
            primary_version="8.14.1",
            summary="command line tool for transferring data",
        )
        render_installed_card(self.console, cand, store_available=True, store_note="")
        output = self.console.export_text()
        self.assertIn("curl", output)
        self.assertIn("Installed", output)
        self.assertIn("8.14.1", output)
        self.assertIn("CLI Tool", output)

    def test_render_store_card(self):
        cand = PackageCandidate(
            name="vlc",
            nature="Desktop App",
            nature_icon="🖥️",
            is_installed=False,
            sources=[
                PackageSourceInfo(
                    source_type="flathub",
                    source_name="Flathub",
                    source_icon="🟣",
                    is_installed=False,
                    version="3.0.20",
                    summary="VLC media player",
                    homepage="https://videolan.org",
                )
            ],
            primary_version="3.0.20",
            summary="VLC media player",
        )
        render_store_card(self.console, cand)
        output = self.console.export_text()
        self.assertIn("vlc", output)
        self.assertIn("Available in Software Catalog", output)
        self.assertIn("Flathub", output)
        self.assertIn("Desktop App", output)

    def test_render_not_found_card(self):
        render_not_found_card(self.console, "nonexistent_app_123")
        output = self.console.export_text()
        self.assertIn("Software Not Found", output)
        self.assertIn("nonexistent_app_123", output)
        self.assertIn("ez update", output)

    # --------------------------------------------------------------------------
    # 6. Action Execution (Install, Uninstall, Dependency Preview)
    # --------------------------------------------------------------------------
    @patch("ezcli_app.package_info.run_command_safe")
    def test_preview_apt_removal_impact(self, mock_run):
        apt_remove_sim = (
            "NOTE: This is only a simulation!\n"
            "Reading package lists... Done\n"
            "The following packages were automatically installed and are no longer required:\n"
            "  libaria2-0 libcares2\n"
            "Use 'apt autoremove' to remove them.\n"
            "The following packages will be REMOVED:\n"
            "  curl libcurl4\n"
            "0 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.\n"
        )
        mock_run.return_value = (0, apt_remove_sim, "")

        impact = preview_apt_removal_impact("curl")
        self.assertIn("curl", impact["packages_to_remove"])
        self.assertIn("libcurl4", impact["packages_to_remove"])
        self.assertIn("libaria2-0", impact["autoremove_packages"])
        self.assertIn("2 to remove", impact["summary"])

    @patch("rich.prompt.Confirm.ask", return_value=True)
    @patch("ezcli_app.package_info.elevated_package_uninstall")
    def test_execute_uninstall_action(self, mock_elev_uninstall, mock_confirm):
        mock_elev_uninstall.return_value = (True, {}, "")
        cand = PackageCandidate(
            name="curl",
            nature="CLI Tool",
            nature_icon="⌨️",
            is_installed=True,
            sources=[
                PackageSourceInfo(
                    source_type="dpkg",
                    source_name="APT",
                    source_icon="📦",
                    is_installed=True,
                    app_id="curl",
                    name="curl",
                )
            ],
        )

        with patch("ezcli_app.package_info.preview_apt_removal_impact") as mock_prev:
            mock_prev.return_value = {
                "packages_to_remove": ["curl"],
                "autoremove_packages": [],
                "summary": "1 to remove",
                "error": "",
            }
            execute_uninstall_action(self.console, cand)

        self.assertTrue(mock_elev_uninstall.called)
        self.assertEqual(mock_elev_uninstall.call_args[1]["package"], "curl")
        self.assertFalse(cand.is_installed)

    @patch("rich.prompt.Confirm.ask", return_value=True)
    @patch("ezcli_app.package_info.elevated_package_install")
    def test_execute_install_action(self, mock_elev_install, mock_confirm):
        mock_elev_install.return_value = (True, {}, "")
        cand = PackageCandidate(
            name="cowsay",
            nature="CLI Tool",
            nature_icon="⌨️",
            is_installed=False,
            sources=[
                PackageSourceInfo(
                    source_type="apt_store",
                    source_name="APT Repository",
                    source_icon="📦",
                    is_installed=False,
                    app_id="cowsay",
                    name="cowsay",
                )
            ],
        )

        execute_install_action(self.console, cand)
        self.assertTrue(mock_elev_install.called)
        self.assertEqual(mock_elev_install.call_args[0][0], "apt")
        self.assertEqual(mock_elev_install.call_args[0][1], "cowsay")
        self.assertTrue(cand.is_installed)

    # --------------------------------------------------------------------------
    # 7. No-Argument Mode (Hub Menu)
    # --------------------------------------------------------------------------
    @patch("rich.prompt.Prompt.ask", return_value="4")
    def test_run_package_info_hub_exit(self, mock_prompt):
        run_package_info_hub(self.console)
        output = self.console.export_text()
        self.assertIn("EasyCLI Package & App Hub", output)
        self.assertIn("My Installed Apps", output)
        self.assertIn("Available Updates", output)
        self.assertIn("Inspect / Search Package", output)

    # --------------------------------------------------------------------------
    # 8. Main Subcommand Runner Flow
    # --------------------------------------------------------------------------
    @patch("ezcli_app.package_info.run_package_info_hub")
    def test_run_cli_package_info_no_args(self, mock_hub):
        run_cli_package_info(None, console=self.console)
        self.assertTrue(mock_hub.called)

    def test_package_info_tui_app_lifecycle(self):
        import asyncio
        from ezcli_app.package_info_tui import PackageInfoApp, AdminPasswordModal

        async def _test():
            app = PackageInfoApp()
            async with app.run_test(size=(120, 36)) as pilot:
                self.assertIsNotNone(pilot.app.query_one("#search-input"))
                self.assertIsNotNone(pilot.app.query_one("#package-table"))
                self.assertIsNotNone(pilot.app.query_one("#catalog-pane"))
                self.assertIsNotNone(pilot.app.query_one("#detail-pane"))
                self.assertIsNotNone(pilot.app.query_one("#detail-scroll"))
                self.assertIsNotNone(pilot.app.query_one("#btn-install"))
                self.assertIsNotNone(pilot.app.query_one("#btn-uninstall"))
                await pilot.click("#btn-close")

        asyncio.run(_test())

    def test_admin_password_modal_lifecycle(self):
        import asyncio
        from textual.app import App  # type: ignore
        from textual.widgets import Input, Label  # type: ignore
        from ezcli_app.package_info_tui import AdminPasswordModal

        class DummyApp(App[None]):
            def on_mount(self):
                self.push_screen(AdminPasswordModal("installation of test-pkg"), self.on_done)
            def on_done(self, result):
                self.result = result
                self.exit()

        async def _test():
            app = DummyApp()
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value = MagicMock(returncode=0)
                async with app.run_test() as pilot:
                    inp = pilot.app.screen.query_one("#admin-input", Input)
                    inp.value = "secret123"
                    await pilot.click("#btn-auth")
                self.assertEqual(app.result, "secret123")

            app2 = DummyApp()
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value = MagicMock(returncode=1)
                async with app2.run_test() as pilot:
                    inp = pilot.app.screen.query_one("#admin-input", Input)
                    inp.value = "wrong"
                    await pilot.click("#btn-auth")
                    err = pilot.app.screen.query_one("#admin-err", Label)
                    self.assertIn("Incorrect password", str(err.render()))
                    await pilot.click("#btn-cancel-auth")
                self.assertIsNone(app2.result)

        asyncio.run(_test())

    def test_check_or_request_admin_passwordless(self):
        from ezcli_app.package_info_tui import PackageInfoApp
        app = PackageInfoApp()
        result = []
        with patch("os.geteuid", return_value=1000), \
             patch("ezcli_app.package_info_tui.is_root", return_value=False), \
             patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            app.check_or_request_admin("test action", result.append)

        self.assertEqual(result, [""])

    def test_confirm_update_all_modal(self):
        import asyncio
        from textual.app import App  # type: ignore
        from ezcli_app.package_info_tui import ConfirmUpdateAllModal

        class DummyApp(App[None]):
            def on_mount(self):
                self.push_screen(ConfirmUpdateAllModal(7), self.on_done)
            def on_done(self, result):
                self.result = result
                self.exit()

        async def _test():
            app = DummyApp()
            async with app.run_test() as pilot:
                await pilot.click("#btn-confirm-update-all")
            self.assertTrue(app.result)

            app2 = DummyApp()
            async with app2.run_test() as pilot:
                await pilot.click("#btn-cancel-update-all")
            self.assertFalse(app2.result)

        asyncio.run(_test())

    def test_updates_tab_toggle_and_candidate_actions(self):
        import asyncio
        from textual.widgets import Button  # type: ignore
        from ezcli_app.package_info_tui import PackageInfoApp
        from ezcli_app.package_info import PackageCandidate, PackageSourceInfo

        cand_update = PackageCandidate(
            name="systemd",
            nature="System Update",
            nature_icon="⬆️",
            is_installed=True,
            summary="Update available: 249.11 → 249.12",
            primary_version="249.12",
            sources=[
                PackageSourceInfo(
                    source_type="apt_store",
                    source_name="APT Update",
                    source_icon="📦",
                    is_installed=True,
                    version="249.12",
                    description="Current: 249.11 → Candidate: 249.12",
                )
            ],
        )

        async def _test():
            app = PackageInfoApp()
            async with app.run_test(size=(120, 36)) as pilot:
                # Switch to updates tab
                with patch("ezcli_app.package_info_tui.collect_available_updates", return_value={"updates": [{"package": "systemd", "current_version": "249.11", "candidate_version": "249.12", "source": "APT"}]}):
                    pilot.app.set_filter_tab("updates")
                    await pilot.pause()

                self.assertTrue(pilot.app.query_one("#tab-update-all", Button).display)
                self.assertTrue(pilot.app.query_one("#btn-update-all", Button).display)
                self.assertFalse(pilot.app.query_one("#btn-launch", Button).display)
                self.assertFalse(pilot.app.query_one("#btn-uninstall", Button).display)

                # Select the update candidate
                pilot.app.update_detail_view(cand_update)
                btn_install = pilot.app.query_one("#btn-install", Button)
                self.assertFalse(btn_install.disabled)
                self.assertIn("Update", str(btn_install.label))

                # Calling action_install on a System Update routes to action_update_single
                with patch.object(pilot.app, "action_update_single") as mock_update_single:
                    pilot.app.action_install()
                    self.assertEqual(mock_update_single.call_count, 1)
                    self.assertEqual(mock_update_single.call_args[0][0].name, "systemd")

                # Test workers inside the active run_test event loop
                with patch("ezcli_app.package_info_tui.elevated_apt_upgrade", return_value=(True, {}, "")) as mock_upgrade, \
                     patch("ezcli_app.package_info_tui.ElevationSession"):
                    pilot.app.run_update_all_worker("mypassword")
                    await pilot.pause()
                    self.assertTrue(mock_upgrade.called)

                with patch("ezcli_app.package_info_tui.elevated_package_install", return_value=(True, {}, "")) as mock_install, \
                     patch("ezcli_app.package_info_tui.ElevationSession"):
                    pilot.app.run_update_single_worker("curl", "mypassword")
                    await pilot.pause()
                    self.assertTrue(mock_install.called)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()

